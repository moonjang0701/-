"""
공역 안전 필드(Airspace Safety Field) 생성 모듈

논문 Section 3.2 구현
3D 공역을 그리드로 나누고 각 셀의 충돌 확률을 계산합니다.
"""

import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from concurrent.futures import ProcessPoolExecutor, as_completed
import os
from .safety_envelope import SafetyEnvelope
from .conflict_probability import ConflictProbabilityCalculator


@dataclass
class UAV:
    """
    UAV 정보 저장 클래스
    
    Attributes
    ----------
    id : int
        UAV 식별자
    position : np.ndarray, shape (3,)
        현재 위치 [x, y, z] (km)
    velocity : np.ndarray, shape (3,)
        현재 속도 [vx, vy, vz] (km/min)
    Vf, Vb, Va, Vd, Vl : float
        최대 속도 파라미터 (km/min)
    response_time : float
        응답 시간 (seconds)
    """
    id: int
    position: np.ndarray
    velocity: np.ndarray
    Vf: float
    Vb: float
    Va: float
    Vd: float
    Vl: float
    response_time: float
    
    def __post_init__(self):
        """데이터 검증"""
        if self.position.shape != (3,):
            raise ValueError("position은 shape (3,) 배열이어야 합니다.")
        if self.velocity.shape != (3,):
            raise ValueError("velocity는 shape (3,) 배열이어야 합니다.")
        if any(v <= 0 for v in [self.Vf, self.Vb, self.Va, self.Vd, self.Vl]):
            raise ValueError("모든 속도는 양수여야 합니다.")
        if self.response_time <= 0:
            raise ValueError("response_time은 양수여야 합니다.")


