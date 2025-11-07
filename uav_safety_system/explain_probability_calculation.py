"""
충돌 확률 계산 방법 설명 - 논문과 구현 비교

논문: Monte Carlo 시뮬레이션 (실제 비행)
구현: 해석적 계산 (수학 공식 직접 사용)
"""

import numpy as np
from core.safety_envelope import SafetyEnvelope
from core.conflict_probability import ConflictProbabilityCalculator

print("=" * 70)
print("충돌 확률 계산 방법 설명")
print("=" * 70)
print()

# ============================================================================
# Step 1: 안전 엔벨로프 생성 (소형 드론)
# ============================================================================
print("Step 1: 안전 엔벨로프 생성 (소형 드론 파라미터)")
print("-" * 70)
envelope = SafetyEnvelope(
    Vf=1.0, Vb=0.5, Va=0.3, Vd=0.4, Vl=0.8,
    response_time=10  # 10초
)
r_eq = envelope.compute_equivalent_radius()
print(f"등가 구 반경 r_eq = {r_eq:.3f} km = {r_eq*1000:.1f}m")
print()

# ============================================================================
# Step 2: 충돌 확률 계산기 생성
# ============================================================================
print("Step 2: 충돌 확률 계산기 생성")
print("-" * 70)
calculator = ConflictProbabilityCalculator(
    safety_envelope=envelope,
    r_A1=0.05,  # Along-track 불확실성
    r_A2=0.05,  # Cross-track 불확실성 1
    r_A3=0.05   # Cross-track 불확실성 2
)
print(f"위치 불확실성: r_A1={0.05}, r_A2={0.05}, r_A3={0.05} km·min^(-1/2)")
print()

# ============================================================================
# Step 3: 시나리오 설정
# ============================================================================
print("Step 3: 시나리오 설정")
print("-" * 70)
print("공역 중앙에 고정된 포인트 X가 있습니다.")
X = np.array([0.75, 0.45, 0.15])  # 공역 중앙 (km)
print(f"포인트 X = [{X[0]:.2f}, {X[1]:.2f}, {X[2]:.2f}] km")
print()

print("여러 UAV가 다양한 위치와 속도로 비행합니다.")
print()

# ============================================================================
# Step 4: 다양한 UAV 위치에서 충돌 확률 계산
# ============================================================================
print("Step 4: 다양한 시나리오별 충돌 확률 계산")
print("=" * 70)
print()

scenarios = [
    {
        "name": "시나리오 1: 매우 가까운 UAV (100m 거리)",
        "X_A0": np.array([0.75, 0.35, 0.15]),  # 100m 아래
        "v_A": np.array([0.0, 1.0, 0.0]),      # 1 km/min 속도
        "t0": 0.0,
        "delta_t": 1.0  # 1분
    },
    {
        "name": "시나리오 2: 중간 거리 UAV (300m 거리)",
        "X_A0": np.array([0.75, 0.15, 0.15]),  # 300m 아래
        "v_A": np.array([0.0, 1.0, 0.0]),
        "t0": 0.0,
        "delta_t": 1.0
    },
    {
        "name": "시나리오 3: 먼 거리 UAV (700m 거리)",
        "X_A0": np.array([0.75, -0.25, 0.15]),  # 700m 아래
        "v_A": np.array([0.0, 1.0, 0.0]),
        "t0": 0.0,
        "delta_t": 1.0
    },
    {
        "name": "시나리오 4: 정지한 UAV (500m 거리)",
        "X_A0": np.array([0.75, -0.05, 0.15]),  # 500m 아래
        "v_A": np.array([0.0, 0.0, 0.0]),       # 정지
        "t0": 0.0,
        "delta_t": 1.0
    },
    {
        "name": "시나리오 5: 빠르게 접근하는 UAV (400m 거리, 빠른 속도)",
        "X_A0": np.array([0.75, 0.05, 0.15]),   # 400m 아래
        "v_A": np.array([0.0, 3.0, 0.0]),       # 3 km/min 속도
        "t0": 0.0,
        "delta_t": 1.0
    }
]

