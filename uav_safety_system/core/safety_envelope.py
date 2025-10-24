"""
UAV 안전 엔벨로프(Safety Envelope) 계산 모듈

논문 Section 2.1 구현
안전 엔벨로프는 UAV가 응답 시간 내에 도달할 수 있는 3D 타원체 영역입니다.
"""

import numpy as np
from typing import Tuple, Dict


class SafetyEnvelope:
    """
    UAV 안전 엔벨로프 계산 클래스
    
    UAV의 기동 성능(최대 속도)과 응답 시간을 기반으로
    보호 공역(타원체)을 계산합니다.
    
    Attributes
    ----------
    Vf : float
        최대 전방 속도 (km/min)
    Vb : float
        최대 후방 속도 (km/min)
    Va : float
        최대 상승 속도 (km/min)
    Vd : float
        최대 하강 속도 (km/min)
    Vl : float
        최대 횡방향 속도 (km/min)
    response_time : float
        응답 시간 (seconds)
    s : float
        응답 시간 (minutes) - 계산용
    a, b, c, d, e, f : float
        각 방향 최대 도달 거리 (km)
    """
    
    def __init__(
        self,
        Vf: float,
        Vb: float,
        Va: float,
        Vd: float,
        Vl: float,
        response_time: float
    ) -> None:
        """
        안전 엔벨로프 초기화
        
        Parameters
        ----------
        Vf : float
            최대 전방 속도 (km/min)
        Vb : float
            최대 후방 속도 (km/min)
        Va : float
            최대 상승 속도 (km/min)
        Vd : float
            최대 하강 속도 (km/min)
        Vl : float
            최대 횡방향 속도 (km/min)
        response_time : float
            응답 시간 (seconds)
            
        Raises
        ------
        ValueError
            속도나 응답 시간이 음수인 경우
        """
        # 입력 유효성 검증
        if any(v <= 0 for v in [Vf, Vb, Va, Vd, Vl, response_time]):
            raise ValueError("모든 속도와 응답 시간은 양수여야 합니다.")
        
        # UAV 성능 파라미터 저장
        self.Vf = Vf  # km/min
        self.Vb = Vb  # km/min
        self.Va = Va  # km/min
        self.Vd = Vd  # km/min
        self.Vl = Vl  # km/min
        self.response_time = response_time  # seconds
        
        # 단위 변환: 초(sec) → 분(min)
        self.s = response_time / 60.0  # min
        
        # Eq. (1) - 각 방향 최대 도달 거리 계산
        axes = self.compute_axes()
        self.a = axes['a']  # 전방 (km)
        self.b = axes['b']  # 후방 (km)
        self.c = axes['c']  # 상승 (km)
        self.d = axes['d']  # 하강 (km)
        self.e = axes['e']  # 좌측 (km)
        self.f = axes['f']  # 우측 (km) - 대칭이므로 e와 동일
    
    def compute_axes(self) -> Dict[str, float]:
        """
        Eq. (1) 구현 - 각 방향 최대 도달 거리 계산
        
        안전 엔벨로프의 각 축 반경을 계산합니다:
        - a: 전방 방향 (x > x_A)
        - b: 후방 방향 (x < x_A)
        - c: 상승 방향 (z > z_A)
        - d: 하강 방향 (z < z_A)
        - e, f: 횡방향 (y축, 좌우 대칭)
        
        수식:
        a = Vf × s
        b = Vb × s
        c = Va × s
        d = Vd × s
        e = f = Vl × s
        
        여기서 s는 응답 시간(분)
        
        Returns
        -------
        Dict[str, float]
            각 축의 반경 {'a', 'b', 'c', 'd', 'e', 'f'} (km)
        """
        a = self.Vf * self.s  # 전방 (km)
        b = self.Vb * self.s  # 후방 (km)
        c = self.Va * self.s  # 상승 (km)
        d = self.Vd * self.s  # 하강 (km)
        e = self.Vl * self.s  # 횡방향 (km)
        f = self.Vl * self.s  # 횡방향 대칭 (km)
        
        return {
            'a': a,
            'b': b,
            'c': c,
            'd': d,
            'e': e,
            'f': f
        }
    
    def compute_equivalent_radius(self) -> float:
        """
        Eq. (24) 구현 - 등가 구 반경 계산
        
        비대칭 타원체를 등가 구로 변환한 반경을 계산합니다.
        이는 충돌 확률 계산 및 안전장 생성에 사용됩니다.
        
        수식:
        r_eq = [Vl × (Vf×Va + Vf×Vd + Vb×Va + Vb×Vd) / 4]^(1/3) × s
        
        Returns
        -------
        float
            등가 구 반경 (km)
        """
        # Eq. (24) - 등가 반경 계산
        # r_eq = [Vl × (Vf×Va + Vf×Vd + Vb×Va + Vb×Vd) / 4]^(1/3) × s
        
        term1 = self.Vf * self.Va
        term2 = self.Vf * self.Vd
        term3 = self.Vb * self.Va
        term4 = self.Vb * self.Vd
        
        sum_terms = term1 + term2 + term3 + term4
        
        r_eq = np.power(self.Vl * sum_terms / 4.0, 1.0/3.0) * self.s
        
        return r_eq
    
    def get_matrix_M(self, X: np.ndarray, X_A: np.ndarray) -> np.ndarray:
        """
        Eq. (3-4) 구현 - 사분면별 행렬 선택
        
        UAV 중심 좌표(X_A)를 기준으로 테스트 좌표(X)의 상대 위치에 따라
        적절한 대각 행렬을 반환합니다.
        
        4개의 사분면(octant):
        - M₁: x ≥ x_A and z ≥ z_A (전방-상승)
        - M₂: x ≥ x_A and z < z_A (전방-하강)
        - M₃: x < x_A and z ≥ z_A (후방-상승)
        - M₄: x < x_A and z < z_A (후방-하강)
        
        수식:
        M₁ = diag[1/a², 1/e², 1/c²]
        M₂ = diag[1/a², 1/e², 1/d²]
        M₃ = diag[1/b², 1/e², 1/c²]
        M₄ = diag[1/b², 1/e², 1/d²]
        
        Parameters
        ----------
        X : np.ndarray, shape (3,)
            테스트할 공간 좌표 [x, y, z] (km)
        X_A : np.ndarray, shape (3,)
            UAV 중심 좌표 [x_A, y_A, z_A] (km)
        
        Returns
        -------
        np.ndarray, shape (3, 3)
            대각 행렬 M
        """
        # 상대 좌표 계산
        dx = X[0] - X_A[0]  # x 방향 차이
        dz = X[2] - X_A[2]  # z 방향 차이
        
        # 사분면 판별 및 해당 행렬 반환
        if dx >= 0 and dz >= 0:
            # M₁: 전방-상승 (x ≥ x_A and z ≥ z_A)
            # diag[1/a², 1/e², 1/c²]
            M = np.diag([1.0/(self.a**2), 1.0/(self.e**2), 1.0/(self.c**2)])
        elif dx >= 0 and dz < 0:
            # M₂: 전방-하강 (x ≥ x_A and z < z_A)
            # diag[1/a², 1/e², 1/d²]
            M = np.diag([1.0/(self.a**2), 1.0/(self.e**2), 1.0/(self.d**2)])
        elif dx < 0 and dz >= 0:
            # M₃: 후방-상승 (x < x_A and z ≥ z_A)
            # diag[1/b², 1/e², 1/c²]
            M = np.diag([1.0/(self.b**2), 1.0/(self.e**2), 1.0/(self.c**2)])
        else:  # dx < 0 and dz < 0
            # M₄: 후방-하강 (x < x_A and z < z_A)
            # diag[1/b², 1/e², 1/d²]
            M = np.diag([1.0/(self.b**2), 1.0/(self.e**2), 1.0/(self.d**2)])
        
        return M
    
    def is_inside(self, X: np.ndarray, X_A: np.ndarray) -> bool:
        """
        Eq. (5) 구현 - 점이 안전 엔벨로프 내부인지 판정
        
        주어진 점 X가 UAV 중심 X_A를 기준으로 한 안전 엔벨로프 내부에
        있는지 타원체 방정식을 이용하여 판정합니다.
        
        수식:
        (X - X_A)ᵀ M (X - X_A) ≤ 1
        
        여기서 M은 사분면에 따라 선택된 대각 행렬
        
        Parameters
        ----------
        X : np.ndarray, shape (3,)
            테스트할 좌표 [x, y, z] (km)
        X_A : np.ndarray, shape (3,)
            UAV 위치 [x_A, y_A, z_A] (km)
        
        Returns
        -------
        bool
            내부이면 True, 외부이면 False
        """
        # 입력 검증
        if X.shape != (3,) or X_A.shape != (3,):
            raise ValueError("X와 X_A는 모두 shape (3,) 배열이어야 합니다.")
        
        # Eq. (5) - 타원체 방정식
        # (X - X_A)ᵀ M (X - X_A) ≤ 1
        
        # 1. 상대 위치 벡터 계산
        delta = X - X_A  # shape (3,)
        
        # 2. 사분면에 따른 행렬 M 선택
        M = self.get_matrix_M(X, X_A)  # shape (3, 3)
        
        # 3. 이차 형식 계산: δᵀ M δ
        quadratic_form = np.dot(delta, np.dot(M, delta))
        
        # 4. 타원체 내부 판정
        return quadratic_form <= 1.0
    
    def get_volume(self) -> float:
        """
        Eq. (22) 구현 - 안전 엔벨로프 부피 계산
        
        비대칭 타원체의 부피를 4개 사분면 타원체의 합으로 계산합니다.
        각 사분면은 1/8 타원체이며, 4개를 합하면 전체 엔벨로프가 됩니다.
        
        수식:
        V = (1/4) × [(4πade)/3 + (4πace)/3 + (4πbce)/3 + (4πbde)/3]
        
        여기서:
        - 첫 번째 항: 전방-상승 사분면 (a, e, c)
        - 두 번째 항: 전방-하강 사분면 (a, e, d)
        - 세 번째 항: 후방-상승 사분면 (b, e, c)
        - 네 번째 항: 후방-하강 사분면 (b, e, d)
        
        Returns
        -------
        float
            안전 엔벨로프 부피 (km³)
        """
        # Eq. (22) - 4개 사분면 타원체 부피의 합
        # V = (1/4) × [(4πade)/3 + (4πace)/3 + (4πbce)/3 + (4πbde)/3]
        
        # 각 사분면의 부피 (1/8 타원체)
        V1 = (4.0 * np.pi * self.a * self.d * self.e) / 3.0  # 전방-하강
        V2 = (4.0 * np.pi * self.a * self.c * self.e) / 3.0  # 전방-상승
        V3 = (4.0 * np.pi * self.b * self.c * self.e) / 3.0  # 후방-상승
        V4 = (4.0 * np.pi * self.b * self.d * self.e) / 3.0  # 후방-하강
        
        # 전체 부피
        V_total = (V1 + V2 + V3 + V4) / 4.0
        
        return V_total
    
    def get_distance_to_surface(
        self,
        X: np.ndarray,
        X_A: np.ndarray
    ) -> float:
        """
        점 X에서 안전 엔벨로프 표면까지의 정규화된 거리 계산
        
        타원체 방정식의 값이 1이면 표면, 1보다 작으면 내부, 크면 외부입니다.
        이 값을 이용하여 표면까지의 상대적 거리를 계산합니다.
        
        Parameters
        ----------
        X : np.ndarray, shape (3,)
            테스트할 좌표 (km)
        X_A : np.ndarray, shape (3,)
            UAV 위치 (km)
        
        Returns
        -------
        float
            정규화된 거리
            - < 1.0: 내부 (표면까지의 거리)
            - = 1.0: 표면
            - > 1.0: 외부 (표면으로부터의 거리)
        """
        delta = X - X_A
        M = self.get_matrix_M(X, X_A)
        quadratic_form = np.dot(delta, np.dot(M, delta))
        
        return np.sqrt(quadratic_form)
    
    def __repr__(self) -> str:
        """문자열 표현"""
        return (
            f"SafetyEnvelope(\n"
            f"  Vf={self.Vf:.2f} km/min, Vb={self.Vb:.2f} km/min,\n"
            f"  Va={self.Va:.2f} km/min, Vd={self.Vd:.2f} km/min,\n"
            f"  Vl={self.Vl:.2f} km/min, response_time={self.response_time:.1f} sec,\n"
            f"  axes: a={self.a:.3f}, b={self.b:.3f}, c={self.c:.3f}, "
            f"d={self.d:.3f}, e={self.e:.3f} km,\n"
            f"  r_eq={self.compute_equivalent_radius():.3f} km, "
            f"  volume={self.get_volume():.3f} km³\n"
            f")"
        )
