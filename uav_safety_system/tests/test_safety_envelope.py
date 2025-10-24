"""
안전 엔벨로프 클래스 단위 테스트

논문의 예제 값과 비교하여 구현을 검증합니다.
"""

import pytest
import numpy as np
from core.safety_envelope import SafetyEnvelope


class TestSafetyEnvelope:
    """SafetyEnvelope 클래스 테스트"""
    
    @pytest.fixture
    def default_envelope(self):
        """기본 테스트용 안전 엔벨로프 (논문 Table 1 기준)"""
        return SafetyEnvelope(
            Vf=5.0,  # km/min
            Vb=2.0,  # km/min
            Va=0.9,  # km/min
            Vd=1.5,  # km/min
            Vl=3.0,  # km/min
            response_time=60  # seconds
        )
    
    def test_initialization(self, default_envelope):
        """초기화 테스트"""
        assert default_envelope.Vf == 5.0
        assert default_envelope.Vb == 2.0
        assert default_envelope.Va == 0.9
        assert default_envelope.Vd == 1.5
        assert default_envelope.Vl == 3.0
        assert default_envelope.response_time == 60
        assert default_envelope.s == 1.0  # 60초 = 1분
    
    def test_invalid_initialization(self):
        """잘못된 입력값 테스트"""
        with pytest.raises(ValueError):
            SafetyEnvelope(
                Vf=-5.0,  # 음수 속도
                Vb=2.0,
                Va=0.9,
                Vd=1.5,
                Vl=3.0,
                response_time=60
            )
        
        with pytest.raises(ValueError):
            SafetyEnvelope(
                Vf=5.0,
                Vb=2.0,
                Va=0.9,
                Vd=1.5,
                Vl=3.0,
                response_time=0  # 0초
            )
    
    def test_compute_axes(self, default_envelope):
        """Eq. (1) - 축 계산 테스트"""
        axes = default_envelope.compute_axes()
        
        # s = 60/60 = 1.0 min
        assert axes['a'] == pytest.approx(5.0 * 1.0, rel=1e-6)  # Vf * s
        assert axes['b'] == pytest.approx(2.0 * 1.0, rel=1e-6)  # Vb * s
        assert axes['c'] == pytest.approx(0.9 * 1.0, rel=1e-6)  # Va * s
        assert axes['d'] == pytest.approx(1.5 * 1.0, rel=1e-6)  # Vd * s
        assert axes['e'] == pytest.approx(3.0 * 1.0, rel=1e-6)  # Vl * s
        assert axes['f'] == pytest.approx(3.0 * 1.0, rel=1e-6)  # Vl * s
        
        # 저장된 값 확인
        assert default_envelope.a == 5.0
        assert default_envelope.b == 2.0
        assert default_envelope.c == 0.9
        assert default_envelope.d == 1.5
        assert default_envelope.e == 3.0
    
    def test_compute_equivalent_radius(self, default_envelope):
        """Eq. (24) - 등가 반경 계산 테스트"""
        r_eq = default_envelope.compute_equivalent_radius()
        
        # 수동 계산
        # r_eq = [Vl × (Vf×Va + Vf×Vd + Vb×Va + Vb×Vd) / 4]^(1/3) × s
        # r_eq = [3.0 × (5.0×0.9 + 5.0×1.5 + 2.0×0.9 + 2.0×1.5) / 4]^(1/3) × 1.0
        # r_eq = [3.0 × (4.5 + 7.5 + 1.8 + 3.0) / 4]^(1/3)
        # r_eq = [3.0 × 16.8 / 4]^(1/3)
        # r_eq = [12.6]^(1/3)
        expected = np.power(3.0 * (5.0*0.9 + 5.0*1.5 + 2.0*0.9 + 2.0*1.5) / 4.0, 1.0/3.0) * 1.0
        
        assert r_eq == pytest.approx(expected, rel=1e-6)
        assert r_eq == pytest.approx(2.327, rel=1e-3)  # 약 2.327 km
    
    def test_get_matrix_M_quadrant1(self, default_envelope):
        """Eq. (3) - M₁ 행렬 테스트 (전방-상승)"""
        X = np.array([55.0, 5.0, 6.0])  # 전방-상승
        X_A = np.array([50.0, 5.0, 5.0])
        
        M = default_envelope.get_matrix_M(X, X_A)
        
        # M₁ = diag[1/a², 1/e², 1/c²]
        expected = np.diag([1.0/(5.0**2), 1.0/(3.0**2), 1.0/(0.9**2)])
        
        np.testing.assert_array_almost_equal(M, expected)
    
    def test_get_matrix_M_quadrant2(self, default_envelope):
        """Eq. (3) - M₂ 행렬 테스트 (전방-하강)"""
        X = np.array([55.0, 5.0, 4.0])  # 전방-하강
        X_A = np.array([50.0, 5.0, 5.0])
        
        M = default_envelope.get_matrix_M(X, X_A)
        
        # M₂ = diag[1/a², 1/e², 1/d²]
        expected = np.diag([1.0/(5.0**2), 1.0/(3.0**2), 1.0/(1.5**2)])
        
        np.testing.assert_array_almost_equal(M, expected)
    
    def test_get_matrix_M_quadrant3(self, default_envelope):
        """Eq. (4) - M₃ 행렬 테스트 (후방-상승)"""
        X = np.array([45.0, 5.0, 6.0])  # 후방-상승
        X_A = np.array([50.0, 5.0, 5.0])
        
        M = default_envelope.get_matrix_M(X, X_A)
        
        # M₃ = diag[1/b², 1/e², 1/c²]
        expected = np.diag([1.0/(2.0**2), 1.0/(3.0**2), 1.0/(0.9**2)])
        
        np.testing.assert_array_almost_equal(M, expected)
    
    def test_get_matrix_M_quadrant4(self, default_envelope):
        """Eq. (4) - M₄ 행렬 테스트 (후방-하강)"""
        X = np.array([45.0, 5.0, 4.0])  # 후방-하강
        X_A = np.array([50.0, 5.0, 5.0])
        
        M = default_envelope.get_matrix_M(X, X_A)
        
        # M₄ = diag[1/b², 1/e², 1/d²]
        expected = np.diag([1.0/(2.0**2), 1.0/(3.0**2), 1.0/(1.5**2)])
        
        np.testing.assert_array_almost_equal(M, expected)
    
    def test_is_inside_center(self, default_envelope):
        """Eq. (5) - 중심점 테스트 (반드시 내부)"""
        X_A = np.array([50.0, 5.0, 5.0])
        
        assert default_envelope.is_inside(X_A, X_A)
    
    def test_is_inside_forward(self, default_envelope):
        """Eq. (5) - 전방 방향 테스트"""
        X_A = np.array([50.0, 5.0, 5.0])
        
        # 전방 최대 거리 내부 (a = 5.0 km)
        X_inside = np.array([54.0, 5.0, 5.0])  # 4km 전방
        assert default_envelope.is_inside(X_inside, X_A)
        
        # 전방 최대 거리 외부
        X_outside = np.array([56.0, 5.0, 5.0])  # 6km 전방 (> a)
        assert not default_envelope.is_inside(X_outside, X_A)
    
    def test_is_inside_backward(self, default_envelope):
        """Eq. (5) - 후방 방향 테스트"""
        X_A = np.array([50.0, 5.0, 5.0])
        
        # 후방 최대 거리 내부 (b = 2.0 km)
        X_inside = np.array([48.5, 5.0, 5.0])  # 1.5km 후방
        assert default_envelope.is_inside(X_inside, X_A)
        
        # 후방 최대 거리 외부
        X_outside = np.array([47.0, 5.0, 5.0])  # 3km 후방 (> b)
        assert not default_envelope.is_inside(X_outside, X_A)
    
    def test_is_inside_upward(self, default_envelope):
        """Eq. (5) - 상승 방향 테스트"""
        X_A = np.array([50.0, 5.0, 5.0])
        
        # 상승 최대 거리 내부 (c = 0.9 km)
        X_inside = np.array([50.0, 5.0, 5.5])  # 0.5km 상승
        assert default_envelope.is_inside(X_inside, X_A)
        
        # 상승 최대 거리 외부
        X_outside = np.array([50.0, 5.0, 6.5])  # 1.5km 상승 (> c)
        assert not default_envelope.is_inside(X_outside, X_A)
    
    def test_is_inside_downward(self, default_envelope):
        """Eq. (5) - 하강 방향 테스트"""
        X_A = np.array([50.0, 5.0, 5.0])
        
        # 하강 최대 거리 내부 (d = 1.5 km)
        X_inside = np.array([50.0, 5.0, 4.0])  # 1.0km 하강
        assert default_envelope.is_inside(X_inside, X_A)
        
        # 하강 최대 거리 외부
        X_outside = np.array([50.0, 5.0, 3.0])  # 2.0km 하강 (> d)
        assert not default_envelope.is_inside(X_outside, X_A)
    
    def test_is_inside_lateral(self, default_envelope):
        """Eq. (5) - 횡방향 테스트"""
        X_A = np.array([50.0, 5.0, 5.0])
        
        # 횡방향 최대 거리 내부 (e = 3.0 km)
        X_inside = np.array([50.0, 7.0, 5.0])  # 2km 횡방향
        assert default_envelope.is_inside(X_inside, X_A)
        
        # 횡방향 최대 거리 외부
        X_outside = np.array([50.0, 9.0, 5.0])  # 4km 횡방향 (> e)
        assert not default_envelope.is_inside(X_outside, X_A)
    
    def test_is_inside_combined(self, default_envelope):
        """Eq. (5) - 복합 방향 테스트"""
        X_A = np.array([50.0, 5.0, 5.0])
        
        # 타원체 방정식: (x/a)² + (y/e)² + (z/c)² ≤ 1 (전방-상승 사분면)
        # (2/5)² + (1/3)² + (0.5/0.9)² = 0.16 + 0.111 + 0.309 = 0.58 < 1
        X_inside = np.array([52.0, 6.0, 5.5])
        assert default_envelope.is_inside(X_inside, X_A)
        
        # 외부 점
        X_outside = np.array([54.0, 7.0, 5.8])
        # (4/5)² + (2/3)² + (0.8/0.9)² = 0.64 + 0.444 + 0.79 = 1.874 > 1
        assert not default_envelope.is_inside(X_outside, X_A)
    
    def test_get_volume(self, default_envelope):
        """Eq. (22) - 부피 계산 테스트"""
        volume = default_envelope.get_volume()
        
        # 수동 계산
        # V = (1/4) × [(4πade)/3 + (4πace)/3 + (4πbce)/3 + (4πbde)/3]
        a, b, c, d, e = 5.0, 2.0, 0.9, 1.5, 3.0
        V1 = (4.0 * np.pi * a * d * e) / 3.0
        V2 = (4.0 * np.pi * a * c * e) / 3.0
        V3 = (4.0 * np.pi * b * c * e) / 3.0
        V4 = (4.0 * np.pi * b * d * e) / 3.0
        expected = (V1 + V2 + V3 + V4) / 4.0
        
        assert volume == pytest.approx(expected, rel=1e-6)
        assert volume > 0  # 부피는 항상 양수
    
    def test_get_distance_to_surface(self, default_envelope):
        """표면까지 거리 계산 테스트"""
        X_A = np.array([50.0, 5.0, 5.0])
        
        # 중심점: 거리 0
        distance_center = default_envelope.get_distance_to_surface(X_A, X_A)
        assert distance_center == pytest.approx(0.0, abs=1e-10)
        
        # 내부 점: < 1.0
        X_inside = np.array([52.0, 5.0, 5.0])
        distance_inside = default_envelope.get_distance_to_surface(X_inside, X_A)
        assert 0 < distance_inside < 1.0
        
        # 외부 점: > 1.0
        X_outside = np.array([56.0, 5.0, 5.0])
        distance_outside = default_envelope.get_distance_to_surface(X_outside, X_A)
        assert distance_outside > 1.0
    
    def test_different_response_time(self):
        """다른 응답 시간 테스트"""
        # 30초 응답 시간
        envelope_30s = SafetyEnvelope(
            Vf=5.0, Vb=2.0, Va=0.9, Vd=1.5, Vl=3.0,
            response_time=30
        )
        
        # 60초 응답 시간
        envelope_60s = SafetyEnvelope(
            Vf=5.0, Vb=2.0, Va=0.9, Vd=1.5, Vl=3.0,
            response_time=60
        )
        
        # 30초는 60초의 절반 크기
        assert envelope_30s.a == pytest.approx(envelope_60s.a / 2.0, rel=1e-6)
        assert envelope_30s.b == pytest.approx(envelope_60s.b / 2.0, rel=1e-6)
        
        # 부피는 (1/2)³ = 1/8 배
        ratio = envelope_30s.get_volume() / envelope_60s.get_volume()
        assert ratio == pytest.approx(1.0/8.0, rel=1e-6)
    
    def test_repr(self, default_envelope):
        """문자열 표현 테스트"""
        repr_str = repr(default_envelope)
        
        assert "SafetyEnvelope" in repr_str
        assert "Vf=5.00" in repr_str
        assert "r_eq=" in repr_str
        assert "volume=" in repr_str


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
