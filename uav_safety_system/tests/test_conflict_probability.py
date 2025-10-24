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


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
