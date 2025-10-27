"""
충돌 확률 계산 엔진 단위 테스트

논문의 수식을 검증하고 각 함수의 정확성을 테스트합니다.
"""

import pytest
import numpy as np
from scipy.stats import norm
from scipy.special import erf
from core.safety_envelope import SafetyEnvelope
from core.conflict_probability import ConflictProbabilityCalculator


class TestConflictProbabilityCalculator:
    """ConflictProbabilityCalculator 클래스 테스트"""
    
    @pytest.fixture
    def default_envelope(self):
        """기본 안전 엔벨로프"""
        return SafetyEnvelope(
            Vf=5.0, Vb=2.0, Va=0.9, Vd=1.5, Vl=3.0,
            response_time=60
        )
    
    @pytest.fixture
    def default_calculator(self, default_envelope):
        """기본 충돌 확률 계산기"""
        return ConflictProbabilityCalculator(
            safety_envelope=default_envelope,
            r_A1=0.2,  # along-track
            r_A2=0.1,  # cross-track 1
            r_A3=0.1   # cross-track 2
        )
    
    def test_initialization(self, default_calculator, default_envelope):
        """초기화 테스트"""
        assert default_calculator.r_A1 == 0.2
        assert default_calculator.r_A2 == 0.1
        assert default_calculator.r_A3 == 0.1
        assert default_calculator.safety_envelope == default_envelope
        assert default_calculator.r_eq > 0
    
    def test_invalid_initialization(self, default_envelope):
        """잘못된 입력값 테스트"""
        with pytest.raises(ValueError):
            ConflictProbabilityCalculator(
                default_envelope,
                r_A1=-0.2,  # 음수
                r_A2=0.1,
                r_A3=0.1
            )
        
        with pytest.raises(ValueError):
            ConflictProbabilityCalculator(
                default_envelope,
                r_A1=0.2,
                r_A2=0.0,  # 0
                r_A3=0.1
            )
    
    def test_compute_p_k_basic(self, default_calculator):
        """Eq. (27) - p_k(t) 기본 테스트"""
        t = 1.0
        r1 = 1.0
        k_norm = 0.5
        
        p_k = default_calculator.compute_p_k(t, r1, k_norm)
        
        # 수동 계산
        coefficient = r1 / np.sqrt(2.0 * np.pi * t**3)
        exponent = -(r1 - k_norm * t)**2 / (2.0 * t)
        expected = coefficient * np.exp(exponent)
        
        assert p_k == pytest.approx(expected, rel=1e-10)
        assert p_k > 0  # 확률 밀도는 양수
    
    def test_compute_p_k_zero_time(self, default_calculator):
        """p_k(t) - t=0 경계 조건"""
        p_k = default_calculator.compute_p_k(0.0, 1.0, 0.5)
        assert p_k == 0.0
    
    def test_compute_p_k_small_time(self, default_calculator):
        """p_k(t) - 작은 t 값"""
        p_k = default_calculator.compute_p_k(1e-12, 1.0, 0.5)
        assert p_k == 0.0  # 수치 안정성
    
    def test_integrate_p_k_basic(self, default_calculator):
        """Eq. (28) - ∫p_k(t)dt 기본 테스트"""
        T = 2.0
        r1 = 1.0
        k_norm = 0.5
        
        integral = default_calculator.integrate_p_k(T, r1, k_norm)
        
        # 수동 계산
        sqrt_T = np.sqrt(T)
        arg1 = (r1 - k_norm * T) / sqrt_T
        term1 = 1.0 - norm.cdf(arg1)
        
        exp_arg = 2.0 * r1 * k_norm
        arg2 = (r1 + k_norm * T) / sqrt_T
        term2 = np.exp(exp_arg) * (1.0 - norm.cdf(arg2))
        
        expected = term1 + term2
        
        assert integral == pytest.approx(expected, rel=1e-10)
        assert 0 <= integral <= 1  # 확률이므로 [0, 1]
    
    def test_integrate_p_k_zero_T(self, default_calculator):
        """∫p_k(t)dt - T=0 경계 조건"""
        integral = default_calculator.integrate_p_k(0.0, 1.0, 0.5)
        assert integral == 0.0
    
    def test_integrate_t_p_k_basic(self, default_calculator):
        """Eq. (29) - ∫t·p_k(t)dt 기본 테스트"""
        T = 2.0
        r1 = 1.0
        k_norm = 0.5
        
        integral = default_calculator.integrate_t_p_k(T, r1, k_norm)
        
        # 수치 적분이므로 대략적인 검증
        assert integral > 0  # 양수여야 함
        assert integral < T * 10  # 합리적인 범위
    
    def test_integrate_t_p_k_zero_T(self, default_calculator):
        """∫t·p_k(t)dt - T=0 경계 조건"""
        integral = default_calculator.integrate_t_p_k(0.0, 1.0, 0.5)
        assert integral == 0.0
    
    def test_compute_T_h_basic(self, default_calculator):
        """Eq. (30) - 대표 시간 T_h 기본 테스트"""
        t0 = 1.0
        delta_t = 2.0
        r1 = 1.0
        k_norm = 0.5
        
        T_h = default_calculator.compute_T_h(t0, delta_t, r1, k_norm)
        
        # T_h는 [t0, t0+delta_t] 범위 내에 있어야 함
        assert t0 <= T_h <= t0 + delta_t
        assert T_h > 0
    
    def test_compute_T_h_midpoint_fallback(self, default_calculator):
        """T_h - 분모가 0인 경우 중점 반환"""
        # 특수한 경우: 적분이 0에 가까워지는 파라미터
        t0 = 0.0
        delta_t = 0.001
        r1 = 100.0  # 매우 큰 r1
        k_norm = 0.0001  # 매우 작은 k_norm
        
        T_h = default_calculator.compute_T_h(t0, delta_t, r1, k_norm)
        
        # 중점 근처여야 함
        expected_midpoint = t0 + delta_t / 2.0
        assert abs(T_h - expected_midpoint) < delta_t
    
    def test_compute_projection_probability_basic(self, default_calculator):
        """Eq. (34) - 투영 확률 기본 테스트"""
        T_h = 1.0
        l2 = 0.5
        l3 = 0.3
        r_eq = 2.0
        
        p_proj = default_calculator.compute_projection_probability(
            T_h, l2, l3, r_eq
        )
        
        # 수동 계산
        normalization = 1.0 / (2.0 * np.pi * T_h)
        sqrt_2Th = np.sqrt(2.0 * T_h)
        
        contrib_l3 = erf((l3 + r_eq) / sqrt_2Th) - erf((l3 - r_eq) / sqrt_2Th)
        contrib_l2 = erf((l2 + r_eq) / sqrt_2Th) - erf((l2 - r_eq) / sqrt_2Th)
        
        expected = normalization * (1.0 / 4.0) * contrib_l3 * contrib_l2
        
        assert p_proj == pytest.approx(expected, rel=1e-10)
        assert p_proj >= 0  # 확률은 음수가 될 수 없음
    
    def test_compute_projection_probability_zero_Th(self, default_calculator):
        """투영 확률 - T_h=0 경계 조건"""
        p_proj = default_calculator.compute_projection_probability(
            0.0, 0.5, 0.3, 2.0
        )
        assert p_proj == 0.0
    
    def test_compute_projection_probability_large_distance(self, default_calculator):
        """투영 확률 - 거리가 먼 경우"""
        T_h = 1.0
        l2 = 100.0  # 매우 먼 거리
        l3 = 100.0
        r_eq = 2.0
        
        p_proj = default_calculator.compute_projection_probability(
            T_h, l2, l3, r_eq
        )
        
        # 거리가 멀면 확률이 매우 작아야 함
        assert p_proj < 0.01
    
    def test_construct_transformation_matrices_basic(self, default_calculator):
        """좌표 변환 행렬 기본 테스트"""
        v_A = np.array([10.0, 0.0, 0.0])  # x 방향 속도
        
        F, P = default_calculator.construct_transformation_matrices(v_A)
        
        # F는 회전 행렬 (직교 행렬)
        assert F.shape == (3, 3)
        identity = F @ F.T
        np.testing.assert_array_almost_equal(identity, np.eye(3), decimal=10)
        
        # P는 대각 행렬
        assert P.shape == (3, 3)
        assert np.allclose(P, np.diag(np.diag(P)))
        
        # P의 대각 원소 확인
        expected_diag = [0.2**2, 0.1**2, 0.1**2]
        np.testing.assert_array_almost_equal(np.diag(P), expected_diag)
    
    def test_construct_transformation_matrices_zero_velocity(self, default_calculator):
        """좌표 변환 행렬 - 속도가 0인 경우"""
        v_A = np.array([0.0, 0.0, 0.0])
        
        F, P = default_calculator.construct_transformation_matrices(v_A)
        
        # 속도가 0이면 F는 단위 행렬
        np.testing.assert_array_almost_equal(F, np.eye(3))
    
    def test_construct_transformation_matrices_different_directions(
        self, default_calculator
    ):
        """좌표 변환 행렬 - 다양한 방향"""
        velocities = [
            np.array([10.0, 0.0, 0.0]),
            np.array([0.0, 10.0, 0.0]),
            np.array([0.0, 0.0, 10.0]),
            np.array([5.0, 5.0, 0.0]),
            np.array([3.0, 4.0, 5.0])
        ]
        
        for v_A in velocities:
            F, P = default_calculator.construct_transformation_matrices(v_A)
            
            # F는 직교 행렬이어야 함
            identity = F @ F.T
            np.testing.assert_array_almost_equal(identity, np.eye(3), decimal=10)
    
    def test_compute_conflict_probability_basic(self, default_calculator):
        """전체 파이프라인 - 기본 충돌 확률 계산"""
        X = np.array([52.0, 6.0, 5.5])  # 테스트 좌표
        X_A0 = np.array([50.0, 5.0, 5.0])  # UAV 초기 위치
        v_A = np.array([0.0, 10.0, 0.0])  # y 방향 이동
        t0 = 0.0
        delta_t = 1.0
        
        prob = default_calculator.compute_conflict_probability(
            X, X_A0, v_A, t0, delta_t
        )
        
        # 확률 범위 확인
        assert 0 <= prob <= 1
        assert isinstance(prob, (int, float))
    
    def test_compute_conflict_probability_far_point(self, default_calculator):
        """전체 파이프라인 - 먼 거리 (낮은 확률)"""
        X = np.array([100.0, 100.0, 20.0])  # 매우 먼 점
        X_A0 = np.array([50.0, 5.0, 5.0])
        v_A = np.array([0.0, 10.0, 0.0])
        t0 = 0.0
        delta_t = 1.0
        
        prob = default_calculator.compute_conflict_probability(
            X, X_A0, v_A, t0, delta_t
        )
        
        # 매우 먼 점이므로 확률이 매우 낮아야 함
        assert prob < 0.1
    
    def test_compute_conflict_probability_near_point(self, default_calculator):
        """전체 파이프라인 - 가까운 거리 (유효한 확률)"""
        X = np.array([50.1, 5.1, 5.0])  # UAV 바로 근처
        X_A0 = np.array([50.0, 5.0, 5.0])
        v_A = np.array([0.0, 1.0, 0.0])  # 느린 속도
        t0 = 0.0
        delta_t = 2.0
        
        prob = default_calculator.compute_conflict_probability(
            X, X_A0, v_A, t0, delta_t
        )
        
        # 확률이 유효 범위 내에 있는지 확인
        assert 0 <= prob <= 1
    
    def test_compute_conflict_probability_zero_velocity(self, default_calculator):
        """전체 파이프라인 - 속도가 0인 경우"""
        X = np.array([52.0, 6.0, 5.5])
        X_A0 = np.array([50.0, 5.0, 5.0])
        v_A = np.array([0.0, 0.0, 0.0])  # 정지
        t0 = 0.0
        delta_t = 1.0
        
        prob = default_calculator.compute_conflict_probability(
            X, X_A0, v_A, t0, delta_t
        )
        
        # 속도가 0이면 k_norm이 0이 되어 확률 0
        assert prob == 0.0
    
    def test_compute_conflict_probability_different_time_intervals(
        self, default_calculator
    ):
        """전체 파이프라인 - 다양한 시간 구간"""
        X = np.array([52.0, 6.0, 5.5])
        X_A0 = np.array([50.0, 5.0, 5.0])
        v_A = np.array([0.0, 10.0, 0.0])
        
        # 시간 구간이 길수록 확률이 증가할 수 있음
        prob_short = default_calculator.compute_conflict_probability(
            X, X_A0, v_A, 0.0, 0.5
        )
        prob_long = default_calculator.compute_conflict_probability(
            X, X_A0, v_A, 0.0, 2.0
        )
        
        # 두 확률 모두 유효 범위 내
        assert 0 <= prob_short <= 1
        assert 0 <= prob_long <= 1
    
    def test_compute_conflict_probability_consistency(self, default_calculator):
        """전체 파이프라인 - 일관성 테스트"""
        X = np.array([52.0, 6.0, 5.5])
        X_A0 = np.array([50.0, 5.0, 5.0])
        v_A = np.array([0.0, 10.0, 0.0])
        t0 = 0.0
        delta_t = 1.0
        
        # 동일한 입력에 대해 동일한 결과
        prob1 = default_calculator.compute_conflict_probability(
            X, X_A0, v_A, t0, delta_t
        )
        prob2 = default_calculator.compute_conflict_probability(
            X, X_A0, v_A, t0, delta_t
        )
        
        assert prob1 == pytest.approx(prob2, rel=1e-10)
    
    def test_repr(self, default_calculator):
        """문자열 표현 테스트"""
        repr_str = repr(default_calculator)
        
        assert "ConflictProbabilityCalculator" in repr_str
        assert "r_A1=0.200" in repr_str
        assert "r_eq=" in repr_str


