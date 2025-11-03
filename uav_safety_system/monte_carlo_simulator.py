"""
Monte Carlo UAV 충돌 시뮬레이터

현실적인 드론 배송 시나리오:
- 8시간 운영
- 시간당 20대 드론 (총 160대, 시간적 분리)
- 출발지 → 목적지 직선 비행
- GPS 오차 ±5m
"""

import numpy as np
from dataclasses import dataclass
from typing import List, Tuple
import time

@dataclass
class UAVFlight:
    """단일 UAV 비행 정보"""
    uav_id: int
    start_time: float        # 출발 시간 (분)
    end_time: float          # 도착 시간 (분)
    start_pos: np.ndarray    # 출발 위치 [x, y, z] (km)
    end_pos: np.ndarray      # 도착 위치 [x, y, z] (km)
    cruise_speed: float      # 순항 속도 (km/min)
    
    def get_position(self, t: float, gps_noise_std: float = 0.005) -> np.ndarray:
        """
        시간 t에서의 UAV 위치 계산 (GPS 오차 포함)
        
        Parameters
        ----------
        t : float
            현재 시간 (분)
        gps_noise_std : float
            GPS 오차 표준편차 (km) - 기본값 5m
            
        Returns
        -------
        np.ndarray
            현재 위치 [x, y, z] (km), None if not active
        """
        # 비행 중이 아니면 None 반환
        if t < self.start_time or t > self.end_time:
            return None
        
        # 비행 진행도 (0 ~ 1)
        progress = (t - self.start_time) / (self.end_time - self.start_time)
        
        # 선형 보간으로 위치 계산
        pos = self.start_pos + progress * (self.end_pos - self.start_pos)
        
        # GPS 오차 추가 (x, y만, z는 고도 유지)
        noise = np.array([
            np.random.normal(0, gps_noise_std),
            np.random.normal(0, gps_noise_std),
            0  # 고도는 정확하다고 가정
        ])
        
        return pos + noise


