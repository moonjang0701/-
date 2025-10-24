"""
안전 엔벨로프 클래스 사용 예제

논문 Table 1의 파라미터를 사용하여 안전 엔벨로프를 생성하고
주요 기능을 테스트합니다.
"""

import numpy as np
from core.safety_envelope import SafetyEnvelope


def main():
    print("=" * 70)
    print("UAV 안전 엔벨로프 예제")
    print("=" * 70)
    
    # 논문 Table 1 파라미터로 안전 엔벨로프 생성
    print("\n1. 안전 엔벨로프 생성 (논문 Table 1 파라미터)")
    envelope = SafetyEnvelope(
        Vf=5.0,  # 최대 전방 속도 (km/min)
        Vb=2.0,  # 최대 후방 속도 (km/min)
        Va=0.9,  # 최대 상승 속도 (km/min)
        Vd=1.5,  # 최대 하강 속도 (km/min)
        Vl=3.0,  # 최대 횡방향 속도 (km/min)
        response_time=60  # 응답 시간 (seconds)
    )
    
    print(envelope)
    
    # 각 방향 최대 도달 거리
    print("\n2. 각 방향 최대 도달 거리 (Eq. 1)")
    axes = envelope.compute_axes()
    print(f"  전방 (a): {axes['a']:.3f} km")
    print(f"  후방 (b): {axes['b']:.3f} km")
    print(f"  상승 (c): {axes['c']:.3f} km")
    print(f"  하강 (d): {axes['d']:.3f} km")
    print(f"  횡방향 (e=f): {axes['e']:.3f} km")
    
    # 등가 구 반경
    print("\n3. 등가 구 반경 (Eq. 24)")
    r_eq = envelope.compute_equivalent_radius()
    print(f"  r_eq = {r_eq:.3f} km")
    
    # 엔벨로프 부피
    print("\n4. 엔벨로프 부피 (Eq. 22)")
    volume = envelope.get_volume()
    print(f"  Volume = {volume:.3f} km³")
    
    # 점 내부/외부 판정 테스트
    print("\n5. 점 내부/외부 판정 테스트 (Eq. 5)")
    X_A = np.array([50.0, 5.0, 5.0])  # UAV 위치
    print(f"  UAV 위치: {X_A}")
    
    test_points = [
        (np.array([50.0, 5.0, 5.0]), "UAV 중심"),
        (np.array([54.0, 5.0, 5.0]), "전방 4km"),
        (np.array([56.0, 5.0, 5.0]), "전방 6km (외부)"),
        (np.array([48.5, 5.0, 5.0]), "후방 1.5km"),
        (np.array([47.0, 5.0, 5.0]), "후방 3km (외부)"),
        (np.array([50.0, 5.0, 5.5]), "상승 0.5km"),
        (np.array([50.0, 5.0, 6.5]), "상승 1.5km (외부)"),
        (np.array([50.0, 7.0, 5.0]), "횡방향 2km"),
        (np.array([52.0, 6.0, 5.5]), "복합 (2, 1, 0.5)"),
    ]
    
    print("\n  점 위치                    내부 여부   거리")
    print("  " + "-" * 60)
    for X, desc in test_points:
        is_inside = envelope.is_inside(X, X_A)
        distance = envelope.get_distance_to_surface(X, X_A)
        status = "내부" if is_inside else "외부"
        print(f"  {desc:25s} {status:6s}    {distance:.3f}")
    
    # 사분면별 행렬 확인
    print("\n6. 사분면별 행렬 M (Eq. 3-4)")
    quadrant_points = [
        (np.array([55.0, 5.0, 6.0]), "M₁ (전방-상승)"),
        (np.array([55.0, 5.0, 4.0]), "M₂ (전방-하강)"),
        (np.array([45.0, 5.0, 6.0]), "M₃ (후방-상승)"),
        (np.array([45.0, 5.0, 4.0]), "M₄ (후방-하강)"),
    ]
    
    for X, desc in quadrant_points:
        M = envelope.get_matrix_M(X, X_A)
        print(f"\n  {desc}:")
        print(f"    대각 원소: [{M[0,0]:.4f}, {M[1,1]:.4f}, {M[2,2]:.4f}]")
    
    # 다른 응답 시간 비교
    print("\n7. 다른 응답 시간 비교")
    envelope_30s = SafetyEnvelope(
        Vf=5.0, Vb=2.0, Va=0.9, Vd=1.5, Vl=3.0,
        response_time=30
    )
    envelope_120s = SafetyEnvelope(
        Vf=5.0, Vb=2.0, Va=0.9, Vd=1.5, Vl=3.0,
        response_time=120
    )
    
    print(f"  30초:  r_eq = {envelope_30s.compute_equivalent_radius():.3f} km, "
          f"Volume = {envelope_30s.get_volume():.3f} km³")
    print(f"  60초:  r_eq = {envelope.compute_equivalent_radius():.3f} km, "
          f"Volume = {envelope.get_volume():.3f} km³")
    print(f"  120초: r_eq = {envelope_120s.compute_equivalent_radius():.3f} km, "
          f"Volume = {envelope_120s.get_volume():.3f} km³")
    
    print("\n" + "=" * 70)
    print("예제 완료!")
    print("=" * 70)


if __name__ == "__main__":
    main()