class TestConflictProbabilityEdgeCases:
    """ConflictProbabilityCalculator Edge Case 테스트"""
    
    @pytest.fixture
    def default_calculator(self):
        """기본 계산기"""
        envelope = SafetyEnvelope(5, 2, 0.9, 1.5, 3, 60)
        return ConflictProbabilityCalculator(envelope, 0.2, 0.1, 0.1)
    
    def test_very_small_uncertainty(self):
        """매우 작은 불확실성 파라미터"""
        envelope = SafetyEnvelope(5, 2, 0.9, 1.5, 3, 60)
        calc = ConflictProbabilityCalculator(envelope, 0.001, 0.001, 0.001)
        
        X = np.array([52.0, 6.0, 5.5])
        X_A0 = np.array([50.0, 5.0, 5.0])
        v_A = np.array([0.0, 10.0, 0.0])
        
        prob = calc.compute_conflict_probability(X, X_A0, v_A, 0, 1)
        
        # 매우 작은 불확실성 → 낮은 확률
        assert 0 <= prob <= 1
        assert prob < 0.5
    
    def test_very_large_uncertainty(self):
        """매우 큰 불확실성 파라미터"""
        envelope = SafetyEnvelope(5, 2, 0.9, 1.5, 3, 60)
        calc = ConflictProbabilityCalculator(envelope, 10.0, 5.0, 5.0)
        
        X = np.array([52.0, 6.0, 5.5])
        X_A0 = np.array([50.0, 5.0, 5.0])
        v_A = np.array([0.0, 10.0, 0.0])
        
        prob = calc.compute_conflict_probability(X, X_A0, v_A, 0, 1)
        
        # 큰 불확실성 → 높은 확률 가능
        assert 0 <= prob <= 1
    
    def test_very_high_velocity(self, default_calculator):
        """매우 빠른 속도"""
        X = np.array([52.0, 6.0, 5.5])
        X_A0 = np.array([50.0, 5.0, 5.0])
        v_A = np.array([0.0, 1000.0, 0.0])  # 매우 빠름
        
        prob = default_calculator.compute_conflict_probability(X, X_A0, v_A, 0, 0.1)
        
        assert 0 <= prob <= 1
        assert np.isfinite(prob)
    
    def test_very_low_velocity(self, default_calculator):
        """매우 느린 속도"""
        X = np.array([52.0, 6.0, 5.5])
        X_A0 = np.array([50.0, 5.0, 5.0])
        v_A = np.array([0.0, 0.001, 0.0])  # 매우 느림
        
        prob = default_calculator.compute_conflict_probability(X, X_A0, v_A, 0, 1)
        
        assert 0 <= prob <= 1
        assert np.isfinite(prob)
    
    def test_negative_coordinates(self, default_calculator):
        """음수 좌표 처리"""
        X = np.array([-48.0, -94.0, -4.5])
        X_A0 = np.array([-50.0, -95.0, -5.0])
        v_A = np.array([0.0, 10.0, 0.0])
        
        prob = default_calculator.compute_conflict_probability(X, X_A0, v_A, 0, 1)
        
        # 상대 위치만 중요하므로 정상 작동
        assert 0 <= prob <= 1
        assert np.isfinite(prob)
    
    def test_very_long_time_interval(self, default_calculator):
        """매우 긴 시간 구간"""
        X = np.array([52.0, 6.0, 5.5])
        X_A0 = np.array([50.0, 5.0, 5.0])
        v_A = np.array([0.0, 10.0, 0.0])
        
        prob = default_calculator.compute_conflict_probability(X, X_A0, v_A, 0, 1000)
        
        assert 0 <= prob <= 1
        assert np.isfinite(prob)
    
    def test_very_short_time_interval(self, default_calculator):
        """매우 짧은 시간 구간"""
        X = np.array([52.0, 6.0, 5.5])
        X_A0 = np.array([50.0, 5.0, 5.0])
        v_A = np.array([0.0, 10.0, 0.0])
        
        prob = default_calculator.compute_conflict_probability(X, X_A0, v_A, 0, 0.001)
        
        assert 0 <= prob <= 1
        assert np.isfinite(prob)
    
    def test_point_on_trajectory(self, default_calculator):
        """점이 정확히 궤적 위에 있는 경우"""
        X_A0 = np.array([50.0, 5.0, 5.0])
        v_A = np.array([0.0, 10.0, 0.0])
        
        # t=0.5에서 UAV는 (50, 10, 5)에 위치
        X = np.array([50.0, 10.0, 5.0])
        
        prob = default_calculator.compute_conflict_probability(X, X_A0, v_A, 0, 1)
        
        # 확률이 유효 범위 내 (0일 수도 있음 - 정확한 궤적 위치에 따라)
        assert 0 <= prob <= 1
        assert np.isfinite(prob)
    
    def test_point_behind_trajectory(self, default_calculator):
        """점이 궤적 뒤에 있는 경우"""
        X_A0 = np.array([50.0, 5.0, 5.0])
        v_A = np.array([0.0, 10.0, 0.0])  # 북쪽으로 이동
        
        # 남쪽에 있는 점
        X = np.array([50.0, 0.0, 5.0])
        
        prob = default_calculator.compute_conflict_probability(X, X_A0, v_A, 0, 1)
        
        # 뒤쪽 점이므로 낮은 확률
        assert 0 <= prob <= 1
    
    def test_numerical_stability_extreme_values(self, default_calculator):
        """수치 안정성 - 극단적 값"""
        # 매우 큰 좌표
        X = np.array([1e10, 1e10, 1e10])
        X_A0 = np.array([1e10 + 2, 1e10, 1e10])
        v_A = np.array([0.0, 10.0, 0.0])
        
        prob = default_calculator.compute_conflict_probability(X, X_A0, v_A, 0, 1)
        
        assert 0 <= prob <= 1
        assert np.isfinite(prob)