class MonteCarloSimulator:
    """Monte Carlo UAV 충돌 시뮬레이터"""
    
    def __init__(
        self,
        airspace_size: Tuple[float, float, float] = (1.5, 0.9, 0.15),  # km
        base_position: Tuple[float, float, float] = (0.75, 0.05, 0.075),  # km
        max_delivery_distance: float = 1.5,  # km
        safe_distance: float = 0.05,  # km (50m)
        gps_noise_std: float = 0.005,  # km (5m)
        cruise_speed: float = 1.0,  # km/min (60 km/h)
        time_step: float = 0.1  # 시간 스텝 (분) - 6초
    ):
        """
        시뮬레이터 초기화
        
        Parameters
        ----------
        airspace_size : tuple
            공역 크기 (x, y, z) in km
        base_position : tuple
            베이스(충전소) 위치 (x, y, z) in km
        max_delivery_distance : float
            최대 배송 거리 (km)
        safe_distance : float
            안전 거리 (km) - 이보다 가까우면 충돌
        gps_noise_std : float
            GPS 오차 표준편차 (km)
        cruise_speed : float
            순항 속도 (km/min)
        time_step : float
            시뮬레이션 시간 간격 (분)
        """
        self.airspace_size = np.array(airspace_size)
        self.base_position = np.array(base_position)
        self.max_delivery_distance = max_delivery_distance
        self.safe_distance = safe_distance
        self.gps_noise_std = gps_noise_std
        self.cruise_speed = cruise_speed
        self.time_step = time_step
        
    def generate_random_destination(self) -> np.ndarray:
        """
        베이스에서 최대 거리 내의 랜덤 목적지 생성
        
        Returns
        -------
        np.ndarray
            목적지 위치 [x, y, z] (km)
        """
        # 각도 랜덤 (0 ~ 360도)
        angle = np.random.uniform(0, 2 * np.pi)
        
        # 거리 랜덤 (0 ~ max_delivery_distance)
        # 면적 균등 분포를 위해 √r 사용
        distance = np.sqrt(np.random.uniform(0, 1)) * self.max_delivery_distance
        
        # 극좌표 → 직교좌표
        dx = distance * np.cos(angle)
        dy = distance * np.sin(angle)
        
        # 목적지 = 베이스 + 오프셋
        dest = self.base_position.copy()
        dest[0] += dx
        dest[1] += dy
        
        # 공역 내로 클램핑
        dest[0] = np.clip(dest[0], 0, self.airspace_size[0])
        dest[1] = np.clip(dest[1], 0, self.airspace_size[1])
        
        return dest
    
    def create_uav_schedule(
        self,
        total_hours: int = 8,
        uavs_per_hour: int = 20
    ) -> List[UAVFlight]:
        """
        UAV 비행 스케줄 생성
        
        Parameters
        ----------
        total_hours : int
            총 운영 시간 (시간)
        uavs_per_hour : int
            시간당 UAV 수
            
        Returns
        -------
        List[UAVFlight]
            UAV 비행 리스트
        """
        flights = []
        uav_id = 0
        
        for hour in range(total_hours):
            # 이 시간대의 시작 시간 (분)
            hour_start = hour * 60
            
            for _ in range(uavs_per_hour):
                # 출발 시간: 이 시간대 내에서 랜덤 (±10분 분산)
                start_time = hour_start + np.random.uniform(0, 60)
                
                # 목적지 생성
                destination = self.generate_random_destination()
                
                # 비행 거리 계산
                distance = np.linalg.norm(destination - self.base_position)
                
                # 비행 시간 계산 (거리 / 속도)
                flight_duration = distance / self.cruise_speed
                
                # 도착 시간
                end_time = start_time + flight_duration
                
                # UAVFlight 객체 생성
                flight = UAVFlight(
                    uav_id=uav_id,
                    start_time=start_time,
                    end_time=end_time,
                    start_pos=self.base_position.copy(),
                    end_pos=destination,
                    cruise_speed=self.cruise_speed
                )
                
                flights.append(flight)
                uav_id += 1
        
        return flights
    
    def check_collision(
        self,
        flights: List[UAVFlight],
        t: float
    ) -> bool:
        """
        시간 t에서 충돌 여부 확인
        
        Parameters
        ----------
        flights : List[UAVFlight]
            모든 UAV 비행 리스트
        t : float
            현재 시간 (분)
            
        Returns
        -------
        bool
            충돌 발생 여부
        """
        # 현재 활성 UAV들의 위치 가져오기
        active_positions = []
        active_ids = []
        
        for flight in flights:
            pos = flight.get_position(t, self.gps_noise_std)
            if pos is not None:
                active_positions.append(pos)
                active_ids.append(flight.uav_id)
        
        # 활성 UAV가 2대 미만이면 충돌 불가
        if len(active_positions) < 2:
            return False
        
        # 모든 UAV 쌍에 대해 거리 확인
        for i in range(len(active_positions)):
            for j in range(i + 1, len(active_positions)):
                distance = np.linalg.norm(
                    active_positions[i] - active_positions[j]
                )
                
                if distance < self.safe_distance:
                    return True  # 충돌 발생!
        
        return False
    
    def run_single_trial(
        self,
        total_hours: int = 8,
        uavs_per_hour: int = 20,
        verbose: bool = False
    ) -> Tuple[bool, dict]:
        """
        단일 시뮬레이션 시행
        
        Parameters
        ----------
        total_hours : int
            총 운영 시간 (시간)
        uavs_per_hour : int
            시간당 UAV 수
        verbose : bool
            상세 로그 출력 여부
            
        Returns
        -------
        Tuple[bool, dict]
            (충돌 여부, 통계 딕셔너리)
        """
        # 1. UAV 스케줄 생성
        flights = self.create_uav_schedule(total_hours, uavs_per_hour)
        
        if verbose:
            print(f"총 {len(flights)}대 UAV 스케줄 생성 완료")
        
        # 2. 시간별 시뮬레이션
        total_minutes = total_hours * 60
        collision_detected = False
        max_active_uavs = 0
        collision_time = None
        
        for t in np.arange(0, total_minutes, self.time_step):
            # 현재 활성 UAV 수 카운트
            active_count = sum(
                1 for f in flights
                if f.start_time <= t <= f.end_time
            )
            max_active_uavs = max(max_active_uavs, active_count)
            
            # 충돌 확인
            if self.check_collision(flights, t):
                collision_detected = True
                collision_time = t
                if verbose:
                    print(f"⚠️  충돌 발생! (시간: {t:.1f}분, 활성 UAV: {active_count}대)")
                break
        
        # 3. 통계 수집
        stats = {
            'collision': collision_detected,
            'collision_time': collision_time,
            'total_uavs': len(flights),
            'max_active_uavs': max_active_uavs
        }
        
        return collision_detected, stats
    
    def run_monte_carlo(
        self,
        n_trials: int = 1000,
        total_hours: int = 8,
        uavs_per_hour: int = 20,
        verbose: bool = True
    ) -> dict:
        """
        Monte Carlo 시뮬레이션 실행
        
        Parameters
        ----------
        n_trials : int
            시뮬레이션 시행 횟수
        total_hours : int
            총 운영 시간 (시간)
        uavs_per_hour : int
            시간당 UAV 수
        verbose : bool
            진행상황 출력 여부
            
        Returns
        -------
        dict
            결과 딕셔너리
        """
        if verbose:
            print("=" * 70)
            print("Monte Carlo UAV 충돌 시뮬레이션")
            print("=" * 70)
            print(f"시행 횟수: {n_trials}")
            print(f"운영 시간: {total_hours} 시간")
            print(f"시간당 UAV: {uavs_per_hour} 대")
            print(f"총 UAV: {total_hours * uavs_per_hour} 대 (시간적 분리)")
            print(f"공역 크기: {self.airspace_size[0]:.2f} × {self.airspace_size[1]:.2f} km")
            print(f"안전 거리: {self.safe_distance*1000:.0f}m")
            print(f"GPS 오차: ±{self.gps_noise_std*1000:.0f}m")
            print("=" * 70)
            print()
        
        start_time = time.time()
        collision_count = 0
        all_stats = []
        
        for trial in range(n_trials):
            collision, stats = self.run_single_trial(
                total_hours, uavs_per_hour, verbose=False
            )
            
            if collision:
                collision_count += 1
            
            all_stats.append(stats)
            
            # 진행상황 표시
            if verbose and (trial + 1) % 100 == 0:
                progress = (trial + 1) / n_trials * 100
                current_prob = collision_count / (trial + 1) * 100
                print(f"진행: {trial + 1}/{n_trials} ({progress:.0f}%) | "
                      f"현재 충돌 확률: {current_prob:.2f}%")
        
        elapsed_time = time.time() - start_time
        
        # 최종 결과
        collision_probability = collision_count / n_trials
        
        # 통계 집계
        max_active_list = [s['max_active_uavs'] for s in all_stats]
        avg_max_active = np.mean(max_active_list)
        
        results = {
            'n_trials': n_trials,
            'collision_count': collision_count,
            'collision_probability': collision_probability,
            'total_hours': total_hours,
            'uavs_per_hour': uavs_per_hour,
            'total_uavs': total_hours * uavs_per_hour,
            'avg_max_active_uavs': avg_max_active,
            'elapsed_time': elapsed_time,
            'all_stats': all_stats
        }
        
        if verbose:
            print()
            print("=" * 70)
            print("시뮬레이션 결과")
            print("=" * 70)
            print(f"충돌 발생: {collision_count} / {n_trials} 시행")
            print(f"충돌 확률: {collision_probability*100:.2f}%")
            print(f"평균 최대 동시 비행 UAV: {avg_max_active:.1f} 대")
            print(f"소요 시간: {elapsed_time:.2f}초")
            print("=" * 70)
        
        return results


def main():
    """예시 실행"""
    
    # 시뮬레이터 생성
    simulator = MonteCarloSimulator(
        airspace_size=(1.5, 0.9, 0.15),  # 1500m × 900m × 150m
        base_position=(0.75, 0.05, 0.075),  # 중앙 하단
        max_delivery_distance=1.5,  # 최대 1.5km 배송
        safe_distance=0.05,  # 50m 안전 거리
        gps_noise_std=0.005,  # ±5m GPS 오차
        cruise_speed=1.0,  # 60 km/h
        time_step=0.1  # 6초 간격
    )
    
    # Monte Carlo 시뮬레이션 실행
    results = simulator.run_monte_carlo(
        n_trials=1000,  # 1000번 시행
        total_hours=8,  # 8시간 운영
        uavs_per_hour=20,  # 시간당 20대
        verbose=True
    )
    
    return results


if __name__ == "__main__":
    results = main()
