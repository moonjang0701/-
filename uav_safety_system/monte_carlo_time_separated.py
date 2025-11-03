"""
Monte Carlo UAV 충돌 시뮬레이터 - 진짜 시간적 분리 버전

핵심 아이디어:
- 각 타임 슬롯(1시간)은 완전히 독립적
- 한 타임 슬롯 내에서만 충돌 검사
- 8개 타임 슬롯 중 하나라도 충돌 → 전체 충돌
"""

import numpy as np
from dataclasses import dataclass
from typing import List, Tuple
import time

@dataclass
class UAVFlight:
    """단일 UAV 비행 정보"""
    uav_id: int
    start_time: float        # 타임슬롯 내 출발 시간 (분)
    end_time: float          # 타임슬롯 내 도착 시간 (분)
    start_pos: np.ndarray    # 출발 위치 [x, y, z] (km)
    end_pos: np.ndarray      # 도착 위치 [x, y, z] (km)
    
    def get_position(self, t: float, gps_noise_std: float = 0.005) -> np.ndarray:
        """
        타임슬롯 내 시간 t에서의 위치 (GPS 오차 포함)
        """
        if t < self.start_time or t > self.end_time:
            return None
        
        progress = (t - self.start_time) / (self.end_time - self.start_time)
        pos = self.start_pos + progress * (self.end_pos - self.start_pos)
        
        # GPS 오차
        noise = np.array([
            np.random.normal(0, gps_noise_std),
            np.random.normal(0, gps_noise_std),
            0
        ])
        
        return pos + noise