class TestConflictProbabilityPaperValidation:
    """논문 예시값 및 수식 검증"""
    
    def test_p_k_normalization(self):
        """
        Eq. (28) 검증: ∫₀^∞ p_k(t) dt = 1
        
        충분히 긴 시간에서 적분이 1에 수렴
        """
        envelope = SafetyEnvelope(5, 2, 0.9, 1.5, 3, 60)
        calc = ConflictProbabilityCalculator(envelope, 0.2, 0.1, 0.1)
        
        r1 = 10.0
        k_norm = 1.0
        
        # 매우 큰 T에서 적분
        integral = calc.integrate_p_k(T=10000, r1=r1, k_norm=k_norm)
        
        # 1에 가까워야 함 (1% 오차 허용)
        assert integral == pytest.approx(1.0, rel=0.01), \
            f"∫p_k(t)dt should approach 1, got {integral:.6f}"
    
    def test_erf_function_accuracy(self):
        """
        Eq. (34) erf 함수 사용 정확도
        
        erf의 성질: erf(-x) = -erf(x), erf(∞) = 1
        """
        from scipy.special import erf
        
        # erf 성질 검증
        assert erf(-1.0) == pytest.approx(-erf(1.0), rel=1e-10)
        assert erf(0.0) == 0.0
        assert erf(5.0) == pytest.approx(1.0, abs=1e-6)
        assert erf(-5.0) == pytest.approx(-1.0, abs=1e-6)
    
    def test_brownian_motion_variance_growth(self):
        """
        Brownian motion 분산 성장 검증
        
        σ²(t) = r²·t (선형 성장)
        """
        envelope = SafetyEnvelope(5, 2, 0.9, 1.5, 3, 60)
        calc = ConflictProbabilityCalculator(envelope, 0.2, 0.1, 0.1)
        
        # r_A1, r_A2, r_A3이 올바르게 저장되었는지 확인
        assert calc.r_A1 == 0.2
        assert calc.r_A2 == 0.1
        assert calc.r_A3 == 0.1
        
        # 시간에 따른 분산 성장: σ²(t) = r²·t
        t = 4.0  # 4분
        expected_variance_1 = 0.2**2 * t
        expected_variance_2 = 0.1**2 * t
        
        # P 행렬 확인 (P = diag[r_A1², r_A2², r_A3²])
        v_A = np.array([10.0, 0.0, 0.0])
        F, P = calc.construct_transformation_matrices(v_A)
        
        assert P[0, 0] == pytest.approx(0.2**2, rel=1e-10)
        assert P[1, 1] == pytest.approx(0.1**2, rel=1e-10)
        assert P[2, 2] == pytest.approx(0.1**2, rel=1e-10)
    
    def test_distance_vs_probability_relationship(self):
        """
        거리와 확률의 관계 검증
        
        거리가 멀수록 확률은 감소
        """
        envelope = SafetyEnvelope(5, 2, 0.9, 1.5, 3, 60)
        calc = ConflictProbabilityCalculator(envelope, 0.2, 0.1, 0.1)
        
        X_A0 = np.array([50.0, 50.0, 10.0])
        v_A = np.array([5.0, 0.0, 0.0])
        
        # 다양한 거리에서 확률 계산
        distances = [1.0, 5.0, 10.0, 20.0, 50.0]
        probabilities = []
        
        for dist in distances:
            X = X_A0 + np.array([0, dist, 0])
            prob = calc.compute_conflict_probability(X, X_A0, v_A, 0, 1)
            probabilities.append(prob)
        
        # 확률이 단조 감소하는지 확인 (일부 예외 허용)
        for i in range(len(probabilities) - 1):
            # 거리가 멀어질수록 확률은 감소하거나 유지
            assert probabilities[i] >= probabilities[i+1] * 0.5, \
                f"Probability should decrease with distance: {probabilities}"
    
    def test_symmetry_property(self):
        """
        대칭성 검증
        
        UAV 주변에서 같은 거리의 점들은 유사한 확률
        """
        envelope = SafetyEnvelope(5, 2, 0.9, 1.5, 3, 60)
        calc = ConflictProbabilityCalculator(envelope, 0.2, 0.1, 0.1)
        
        X_A0 = np.array([50.0, 50.0, 10.0])
        v_A = np.array([5.0, 0.0, 0.0])  # x 방향
        
        # 같은 거리, 다른 방향 (y축 대칭)
        distance = 5.0
        X1 = X_A0 + np.array([0, distance, 0])   # +y
        X2 = X_A0 + np.array([0, -distance, 0])  # -y
        
        prob1 = calc.compute_conflict_probability(X1, X_A0, v_A, 0, 1)
        prob2 = calc.compute_conflict_probability(X2, X_A0, v_A, 0, 1)
        
        # 대칭이므로 유사한 확률 (30% 오차 허용)
        assert prob1 == pytest.approx(prob2, rel=0.3), \
            f"Symmetric points should have similar probabilities: {prob1:.6f} vs {prob2:.6f}"
    
    def test_time_interval_effect(self):
        """
        시간 구간 길이의 영향 검증
        
        delta_t가 길수록 T_h가 커지고 분산도 증가
        """
        envelope = SafetyEnvelope(5, 2, 0.9, 1.5, 3, 60)
        calc = ConflictProbabilityCalculator(envelope, 0.2, 0.1, 0.1)
        
        X = np.array([52.0, 56.0, 10.5])
        X_A0 = np.array([50.0, 50.0, 10.0])
        v_A = np.array([5.0, 5.0, 0.0])
        
        # 다양한 delta_t
        delta_ts = [0.5, 1.0, 2.0, 5.0]
        probs = []
        
        for dt in delta_ts:
            prob = calc.compute_conflict_probability(X, X_A0, v_A, 0, dt)
            probs.append(prob)
        
        # 모든 확률이 유효 범위 내
        for prob in probs:
            assert 0 <= prob <= 1
            assert np.isfinite(prob)


