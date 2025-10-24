"""
충돌 확률 계산 예제

논문의 파라미터를 사용하여 다양한 시나리오의 충돌 확률을 계산합니다.
"""

import numpy as np
from core.safety_envelope import SafetyEnvelope
from core.conflict_probability import ConflictProbabilityCalculator


def main():
    print("=" * 70)
    print("UAV 충돌 확률 계산 예제")
    print("=" * 70)
    
    # 1. 안전 엔벨로프 생성
    print("\n1. 안전 엔벨로프 생성 (논문 Table 1)")
    envelope = SafetyEnvelope(
        Vf=5.0, Vb=2.0, Va=0.9, Vd=1.5, Vl=3.0,
        response_time=60
    )
    print(f"  등가 반경: r_eq = {envelope.compute_equivalent_radius():.3f} km")
    
    # 2. 충돌 확률 계산기 생성
    print("\n2. 충돌 확률 계산기 생성")
    calculator = ConflictProbabilityCalculator(
        safety_envelope=envelope,
        r_A1=0.2,  # along-track 분산 성장률
        r_A2=0.1,  # cross-track 분산 성장률 1
        r_A3=0.1   # cross-track 분산 성장률 2
    )
    print(calculator)
    
    # 3. 기본 함수 테스트
    print("\n3. 기본 함수 테스트")
    
    # Eq. (27) - p_k(t)
    t = 1.0
    r1 = 1.0
    k_norm = 0.5
    p_k = calculator.compute_p_k(t, r1, k_norm)
    print(f"\n  Eq. (27) - p_k(t={t:.1f}):")
    print(f"    r1={r1:.1f}, ||k||={k_norm:.1f}")
    print(f"    p_k = {p_k:.6f}")
    
    # Eq. (28) - ∫p_k(t)dt
    T = 2.0
    integral_p_k = calculator.integrate_p_k(T, r1, k_norm)
    print(f"\n  Eq. (28) - ∫₀^T p_k(t)dt:")
    print(f"    T={T:.1f}")
    print(f"    ∫p_k = {integral_p_k:.6f}")
    
    # Eq. (29) - ∫t·p_k(t)dt
    integral_t_p_k = calculator.integrate_t_p_k(T, r1, k_norm)
    print(f"\n  Eq. (29) - ∫₀^T t·p_k(t)dt:")
    print(f"    ∫t·p_k = {integral_t_p_k:.6f}")
    
    # Eq. (30) - T_h
    t0 = 0.5
    delta_t = 1.5
    T_h = calculator.compute_T_h(t0, delta_t, r1, k_norm)
    print(f"\n  Eq. (30) - 대표 시간 T_h:")
    print(f"    t0={t0:.1f}, Δt={delta_t:.1f}")
    print(f"    T_h = {T_h:.6f} min")
    print(f"    (구간 [{t0:.1f}, {t0+delta_t:.1f}] 내)")
    
    # Eq. (34) - 투영 확률
    l2 = 0.5
    l3 = 0.3
    r_eq = envelope.compute_equivalent_radius()
    p_proj = calculator.compute_projection_probability(T_h, l2, l3, r_eq)
    print(f"\n  Eq. (34) - 투영 확률 p(T_h):")
    print(f"    l2={l2:.1f}, l3={l3:.1f}, r_eq={r_eq:.3f}")
    print(f"    p(T_h) = {p_proj:.6e}")
    
    # 4. 충돌 확률 계산 시나리오
    print("\n4. 충돌 확률 계산 시나리오")
    
    # UAV 설정
    X_A0 = np.array([50.0, 0.0, 5.0])  # 초기 위치
    v_A = np.array([0.0, 10.0, 0.0])   # 속도 (y 방향으로 10 km/min)
    t0 = 0.0
    delta_t = 1.0  # 1분 구간
    
    print(f"\n  UAV 설정:")
    print(f"    초기 위치: {X_A0}")
    print(f"    속도: {v_A} km/min")
    print(f"    시간 구간: [{t0:.1f}, {t0+delta_t:.1f}] min")
    
    # 테스트 포인트들
    test_scenarios = [
        {
            'name': '시나리오 1: UAV 경로 상 (직진)',
            'X': np.array([50.0, 10.0, 5.0]),
            'description': 'UAV가 1분 후 도달할 위치'
        },
        {
            'name': '시나리오 2: 경로 근처 (횡방향 1km)',
            'X': np.array([51.0, 10.0, 5.0]),
            'description': '경로에서 횡방향으로 1km 떨어진 지점'
        },
        {
            'name': '시나리오 3: 경로 위 (상승 1km)',
            'X': np.array([50.0, 10.0, 6.0]),
            'description': '경로 상에서 1km 상승한 지점'
        },
        {
            'name': '시나리오 4: 먼 거리',
            'X': np.array([60.0, 20.0, 10.0]),
            'description': '경로에서 멀리 떨어진 지점'
        },
        {
            'name': '시나리오 5: 매우 가까운 거리',
            'X': np.array([50.5, 5.0, 5.0]),
            'description': 'UAV 시작 위치 근처'
        },
    ]
    
    print("\n  " + "=" * 66)
    print("  시나리오                                충돌 확률")
    print("  " + "=" * 66)
    
    for scenario in test_scenarios:
        X = scenario['X']
        prob = calculator.compute_conflict_probability(
            X, X_A0, v_A, t0, delta_t
        )
        
        print(f"\n  {scenario['name']}")
        print(f"  좌표: {X}")
        print(f"  설명: {scenario['description']}")
        print(f"  충돌 확률: {prob:.6e} ({prob*100:.6f}%)")
    
    # 5. 시간 구간 변화에 따른 확률
    print("\n5. 시간 구간 변화에 따른 충돌 확률")
    X_test = np.array([50.0, 10.0, 5.0])
    print(f"  테스트 좌표: {X_test}")
    print(f"  UAV 초기 위치: {X_A0}")
    print(f"  UAV 속도: {v_A} km/min")
    
    print("\n  시간 구간 (min)    충돌 확률")
    print("  " + "-" * 40)
    for dt in [0.5, 1.0, 2.0, 3.0, 5.0]:
        prob = calculator.compute_conflict_probability(
            X_test, X_A0, v_A, 0.0, dt
        )
        print(f"  [0.0, {dt:4.1f}]        {prob:.6e} ({prob*100:.6f}%)")
    
    # 6. 속도 변화에 따른 확률
    print("\n6. 속도 변화에 따른 충돌 확률")
    X_test = np.array([50.0, 5.0, 5.0])
    print(f"  테스트 좌표: {X_test}")
    print(f"  시간 구간: [0.0, 1.0] min")
    
    velocities = [
        np.array([0.0, 5.0, 0.0]),
        np.array([0.0, 10.0, 0.0]),
        np.array([0.0, 15.0, 0.0]),
        np.array([5.0, 5.0, 0.0]),
        np.array([10.0, 0.0, 0.0]),
    ]
    
    print("\n  속도 (km/min)              충돌 확률")
    print("  " + "-" * 50)
    for v in velocities:
        prob = calculator.compute_conflict_probability(
            X_test, X_A0, v, 0.0, 1.0
        )
        print(f"  {str(v):25s} {prob:.6e} ({prob*100:.6f}%)")
    
    # 7. 분산 성장률 비교
    print("\n7. 분산 성장률에 따른 충돌 확률 비교")
    X_test = np.array([50.0, 10.0, 5.0])
    
    uncertainty_scenarios = [
        {'r_A1': 0.1, 'r_A2': 0.05, 'r_A3': 0.05, 'name': '낮은 불확실성'},
        {'r_A1': 0.2, 'r_A2': 0.1, 'r_A3': 0.1, 'name': '중간 불확실성 (기본)'},
        {'r_A1': 0.4, 'r_A2': 0.2, 'r_A3': 0.2, 'name': '높은 불확실성'},
    ]
    
    print(f"  테스트 좌표: {X_test}")
    print("\n  불확실성 수준              r_A1   r_A2   r_A3   충돌 확률")
    print("  " + "-" * 70)
    
    for scenario in uncertainty_scenarios:
        calc = ConflictProbabilityCalculator(
            envelope,
            r_A1=scenario['r_A1'],
            r_A2=scenario['r_A2'],
            r_A3=scenario['r_A3']
        )
        prob = calc.compute_conflict_probability(
            X_test, X_A0, v_A, 0.0, 1.0
        )
        print(f"  {scenario['name']:25s} {scenario['r_A1']:.2f}  "
              f"{scenario['r_A2']:.2f}  {scenario['r_A3']:.2f}  "
              f"{prob:.6e} ({prob*100:.6f}%)")
    
    print("\n" + "=" * 70)
    print("예제 완료!")
    print("=" * 70)


if __name__ == "__main__":
    main()