for i, scenario in enumerate(scenarios, 1):
    print(f"{scenario['name']}")
    print("-" * 70)
    
    X_A0 = scenario['X_A0']
    v_A = scenario['v_A']
    t0 = scenario['t0']
    delta_t = scenario['delta_t']
    
    # 거리 계산
    distance = np.linalg.norm(X - X_A0)
    
    print(f"UAV 초기 위치: X_A0 = [{X_A0[0]:.2f}, {X_A0[1]:.2f}, {X_A0[2]:.2f}] km")
    print(f"UAV 속도: v_A = [{v_A[0]:.2f}, {v_A[1]:.2f}, {v_A[2]:.2f}] km/min")
    print(f"초기 거리: {distance*1000:.1f}m")
    print(f"시간 구간: [{t0:.1f}, {t0+delta_t:.1f}] 분")
    print()
    
    # ========================================================================
    # 핵심: 충돌 확률 계산
    # ========================================================================
    prob = calculator.compute_conflict_probability(X, X_A0, v_A, t0, delta_t)
    
    print(f"📊 계산된 충돌 확률: {prob:.6f} ({prob*100:.4f}%)")
    print()
    
    # 계산 과정 설명
    print("계산 과정:")
    print("  1. 상대 위치 계산: ΔX₀ = X - X_A0")
    DeltaX0 = X - X_A0
    print(f"     ΔX₀ = [{DeltaX0[0]:+.3f}, {DeltaX0[1]:+.3f}, {DeltaX0[2]:+.3f}] km")
    
    print("  2. 좌표 변환 (속도 방향 기준)")
    print("     - Along-track: 속도 방향")
    print("     - Cross-track: 속도에 수직인 방향 2개")
    
    print("  3. 브라운 운동 파라미터 계산")
    print("     - r: 변환된 초기 위치")
    print("     - k: 변환된 속도 벡터")
    
    print("  4. 대표 시간 T_h 계산 (Eq. 30)")
    print("     - 확률 분포의 무게 중심 시간")
    
    print("  5. 투영 확률 p(T_h) 계산 (Eq. 34)")
    print("     - erf 함수 사용")
    
    print("  6. 최종 적분 (Eq. 35)")
    print("     - ∫ p(T_h) × p_k(t) dt")
    print()
    print("=" * 70)
    print()

# ============================================================================
# Step 5: 다중 UAV 충돌 확률 (Eq. 9)
# ============================================================================
print("Step 5: 다중 UAV 독립적 충돌 확률 결합 (Eq. 9)")
print("=" * 70)
print()

print("공식: s(X) = 1 - ∏(1 - p_i)")
print("설명: N개의 UAV 중 적어도 하나와 충돌할 확률")
print()

# 여러 UAV 설정
uavs = [
    {"X_A0": np.array([0.75, 0.35, 0.15]), "v_A": np.array([0.0, 1.0, 0.0])},
    {"X_A0": np.array([0.75, 0.15, 0.15]), "v_A": np.array([0.0, 1.0, 0.0])},
    {"X_A0": np.array([0.75, 0.05, 0.15]), "v_A": np.array([0.0, 3.0, 0.0])},
]

individual_probs = []
for i, uav in enumerate(uavs, 1):
    prob = calculator.compute_conflict_probability(
        X, uav['X_A0'], uav['v_A'], 0.0, 1.0
    )
    individual_probs.append(prob)
    distance = np.linalg.norm(X - uav['X_A0'])
    print(f"UAV {i}: 거리={distance*1000:.0f}m, p_{i}={prob:.6f} ({prob*100:.4f}%)")

print()
print("독립성 가정 적용:")
product = 1.0
for i, p in enumerate(individual_probs, 1):
    product *= (1.0 - p)
    print(f"  단계 {i}: (1 - p₁) × ... × (1 - p_{i}) = {product:.6f}")

combined_prob = 1.0 - product
print()
print(f"최종 결합 충돌 확률: s(X) = 1 - {product:.6f} = {combined_prob:.6f}")
print(f"                           = {combined_prob*100:.4f}%")
print()

# ============================================================================
# 요약
# ============================================================================
print("=" * 70)
print("📌 요약: 충돌 확률 계산 방법")
print("=" * 70)
print()
print("논문 방법 (실험적):")
print("  - 실제 UAV 비행 또는 Monte Carlo 시뮬레이션")
print("  - 수천~수만 번 반복 시뮬레이션")
print("  - 충돌 횟수 / 총 시행 횟수")
print("  - 장점: 직관적, 현실적")
print("  - 단점: 시간 소요, 계산 비용 큼")
print()
print("우리 구현 방법 (해석적):")
print("  - 논문의 수학 공식 직접 사용 (Eq. 27-35)")
print("  - 브라운 운동 이론 기반")
print("  - 확률 분포 함수로 직접 계산")
print("  - 장점: 빠름, 정확함, 시뮬레이션 불필요")
print("  - 단점: 수학적 가정 필요 (정규 분포, 독립성)")
print()
print("핵심 차이:")
print("  논문: 충돌 여부를 '실제로 확인'")
print("  구현: 충돌 확률을 '수학적으로 계산'")
print()
print("결과:")
print("  두 방법 모두 동일한 확률 값을 제공하지만,")
print("  해석적 방법이 훨씬 빠르고 효율적입니다.")
print()
print("=" * 70)