class AirspaceSafetyField:
    """
    공역 안전 필드 구축 클래스
    
    3D 공역을 그리드로 나누고, 각 그리드 셀에 대해
    다중 UAV와의 충돌 확률을 계산하여 안전 필드를 생성합니다.
    
    Attributes
    ----------
    bounds : Dict[str, Tuple[float, float]]
        공역 경계 {'x': (min, max), 'y': (min, max), 'z': (min, max)} (km)
    grid_resolution : float
        그리드 셀 크기 (km)
    r_A1, r_A2, r_A3 : float
        위치 불확실성 파라미터 (km·min^(-1/2))
    grid_shape : Tuple[int, int, int]
        그리드 차원 (nx, ny, nz)
    field : np.ndarray, shape (nx, ny, nz)
        계산된 안전 필드 (각 셀의 충돌 확률)
    """
    
    def __init__(
        self,
        bounds: Dict[str, Tuple[float, float]],
        grid_resolution: float,
        r_A1: float,
        r_A2: float,
        r_A3: float
    ) -> None:
        """
        공역 안전 필드 초기화
        
        Parameters
        ----------
        bounds : Dict[str, Tuple[float, float]]
            공역 경계 {'x': (xmin, xmax), 'y': (ymin, ymax), 'z': (zmin, zmax)} (km)
        grid_resolution : float
            그리드 셀 크기 (km)
        r_A1 : float
            Along-track 분산 성장률 (km·min^(-1/2))
        r_A2 : float
            Cross-track 분산 성장률 1 (km·min^(-1/2))
        r_A3 : float
            Cross-track 분산 성장률 2 (km·min^(-1/2))
            
        Raises
        ------
        ValueError
            경계나 해상도가 유효하지 않은 경우
        """
        # 입력 검증
        if grid_resolution <= 0:
            raise ValueError("grid_resolution은 양수여야 합니다.")
        
        for axis in ['x', 'y', 'z']:
            if axis not in bounds:
                raise ValueError(f"bounds에 '{axis}' 키가 필요합니다.")
            if bounds[axis][0] >= bounds[axis][1]:
                raise ValueError(f"{axis} 축의 min은 max보다 작아야 합니다.")
        
        if any(r <= 0 for r in [r_A1, r_A2, r_A3]):
            raise ValueError("모든 분산 성장률은 양수여야 합니다.")
        
        self.bounds = bounds
        self.grid_resolution = grid_resolution
        self.r_A1 = r_A1
        self.r_A2 = r_A2
        self.r_A3 = r_A3
        
        # 그리드 차원 계산
        self.x_min, self.x_max = bounds['x']
        self.y_min, self.y_max = bounds['y']
        self.z_min, self.z_max = bounds['z']
        
        self.nx = int(np.ceil((self.x_max - self.x_min) / grid_resolution))
        self.ny = int(np.ceil((self.y_max - self.y_min) / grid_resolution))
        self.nz = int(np.ceil((self.z_max - self.z_min) / grid_resolution))
        
        self.grid_shape = (self.nx, self.ny, self.nz)
        
        # 안전 필드 (초기값 0)
        self.field: Optional[np.ndarray] = None
        
        # 그리드 좌표 생성 (중심점)
        self.x_coords = np.linspace(
            self.x_min + grid_resolution/2,
            self.x_max - grid_resolution/2,
            self.nx
        )
        self.y_coords = np.linspace(
            self.y_min + grid_resolution/2,
            self.y_max - grid_resolution/2,
            self.ny
        )
        self.z_coords = np.linspace(
            self.z_min + grid_resolution/2,
            self.z_max - grid_resolution/2,
            self.nz
        )
    
    def compute_field(
        self,
        uavs: List[UAV],
        t0: float,
        delta_t: float,
        parallel: bool = True,
        n_workers: Optional[int] = None,
        verbose: bool = False
    ) -> np.ndarray:
        """
        전체 공역의 안전 필드 계산
        
        모든 그리드 셀에 대해 다중 UAV와의 충돌 확률을 계산합니다.
        병렬 처리를 통해 계산 속도를 향상시킵니다.
        
        Parameters
        ----------
        uavs : List[UAV]
            UAV 리스트
        t0 : float
            시작 시간 (min)
        delta_t : float
            예측 시간 구간 (min)
        parallel : bool, default=True
            병렬 처리 여부
        n_workers : Optional[int], default=None
            워커 프로세스 수 (None이면 CPU 코어 수)
        verbose : bool, default=False
            진행률 출력 여부
        
        Returns
        -------
        np.ndarray, shape (nx, ny, nz)
            각 셀의 충돌 확률
        """
        if len(uavs) == 0:
            raise ValueError("UAV 리스트가 비어있습니다.")
        
        # 안전 필드 초기화
        self.field = np.zeros(self.grid_shape)
        
        # 모든 그리드 좌표 생성
        grid_points = []
        grid_indices = []
        
        for i in range(self.nx):
            for j in range(self.ny):
                for k in range(self.nz):
                    X = np.array([
                        self.x_coords[i],
                        self.y_coords[j],
                        self.z_coords[k]
                    ])
                    grid_points.append(X)
                    grid_indices.append((i, j, k))
        
        total_points = len(grid_points)
        
        if verbose:
            print(f"공역 안전 필드 계산 시작")
            print(f"  그리드 크기: {self.grid_shape}")
            print(f"  총 포인트 수: {total_points:,}")
            print(f"  UAV 수: {len(uavs)}")
            print(f"  병렬 처리: {parallel}")
        
        if parallel and total_points > 100:
            # 병렬 처리
            if n_workers is None:
                n_workers = os.cpu_count()
            
            if verbose:
                print(f"  워커 수: {n_workers}")
            
            # 작업 분할
            chunk_size = max(1, total_points // (n_workers * 4))
            
            with ProcessPoolExecutor(max_workers=n_workers) as executor:
                # 작업 제출
                futures = []
                for i in range(0, total_points, chunk_size):
                    chunk_points = grid_points[i:i+chunk_size]
                    chunk_indices = grid_indices[i:i+chunk_size]
                    
                    future = executor.submit(
                        _compute_chunk_safety,
                        chunk_points,
                        chunk_indices,
                        uavs,
                        t0,
                        delta_t,
                        self.r_A1,
                        self.r_A2,
                        self.r_A3
                    )
                    futures.append(future)
                
                # 결과 수집
                completed = 0
                for future in as_completed(futures):
                    chunk_results = future.result()
                    for idx, prob in chunk_results:
                        i, j, k = idx
                        self.field[i, j, k] = prob
                    
                    completed += len(chunk_results)
                    if verbose and completed % 1000 == 0:
                        progress = completed / total_points * 100
                        print(f"  진행률: {progress:.1f}% ({completed:,}/{total_points:,})")
        
        else:
            # 순차 처리
            if verbose:
                print(f"  순차 처리 모드")
            
            for idx_num, (X, idx) in enumerate(zip(grid_points, grid_indices)):
                prob = self._compute_point_safety(X, uavs, t0, delta_t)
                i, j, k = idx
                self.field[i, j, k] = prob
                
                if verbose and (idx_num + 1) % 1000 == 0:
                    progress = (idx_num + 1) / total_points * 100
                    print(f"  진행률: {progress:.1f}% ({idx_num+1:,}/{total_points:,})")
        
        if verbose:
            print(f"계산 완료!")
            print(f"  최대 충돌 확률: {np.max(self.field):.6e}")
            print(f"  평균 충돌 확률: {np.mean(self.field):.6e}")
            dangerous = np.sum(self.field > 0.01)
            print(f"  위험 셀 수 (>1%): {dangerous:,} ({dangerous/total_points*100:.2f}%)")
        
        return self.field
    
    def _compute_point_safety(
        self,
        X: np.ndarray,
        uavs: List[UAV],
        t0: float,
        delta_t: float
    ) -> float:
        """
        Eq. (9) 구현 - 단일 좌표의 안전도 계산
        
        다중 UAV와의 충돌 확률을 결합합니다.
        
        수식:
        s(X) = 1 - ∏_{i=1}^N (1 - p_{A_i}(X))
        
        의미: N대의 UAV 중 적어도 하나와 충돌할 확률
        
        Parameters
        ----------
        X : np.ndarray, shape (3,)
            공간 좌표 [x, y, z] (km)
        uavs : List[UAV]
            모든 UAV
        t0 : float
            시작 시간 (min)
        delta_t : float
            시간 구간 (min)
        
        Returns
        -------
        float
            충돌 확률 s(X) ∈ [0, 1]
        """
        # Eq. (9) - Multiple UAV safety probability
        # s(X) = 1 - ∏(1 - p_i)
        
        product_term = 1.0
        
        for uav in uavs:
            # 각 UAV에 대한 안전 엔벨로프 생성
            envelope = SafetyEnvelope(
                Vf=uav.Vf,
                Vb=uav.Vb,
                Va=uav.Va,
                Vd=uav.Vd,
                Vl=uav.Vl,
                response_time=uav.response_time
            )
            
            # 충돌 확률 계산기 생성
            calculator = ConflictProbabilityCalculator(
                safety_envelope=envelope,
                r_A1=self.r_A1,
                r_A2=self.r_A2,
                r_A3=self.r_A3
            )
            
            # 해당 UAV와의 충돌 확률 계산
            p_i = calculator.compute_conflict_probability(
                X=X,
                X_A0=uav.position,
                v_A=uav.velocity,
                t0=t0,
                delta_t=delta_t
            )
            
            # 누적 곱 계산: ∏(1 - p_i)
            product_term *= (1.0 - p_i)
        
        # 최종 충돌 확률: 1 - ∏(1 - p_i)
        safety_probability = 1.0 - product_term
        
        return safety_probability
    
    def get_dangerous_regions(
        self,
        threshold: float = 0.01
    ) -> np.ndarray:
        """
        임계값을 초과하는 위험 영역 추출
        
        Parameters
        ----------
        threshold : float, default=0.01
            충돌 확률 임계값 (1%)
        
        Returns
        -------
        np.ndarray, shape (N, 3)
            위험 좌표 배열 [x, y, z]
        
        Raises
        ------
        ValueError
            안전 필드가 아직 계산되지 않은 경우
        """
        if self.field is None:
            raise ValueError("먼저 compute_field()를 호출하여 안전 필드를 계산해야 합니다.")
        
        # 임계값 초과 인덱스 찾기
        dangerous_indices = np.argwhere(self.field > threshold)
        
        # 인덱스를 실제 좌표로 변환
        dangerous_positions = []
        for idx in dangerous_indices:
            i, j, k = idx
            position = self.index_to_position((i, j, k))
            dangerous_positions.append(position)
        
        if len(dangerous_positions) == 0:
            return np.empty((0, 3))
        
        return np.array(dangerous_positions)
    
    def get_value_at_position(self, position: np.ndarray) -> float:
        """
        특정 위치의 충돌 확률 조회
        
        가장 가까운 그리드 셀의 값을 반환합니다.
        
        Parameters
        ----------
        position : np.ndarray, shape (3,)
            조회할 위치 [x, y, z] (km)
        
        Returns
        -------
        float
            충돌 확률
        
        Raises
        ------
        ValueError
            안전 필드가 계산되지 않았거나 위치가 공역 밖인 경우
        """
        if self.field is None:
            raise ValueError("먼저 compute_field()를 호출하여 안전 필드를 계산해야 합니다.")
        
        # 인덱스 변환
        i, j, k = self.position_to_index(position)
        
        # 경계 확인
        if not (0 <= i < self.nx and 0 <= j < self.ny and 0 <= k < self.nz):
            raise ValueError(f"위치 {position}가 공역 경계를 벗어났습니다.")
        
        return self.field[i, j, k]
    
    def position_to_index(self, position: np.ndarray) -> Tuple[int, int, int]:
        """
        실제 좌표를 그리드 인덱스로 변환
        
        Parameters
        ----------
        position : np.ndarray, shape (3,)
            [x, y, z] (km)
        
        Returns
        -------
        Tuple[int, int, int]
            (i, j, k) 그리드 인덱스
        """
        x, y, z = position
        
        # 가장 가까운 그리드 셀 인덱스 계산
        i = int(np.round((x - self.x_min) / self.grid_resolution - 0.5))
        j = int(np.round((y - self.y_min) / self.grid_resolution - 0.5))
        k = int(np.round((z - self.z_min) / self.grid_resolution - 0.5))
        
        # 경계 내로 제한
        i = np.clip(i, 0, self.nx - 1)
        j = np.clip(j, 0, self.ny - 1)
        k = np.clip(k, 0, self.nz - 1)
        
        return (i, j, k)
    
    def index_to_position(self, idx: Tuple[int, int, int]) -> np.ndarray:
        """
        그리드 인덱스를 실제 좌표로 변환
        
        그리드 셀의 중심 좌표를 반환합니다.
        
        Parameters
        ----------
        idx : Tuple[int, int, int]
            (i, j, k) 그리드 인덱스
        
        Returns
        -------
        np.ndarray, shape (3,)
            [x, y, z] (km)
        """
        i, j, k = idx
        
        x = self.x_coords[i]
        y = self.y_coords[j]
        z = self.z_coords[k]
        
        return np.array([x, y, z])
    
    def get_statistics(self) -> Dict[str, float]:
        """
        안전 필드 통계 반환
        
        Returns
        -------
        Dict[str, float]
            통계 정보
        """
        if self.field is None:
            raise ValueError("먼저 compute_field()를 호출하여 안전 필드를 계산해야 합니다.")
        
        return {
            'max': float(np.max(self.field)),
            'min': float(np.min(self.field)),
            'mean': float(np.mean(self.field)),
            'std': float(np.std(self.field)),
            'median': float(np.median(self.field)),
            'dangerous_cells_1pct': int(np.sum(self.field > 0.01)),
            'dangerous_cells_5pct': int(np.sum(self.field > 0.05)),
            'dangerous_cells_10pct': int(np.sum(self.field > 0.1)),
        }
    
    def __repr__(self) -> str:
        """문자열 표현"""
        field_status = "계산됨" if self.field is not None else "미계산"
        return (
            f"AirspaceSafetyField(\n"
            f"  bounds: x=[{self.x_min}, {self.x_max}], "
            f"y=[{self.y_min}, {self.y_max}], "
            f"z=[{self.z_min}, {self.z_max}] km,\n"
            f"  grid_shape: {self.grid_shape},\n"
            f"  resolution: {self.grid_resolution} km,\n"
            f"  uncertainty: r_A1={self.r_A1}, r_A2={self.r_A2}, r_A3={self.r_A3},\n"
            f"  field: {field_status}\n"
            f")"
        )


# 병렬 처리를 위한 독립 함수
def _compute_chunk_safety(
    chunk_points: List[np.ndarray],
    chunk_indices: List[Tuple[int, int, int]],
    uavs: List[UAV],
    t0: float,
    delta_t: float,
    r_A1: float,
    r_A2: float,
    r_A3: float
) -> List[Tuple[Tuple[int, int, int], float]]:
    """
    병렬 처리를 위한 청크 안전도 계산
    
    Parameters
    ----------
    chunk_points : List[np.ndarray]
        계산할 좌표 리스트
    chunk_indices : List[Tuple[int, int, int]]
        해당하는 그리드 인덱스 리스트
    uavs : List[UAV]
        UAV 리스트
    t0, delta_t : float
        시간 파라미터
    r_A1, r_A2, r_A3 : float
        불확실성 파라미터
    
    Returns
    -------
    List[Tuple[Tuple[int, int, int], float]]
        [(인덱스, 확률), ...] 리스트
    """
    results = []
    
    for X, idx in zip(chunk_points, chunk_indices):
        # 각 UAV와의 충돌 확률 계산 및 결합
        product_term = 1.0
        
        for uav in uavs:
            envelope = SafetyEnvelope(
                Vf=uav.Vf,
                Vb=uav.Vb,
                Va=uav.Va,
                Vd=uav.Vd,
                Vl=uav.Vl,
                response_time=uav.response_time
            )
            
            calculator = ConflictProbabilityCalculator(
                safety_envelope=envelope,
                r_A1=r_A1,
                r_A2=r_A2,
                r_A3=r_A3
            )
            
            p_i = calculator.compute_conflict_probability(
                X=X,
                X_A0=uav.position,
                v_A=uav.velocity,
                t0=t0,
                delta_t=delta_t
            )
            
            product_term *= (1.0 - p_i)
        
        safety_prob = 1.0 - product_term
        results.append((idx, safety_prob))
    
    return results