class MonteCarloTimeSeparated:
    """시간 분리 Monte Carlo 시뮬레이터"""
    
    def __init__(
        self,
        airspace_size: Tuple[float, float, float] = (1.5, 0.9, 0.15),
        base_position: Tuple[float, float, float] = (0.75, 0.05, 0.075),
        max_delivery_distance: float = 1.5,
        safe_distance: float = 0.05,
        gps_noise_std: float = 0.005,
        cruise_speed: float = 1.0,
        time_step: float = 0.1  # 6초
    ):
        self.airspace_size = np.array(airspace_size)
        self.base_position = np.array(base_position)
        self.max_delivery_distance = max_delivery_distance
        self.safe_distance = safe_distance
        self.gps_noise_std = gps_noise_std
        self.cruise_speed = cruise_speed
        self.time_step = time_step
    
    def generate_random_destination(self) -> np.ndarray:
        """랜덤 배송 목적지 생성"""
        angle = np.random.uniform(0, 2 * np.pi)
        distance = np.sqrt(np.random.uniform(0, 1)) * self.max_delivery_distance
        
        dx = distance * np.cos(angle)
        dy = distance * np.sin(angle)
        
        dest = self.base_position.copy()
        dest[0] += dx
        dest[1] += dy
        
        dest[0] = np.clip(dest[0], 0, self.airspace_size[0])
        dest[1] = np.clip(dest[1], 0, self.airspace_size[1])
        
        return dest
    
    def create_time_slot_flights(self, num_uavs: int) -> List[UAVFlight]:
        """
        단일 타임슬롯(1시간)용 UAV 생성
        
        핵심: 모든 UAV가 0~60분 내에서 출발하고 도착함
        """
        flights = []
        
        for i in range(num_uavs):
            # 출발 시간: 0~60분 랜덤
            start_time = np.random.uniform(0, 60)
            
            # 목적지
            destination = self.generate_random_destination()
            distance = np.linalg.norm(destination - self.base_position)
            
            # 비행 시간
            flight_duration = distance / self.cruise_speed
            end_time = start_time + flight_duration
            
            # 60분 넘어가면 잘라냄 (타임슬롯 경계 넘지 않음)
            if end_time > 60:
                end_time = 60
            
            flight = UAVFlight(
                uav_id=i,
                start_time=start_time,
                end_time=end_time,
                start_pos=self.base_position.copy(),
                end_pos=destination
            )
            
            flights.append(flight)
        
        return flights
    
    def check_collision_in_slot(self, flights: List[UAVFlight]) -> Tuple[bool, float]:
        """
        단일 타임슬롯 내 충돌 검사
        
        Returns
        -------
        Tuple[bool, float]
            (충돌 여부, 충돌 시간 or None)
        """
        for t in np.arange(0, 60, self.time_step):
            # 현재 비행 중인 UAV 위치들
            active_positions = []
            
            for flight in flights:
                pos = flight.get_position(t, self.gps_noise_std)
                if pos is not None:
                    active_positions.append(pos)
            
            # 충돌 검사
            if len(active_positions) >= 2:
                for i in range(len(active_positions)):
                    for j in range(i + 1, len(active_positions)):
                        distance = np.linalg.norm(
                            active_positions[i] - active_positions[j]
                        )
                        
                        if distance < self.safe_distance:
                            return True, t  # 충돌!
        
        return False, None
    
    def run_single_trial(
        self,
        total_hours: int = 8,
        uavs_per_hour: int = 20,
        verbose: bool = False
    ) -> dict:
        """
        단일 시뮬레이션 시행
        
        각 타임슬롯 독립적으로 시뮬레이션
        """
        collision_by_slot = []
        collision_times = []
        
        for hour in range(total_hours):
            # 이 타임슬롯용 UAV 생성
            flights = self.create_time_slot_flights(uavs_per_hour)
            
            # 충돌 검사
            collision, col_time = self.check_collision_in_slot(flights)
            
            collision_by_slot.append(collision)
            if collision:
                actual_time = hour * 60 + col_time
                collision_times.append(actual_time)
                
                if verbose:
                    print(f"  타임슬롯 {hour} ({hour*60:3d}~{(hour+1)*60:3d}분): "
                          f"⚠️  충돌 발생 (t={actual_time:.1f}분)")
            else:
                if verbose:
                    print(f"  타임슬롯 {hour} ({hour*60:3d}~{(hour+1)*60:3d}분): "
                          f"✅ 안전")
        
        # 전체 충돌 여부: 하나라도 충돌 → 전체 충돌
        overall_collision = any(collision_by_slot)
        
        stats = {
            'collision': overall_collision,
            'collision_by_slot': collision_by_slot,
            'collision_times': collision_times,
            'num_collisions': sum(collision_by_slot),
            'total_uavs': total_hours * uavs_per_hour
        }
        
        return stats
    
    def run_monte_carlo(
        self,
        n_trials: int = 1000,
        total_hours: int = 8,
        uavs_per_hour: int = 20,
        verbose: bool = True
    ) -> dict:
        """Monte Carlo 시뮬레이션 (시간 분리)"""
        
        if verbose:
            print("=" * 70)
            print("Monte Carlo 시뮬레이션 - 진짜 시간적 분리")
            print("=" * 70)
            print(f"시행 횟수: {n_trials}")
            print(f"타임슬롯: {total_hours}개 (각 1시간)")
            print(f"타임슬롯당 UAV: {uavs_per_hour}대")
            print(f"총 UAV: {total_hours * uavs_per_hour}대")
            print(f"공역: {self.airspace_size[0]:.2f} × {self.airspace_size[1]:.2f} km")
            print(f"안전 거리: {self.safe_distance*1000:.0f}m")
            print()
            print("핵심 개념:")
            print("  - 각 타임슬롯은 독립적 (1시간 단위)")
            print("  - 타임슬롯 내에서만 동시 비행")
            print("  - 타임슬롯 간 충돌 없음 (완전 분리)")
            print("=" * 70)
            print()
        
        start_time = time.time()
        collision_count = 0
        slot_collision_counts = [0] * total_hours
        all_stats = []
        
        for trial in range(n_trials):
            stats = self.run_single_trial(
                total_hours, uavs_per_hour, verbose=False
            )
            
            if stats['collision']:
                collision_count += 1
            
            # 슬롯별 충돌 집계
            for slot_idx, collision in enumerate(stats['collision_by_slot']):
                if collision:
                    slot_collision_counts[slot_idx] += 1
            
            all_stats.append(stats)
            
            if verbose and (trial + 1) % 100 == 0:
                progress = (trial + 1) / n_trials * 100
                current_prob = collision_count / (trial + 1) * 100
                print(f"진행: {trial + 1}/{n_trials} ({progress:.0f}%) | "
                      f"충돌 확률: {current_prob:.2f}%")
        
        elapsed_time = time.time() - start_time
        
        # 결과 집계
        collision_probability = collision_count / n_trials
        slot_probabilities = [c / n_trials for c in slot_collision_counts]
        
        results = {
            'n_trials': n_trials,
            'collision_count': collision_count,
            'collision_probability': collision_probability,
            'slot_probabilities': slot_probabilities,
            'total_hours': total_hours,
            'uavs_per_hour': uavs_per_hour,
            'elapsed_time': elapsed_time,
            'all_stats': all_stats
        }
        
        if verbose:
            print()
            print("=" * 70)
            print("결과")
            print("=" * 70)
            print(f"전체 충돌 확률: {collision_probability*100:.2f}%")
            print(f"  (8개 타임슬롯 중 하나라도 충돌)")
            print()
            print("타임슬롯별 충돌 확률:")
            for i, prob in enumerate(slot_probabilities):
                print(f"  슬롯 {i} ({i*60:3d}~{(i+1)*60:3d}분): {prob*100:.2f}%")
            print()
            print(f"평균 슬롯 충돌 확률: {np.mean(slot_probabilities)*100:.2f}%")
            print(f"소요 시간: {elapsed_time:.2f}초")
            print("=" * 70)
        
        return results


def main():
    """예시 실행"""
    
    print("=" * 70)
    print("시간적 분리 비교")
    print("=" * 70)
    print()
    
    # 시뮬레이터 생성
    simulator = MonteCarloTimeSeparated(
        airspace_size=(1.5, 0.9, 0.15),
        safe_distance=0.05,
        gps_noise_std=0.005
    )
    
    # 시나리오 1: 시간당 20대
    print("📊 시나리오: 시간당 20대")
    print()
    results = simulator.run_monte_carlo(
        n_trials=1000,
        total_hours=8,
        uavs_per_hour=20
    )
    
    return results


if __name__ == "__main__":
    results = main()
