"""
공역 안전 필드 생성 예제

3D 공역 그리드를 생성하고 다중 UAV에 대한 안전 필드를 계산합니다.
"""

import numpy as np
from core.safety_field import UAV, AirspaceSafetyField


def main():
    print("=" * 70)
    print("공역 안전 필드 생성 예제")
    print("=" * 70)
    
    # 1. 공역 정의
    print("\n1. 공역 정의")
    bounds = {
        'x': (45.0, 55.0),  # 10 km
        'y': (0.0, 20.0),   # 20 km
        'z': (0.0, 10.0)    # 10 km
    }
    grid_resolution = 2.0  # 2 km 해상도 (빠른 계산을 위해)
    
    print(f"  공역 범위:")
    print(f"    X: [{bounds['x'][0]}, {bounds['x'][1]}] km")
    print(f"    Y: [{bounds['y'][0]}, {bounds['y'][1]}] km")
    print(f"    Z: [{bounds['z'][0]}, {bounds['z'][1]}] km")
    print(f"  그리드 해상도: {grid_resolution} km")
    
    # 2. 안전 필드 객체 생성
    print("\n2. 안전 필드 객체 생성")
    safety_field = AirspaceSafetyField(
        bounds=bounds,
        grid_resolution=grid_resolution,
        r_A1=0.2,  # along-track 불확실성
        r_A2=0.1,  # cross-track 불확실성 1
        r_A3=0.1   # cross-track 불확실성 2
    )
    print(safety_field)
    
    # 3. UAV 정의
    print("\n3. UAV 정의")
    
    # UAV 1: 남쪽에서 북쪽으로 이동
    uav1 = UAV(
        id=1,
        position=np.array([50.0, 0.0, 5.0]),
        velocity=np.array([0.0, 10.0, 0.0]),  # 북쪽으로 10 km/min
        Vf=5.0, Vb=2.0, Va=0.9, Vd=1.5, Vl=3.0,
        response_time=60
    )
    
    print(f"\n  UAV 1:")
    print(f"    위치: {uav1.position} km")
    print(f"    속도: {uav1.velocity} km/min")
    print(f"    성능: Vf={uav1.Vf}, Vb={uav1.Vb}, Va={uav1.Va}, "
          f"Vd={uav1.Vd}, Vl={uav1.Vl} km/min")
    
    # UAV 2: 서쪽에서 동쪽으로 이동
    uav2 = UAV(
        id=2,
        position=np.array([45.0, 10.0, 5.0]),
        velocity=np.array([5.0, 0.0, 0.0]),  # 동쪽으로 5 km/min
        Vf=5.0, Vb=2.0, Va=0.9, Vd=1.5, Vl=3.0,
        response_time=60
    )
    
    print(f"\n  UAV 2:")
    print(f"    위치: {uav2.position} km")
    print(f"    속도: {uav2.velocity} km/min")
    
    uavs = [uav1, uav2]
    
    # 4. 안전 필드 계산 - 단일 UAV
    print("\n4. 안전 필드 계산 - 단일 UAV")
    print("  (빠른 계산을 위해 작은 그리드 사용)")
    
    field_single = safety_field.compute_field(
        uavs=[uav1],
        t0=0.0,
        delta_t=1.0,
        parallel=False,  # 작은 그리드는 순차 처리가 더 빠름
        verbose=True
    )
    
    print(f"\n  계산 완료! 필드 shape: {field_single.shape}")
    
    # 5. 통계 확인
    print("\n5. 단일 UAV 안전 필드 통계")
    stats_single = safety_field.get_statistics()
    print(f"  최대 충돌 확률: {stats_single['max']:.6e} ({stats_single['max']*100:.4f}%)")
    print(f"  평균 충돌 확률: {stats_single['mean']:.6e} ({stats_single['mean']*100:.4f}%)")
    print(f"  중간값: {stats_single['median']:.6e}")
    print(f"  표준편차: {stats_single['std']:.6e}")
    print(f"  위험 셀 (>1%): {stats_single['dangerous_cells_1pct']} 개")
    print(f"  위험 셀 (>5%): {stats_single['dangerous_cells_5pct']} 개")
    
    # 6. 특정 위치 조회
    print("\n6. 특정 위치의 충돌 확률 조회")
    
    test_positions = [
        (np.array([50.0, 5.0, 5.0]), "UAV1 경로 상 (5km 북쪽)"),
        (np.array([50.0, 10.0, 5.0]), "UAV1 경로 상 (10km 북쪽)"),
        (np.array([52.0, 5.0, 5.0]), "UAV1 경로 동쪽 2km"),
        (np.array([48.0, 5.0, 5.0]), "UAV1 경로 서쪽 2km"),
        (np.array([50.0, 5.0, 7.0]), "UAV1 경로 상공 2km"),
    ]
    
    print("\n  위치                                   충돌 확률")
    print("  " + "-" * 64)
    for position, description in test_positions:
        try:
            prob = safety_field.get_value_at_position(position)
            print(f"  {description:35s} {prob:.6e} ({prob*100:.4f}%)")
        except ValueError as e:
            print(f"  {description:35s} 범위 밖")
    
    # 7. 위험 영역 추출
    print("\n7. 위험 영역 추출 (>0.1% 충돌 확률)")
    dangerous_regions = safety_field.get_dangerous_regions(threshold=0.001)
    
    print(f"  위험 영역 수: {len(dangerous_regions)}")
    if len(dangerous_regions) > 0:
        print(f"\n  처음 5개 위험 영역:")
        print("    X (km)    Y (km)    Z (km)")
        print("  " + "-" * 35)
        for i, pos in enumerate(dangerous_regions[:5]):
            print(f"  {pos[0]:8.2f}  {pos[1]:8.2f}  {pos[2]:8.2f}")
    
    # 8. 다중 UAV 안전 필드 계산 (Eq. 9)
    print("\n8. 다중 UAV 안전 필드 계산 (Eq. 9)")
    print("  2대의 UAV에 대한 결합 확률 계산")
    
    field_multi = safety_field.compute_field(
        uavs=uavs,  # 2대의 UAV
        t0=0.0,
        delta_t=1.0,
        parallel=False,
        verbose=True
    )
    
    # 9. 다중 UAV 통계
    print("\n9. 다중 UAV 안전 필드 통계")
    stats_multi = safety_field.get_statistics()
    print(f"  최대 충돌 확률: {stats_multi['max']:.6e} ({stats_multi['max']*100:.4f}%)")
    print(f"  평균 충돌 확률: {stats_multi['mean']:.6e} ({stats_multi['mean']*100:.4f}%)")
    print(f"  위험 셀 (>1%): {stats_multi['dangerous_cells_1pct']} 개")
    
    # 10. 단일 vs 다중 UAV 비교
    print("\n10. 단일 vs 다중 UAV 비교")
    print("\n  메트릭                     단일 UAV        다중 UAV        증가율")
    print("  " + "=" * 70)
    
    max_increase = (stats_multi['max'] / stats_single['max'] - 1) * 100 if stats_single['max'] > 0 else 0
    mean_increase = (stats_multi['mean'] / stats_single['mean'] - 1) * 100 if stats_single['mean'] > 0 else 0
    danger_increase = (stats_multi['dangerous_cells_1pct'] / stats_single['dangerous_cells_1pct'] - 1) * 100 \
                      if stats_single['dangerous_cells_1pct'] > 0 else 0
    
    print(f"  최대 충돌 확률        {stats_single['max']:.6e}  {stats_multi['max']:.6e}  {max_increase:+.1f}%")
    print(f"  평균 충돌 확률        {stats_single['mean']:.6e}  {stats_multi['mean']:.6e}  {mean_increase:+.1f}%")
    print(f"  위험 셀 수 (>1%)      {stats_single['dangerous_cells_1pct']:8d}    "
          f"{stats_multi['dangerous_cells_1pct']:8d}    {danger_increase:+.1f}%")
    
    # 11. 교차점 근처 확률 비교
    print("\n11. UAV 경로 교차 지점 분석")
    # UAV1은 (50, y, 5) 경로, UAV2는 (x, 10, 5) 경로
    # 교차점: (50, 10, 5)
    
    intersection = np.array([50.0, 10.0, 5.0])
    nearby_points = [
        (np.array([50.0, 10.0, 5.0]), "교차점"),
        (np.array([50.0, 8.0, 5.0]), "교차점 남쪽 2km"),
        (np.array([50.0, 12.0, 5.0]), "교차점 북쪽 2km"),
        (np.array([48.0, 10.0, 5.0]), "교차점 서쪽 2km"),
        (np.array([52.0, 10.0, 5.0]), "교차점 동쪽 2km"),
    ]
    
    print("\n  위치                      충돌 확률")
    print("  " + "-" * 50)
    for position, description in nearby_points:
        try:
            prob = safety_field.get_value_at_position(position)
            print(f"  {description:25s} {prob:.6e} ({prob*100:.4f}%)")
        except ValueError:
            print(f"  {description:25s} 범위 밖")
    
    # 12. 그리드 인덱스 변환 예제
    print("\n12. 좌표 ↔ 그리드 인덱스 변환 예제")
    position = np.array([50.0, 10.0, 5.0])
    idx = safety_field.position_to_index(position)
    recovered_position = safety_field.index_to_position(idx)
    
    print(f"  원본 좌표: {position}")
    print(f"  그리드 인덱스: {idx}")
    print(f"  복원 좌표: {recovered_position}")
    print(f"  오차: {np.linalg.norm(position - recovered_position):.6f} km")
    
    print("\n" + "=" * 70)
    print("예제 완료!")
    print("=" * 70)
    
    print("\n💡 참고:")
    print("  - 실제 응용에서는 더 높은 해상도 (0.1-0.5 km)를 사용하세요")
    print("  - 병렬 처리(parallel=True)는 큰 그리드에서 효과적입니다")
    print("  - 안전 필드는 경로 계획 및 충돌 회피에 사용됩니다")


if __name__ == "__main__":
    main()