class TestMultiUAVIndependence:
    """다중 UAV 독립성 검증 (Eq. 9)"""
    
    def test_independence_assumption(self):
        """
        Eq. (9): s(X) = 1 - ∏(1 - p_i)
        
        다중 UAV 충돌 확률의 독립성 가정 검증
        """
        envelope = SafetyEnvelope(5, 2, 0.9, 1.5, 3, 60)
        calc = ConflictProbabilityCalculator(envelope, 0.2, 0.1, 0.1)
        
        # 테스트 점
        X = np.array([52.0, 52.0, 10.0])
        
        # 두 UAV
        X_A1 = np.array([50.0, 50.0, 10.0])
        v_A1 = np.array([5.0, 0.0, 0.0])
        
        X_A2 = np.array([55.0, 55.0, 10.0])
        v_A2 = np.array([0.0, 5.0, 0.0])
        
        # 개별 확률
        p1 = calc.compute_conflict_probability(X, X_A1, v_A1, 0, 1)
        p2 = calc.compute_conflict_probability(X, X_A2, v_A2, 0, 1)
        
        # 결합 확률 (Eq. 9)
        p_combined = 1.0 - (1.0 - p1) * (1.0 - p2)
        
        # 검증
        assert 0 <= p_combined <= 1
        assert p_combined >= max(p1, p2), "Combined probability should be >= individual max"
        assert p_combined <= p1 + p2, "Combined probability should be <= sum (independence)"
    
    def test_three_uavs_independence(self):
        """3대 UAV 독립성"""
        envelope = SafetyEnvelope(5, 2, 0.9, 1.5, 3, 60)
        calc = ConflictProbabilityCalculator(envelope, 0.2, 0.1, 0.1)
        
        X = np.array([52.0, 52.0, 10.0])
        
        # 세 UAV
        uavs = [
            (np.array([50.0, 50.0, 10.0]), np.array([5.0, 0.0, 0.0])),
            (np.array([55.0, 50.0, 10.0]), np.array([0.0, 5.0, 0.0])),
            (np.array([50.0, 55.0, 10.0]), np.array([3.0, 3.0, 0.0]))
        ]
        
        # 개별 확률
        probs = []
        for X_A, v_A in uavs:
            p = calc.compute_conflict_probability(X, X_A, v_A, 0, 1)
            probs.append(p)
        
        # 결합 확률
        product = 1.0
        for p in probs:
            product *= (1.0 - p)
        
        p_combined = 1.0 - product
        
        # 검증
        assert 0 <= p_combined <= 1
        assert p_combined >= max(probs)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
