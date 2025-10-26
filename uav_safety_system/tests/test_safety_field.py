"""
공역 안전 필드 클래스 단위 테스트

UAV 및 AirspaceSafetyField 클래스의 기능을 검증합니다.
"""

import pytest
import numpy as np
from core.safety_field import UAV, AirspaceSafetyField


class TestUAV:
    """UAV 데이터 클래스 테스트"""
    
    def test_uav_creation(self):
        """UAV 생성 테스트"""
        uav = UAV(
            id=1,
            position=np.array([50.0, 5.0, 5.0]),
            velocity=np.array([0.0, 10.0, 0.0]),
            Vf=5.0, Vb=2.0, Va=0.9, Vd=1.5, Vl=3.0,
            response_time=60
        )
        
        assert uav.id == 1
        np.testing.assert_array_equal(uav.position, [50.0, 5.0, 5.0])
        np.testing.assert_array_equal(uav.velocity, [0.0, 10.0, 0.0])
        assert uav.Vf == 5.0
        assert uav.response_time == 60
    
    def test_uav_invalid_position_shape(self):
        """잘못된 position shape 테스트"""
        with pytest.raises(ValueError, match="position"):
            UAV(
                id=1,
                position=np.array([50.0, 5.0]),  # shape (2,) - 잘못됨
                velocity=np.array([0.0, 10.0, 0.0]),
                Vf=5.0, Vb=2.0, Va=0.9, Vd=1.5, Vl=3.0,
                response_time=60
            )
    
    def test_uav_invalid_velocity_shape(self):
        """잘못된 velocity shape 테스트"""
        with pytest.raises(ValueError, match="velocity"):
            UAV(
                id=1,
                position=np.array([50.0, 5.0, 5.0]),
                velocity=np.array([0.0, 10.0]),  # shape (2,) - 잘못됨
                Vf=5.0, Vb=2.0, Va=0.9, Vd=1.5, Vl=3.0,
                response_time=60
            )
    
    def test_uav_invalid_speed(self):
        """잘못된 속도 파라미터 테스트"""
        with pytest.raises(ValueError, match="속도"):
            UAV(
                id=1,
                position=np.array([50.0, 5.0, 5.0]),
                velocity=np.array([0.0, 10.0, 0.0]),
                Vf=-5.0,  # 음수 - 잘못됨
                Vb=2.0, Va=0.9, Vd=1.5, Vl=3.0,
                response_time=60
            )
    
    def test_uav_invalid_response_time(self):
        """잘못된 응답 시간 테스트"""
        with pytest.raises(ValueError, match="response_time"):
            UAV(
                id=1,
                position=np.array([50.0, 5.0, 5.0]),
                velocity=np.array([0.0, 10.0, 0.0]),
                Vf=5.0, Vb=2.0, Va=0.9, Vd=1.5, Vl=3.0,
                response_time=0  # 0 - 잘못됨
            )


class TestAirspaceSafetyField:
    """AirspaceSafetyField 클래스 테스트"""
    
    @pytest.fixture
    def default_field(self):
        """기본 안전 필드"""
        bounds = {
            'x': (45.0, 55.0),
            'y': (0.0, 10.0),
            'z': (0.0, 10.0)
        }
        return AirspaceSafetyField(
            bounds=bounds,
            grid_resolution=1.0,
            r_A1=0.2,
            r_A2=0.1,
            r_A3=0.1
        )
    
    @pytest.fixture
    def single_uav(self):
        """단일 UAV"""
        return UAV(
            id=1,
            position=np.array([50.0, 0.0, 5.0]),
            velocity=np.array([0.0, 10.0, 0.0]),
            Vf=5.0, Vb=2.0, Va=0.9, Vd=1.5, Vl=3.0,
            response_time=60
        )
    
    def test_initialization(self, default_field):
        """초기화 테스트"""
        assert default_field.x_min == 45.0
        assert default_field.x_max == 55.0
        assert default_field.grid_resolution == 1.0
        assert default_field.r_A1 == 0.2
        assert default_field.r_A2 == 0.1
        assert default_field.r_A3 == 0.1
        assert default_field.field is None  # 아직 계산 안 됨
    
    def test_grid_shape(self, default_field):
        """그리드 크기 계산 테스트"""
        # x: [45, 55] with resolution 1.0 -> 10 cells
        # y: [0, 10] with resolution 1.0 -> 10 cells
        # z: [0, 10] with resolution 1.0 -> 10 cells
        assert default_field.nx == 10
        assert default_field.ny == 10
        assert default_field.nz == 10
        assert default_field.grid_shape == (10, 10, 10)
    
    def test_invalid_bounds(self):
        """잘못된 경계 테스트"""
        # min >= max
        with pytest.raises(ValueError):
            AirspaceSafetyField(
                bounds={'x': (55.0, 45.0), 'y': (0.0, 10.0), 'z': (0.0, 10.0)},
                grid_resolution=1.0,
                r_A1=0.2, r_A2=0.1, r_A3=0.1
            )
        
        # 누락된 축
        with pytest.raises(ValueError):
            AirspaceSafetyField(
                bounds={'x': (45.0, 55.0), 'y': (0.0, 10.0)},  # z 누락
                grid_resolution=1.0,
                r_A1=0.2, r_A2=0.1, r_A3=0.1
            )
    
    def test_invalid_resolution(self):
        """잘못된 해상도 테스트"""
        with pytest.raises(ValueError):
            AirspaceSafetyField(
                bounds={'x': (45.0, 55.0), 'y': (0.0, 10.0), 'z': (0.0, 10.0)},
                grid_resolution=-1.0,  # 음수
                r_A1=0.2, r_A2=0.1, r_A3=0.1
            )
    
    def test_position_to_index(self, default_field):
        """좌표 → 인덱스 변환 테스트"""
        # 중심점
        position = np.array([50.0, 5.0, 5.0])
        i, j, k = default_field.position_to_index(position)
        
        assert isinstance(i, (int, np.integer))
        assert isinstance(j, (int, np.integer))
        assert isinstance(k, (int, np.integer))
        assert 0 <= i < default_field.nx
        assert 0 <= j < default_field.ny
        assert 0 <= k < default_field.nz
    
    def test_index_to_position(self, default_field):
        """인덱스 → 좌표 변환 테스트"""
        idx = (5, 5, 5)
        position = default_field.index_to_position(idx)
        
        assert position.shape == (3,)
        assert default_field.x_min <= position[0] <= default_field.x_max
        assert default_field.y_min <= position[1] <= default_field.y_max
        assert default_field.z_min <= position[2] <= default_field.z_max
    
    def test_position_index_roundtrip(self, default_field):
        """좌표 ↔ 인덱스 변환 왕복 테스트"""
        # 인덱스에서 시작
        original_idx = (5, 5, 5)
        position = default_field.index_to_position(original_idx)
        recovered_idx = default_field.position_to_index(position)
        
        assert recovered_idx == original_idx
    
    def test_compute_point_safety_single_uav(self, default_field, single_uav):
        """단일 UAV에 대한 점 안전도 계산 테스트"""
        X = np.array([50.0, 5.0, 5.0])
        t0 = 0.0
        delta_t = 1.0
        
        prob = default_field._compute_point_safety(X, [single_uav], t0, delta_t)
        
        # 확률 범위 확인
        assert 0 <= prob <= 1
        assert isinstance(prob, (int, float))
    
    def test_compute_point_safety_multiple_uavs(self, default_field):
        """다중 UAV에 대한 점 안전도 계산 테스트 (Eq. 9)"""
        uav1 = UAV(
            id=1,
            position=np.array([50.0, 0.0, 5.0]),
            velocity=np.array([0.0, 10.0, 0.0]),
            Vf=5.0, Vb=2.0, Va=0.9, Vd=1.5, Vl=3.0,
            response_time=60
        )
        
        uav2 = UAV(
            id=2,
            position=np.array([48.0, 2.0, 5.0]),
            velocity=np.array([2.0, 8.0, 0.0]),
            Vf=5.0, Vb=2.0, Va=0.9, Vd=1.5, Vl=3.0,
            response_time=60
        )
        
        X = np.array([50.0, 10.0, 5.0])
        t0 = 0.0
        delta_t = 1.0
        
        # 단일 UAV 확률들
        prob1 = default_field._compute_point_safety(X, [uav1], t0, delta_t)
        prob2 = default_field._compute_point_safety(X, [uav2], t0, delta_t)
        
        # 다중 UAV 확률
        prob_combined = default_field._compute_point_safety(
            X, [uav1, uav2], t0, delta_t
        )
        
        # Eq. (9): s(X) = 1 - (1 - p1)(1 - p2)
        # 따라서 prob_combined >= max(prob1, prob2)
        assert prob_combined >= max(prob1, prob2) - 1e-10
        assert 0 <= prob_combined <= 1
    
    def test_compute_field_small_grid(self):
        """작은 그리드로 안전 필드 계산 테스트"""
        # 작은 그리드 (빠른 테스트)
        bounds = {
            'x': (49.0, 51.0),
            'y': (0.0, 2.0),
            'z': (4.0, 6.0)
        }
        field = AirspaceSafetyField(
            bounds=bounds,
            grid_resolution=1.0,
            r_A1=0.2,
            r_A2=0.1,
            r_A3=0.1
        )
        
        uav = UAV(
            id=1,
            position=np.array([50.0, 0.0, 5.0]),
            velocity=np.array([0.0, 10.0, 0.0]),
            Vf=5.0, Vb=2.0, Va=0.9, Vd=1.5, Vl=3.0,
            response_time=60
        )
        
        # 순차 처리로 계산 (빠름)
        result = field.compute_field(
            uavs=[uav],
            t0=0.0,
            delta_t=1.0,
            parallel=False,
            verbose=False
        )
        
        # 결과 확인
        assert result.shape == field.grid_shape
        assert np.all(result >= 0)
        assert np.all(result <= 1)
        assert field.field is not None
        np.testing.assert_array_equal(result, field.field)
    
    def test_get_value_at_position(self):
        """특정 위치 값 조회 테스트"""
        bounds = {
            'x': (49.0, 51.0),
            'y': (0.0, 2.0),
            'z': (4.0, 6.0)
        }
        field = AirspaceSafetyField(
            bounds=bounds,
            grid_resolution=1.0,
            r_A1=0.2,
            r_A2=0.1,
            r_A3=0.1
        )
        
        uav = UAV(
            id=1,
            position=np.array([50.0, 0.0, 5.0]),
            velocity=np.array([0.0, 10.0, 0.0]),
            Vf=5.0, Vb=2.0, Va=0.9, Vd=1.5, Vl=3.0,
            response_time=60
        )
        
        field.compute_field(uavs=[uav], t0=0.0, delta_t=1.0, parallel=False)
        
        # 값 조회
        position = np.array([50.0, 1.0, 5.0])
        value = field.get_value_at_position(position)
        
        assert 0 <= value <= 1
        assert isinstance(value, (float, np.floating))
    
    def test_get_value_at_position_before_compute(self, default_field):
        """계산 전 값 조회 시 에러 테스트"""
        with pytest.raises(ValueError, match="compute_field"):
            default_field.get_value_at_position(np.array([50.0, 5.0, 5.0]))
    
    def test_get_dangerous_regions(self):
        """위험 영역 추출 테스트"""
        bounds = {
            'x': (49.0, 51.0),
            'y': (0.0, 2.0),
            'z': (4.0, 6.0)
        }
        field = AirspaceSafetyField(
            bounds=bounds,
            grid_resolution=1.0,
            r_A1=0.2,
            r_A2=0.1,
            r_A3=0.1
        )
        
        uav = UAV(
            id=1,
            position=np.array([50.0, 0.0, 5.0]),
            velocity=np.array([0.0, 10.0, 0.0]),
            Vf=5.0, Vb=2.0, Va=0.9, Vd=1.5, Vl=3.0,
            response_time=60
        )
        
        field.compute_field(uavs=[uav], t0=0.0, delta_t=1.0, parallel=False)
        
        # 위험 영역 추출
        dangerous = field.get_dangerous_regions(threshold=0.001)
        
        # 결과 확인
        assert dangerous.shape[1] == 3  # [x, y, z]
        assert len(dangerous) >= 0  # 0개 이상
    
    def test_get_dangerous_regions_before_compute(self, default_field):
        """계산 전 위험 영역 추출 시 에러 테스트"""
        with pytest.raises(ValueError, match="compute_field"):
            default_field.get_dangerous_regions()
    
    def test_get_statistics(self):
        """통계 조회 테스트"""
        bounds = {
            'x': (49.0, 51.0),
            'y': (0.0, 2.0),
            'z': (4.0, 6.0)
        }
        field = AirspaceSafetyField(
            bounds=bounds,
            grid_resolution=1.0,
            r_A1=0.2,
            r_A2=0.1,
            r_A3=0.1
        )
        
        uav = UAV(
            id=1,
            position=np.array([50.0, 0.0, 5.0]),
            velocity=np.array([0.0, 10.0, 0.0]),
            Vf=5.0, Vb=2.0, Va=0.9, Vd=1.5, Vl=3.0,
            response_time=60
        )
        
        field.compute_field(uavs=[uav], t0=0.0, delta_t=1.0, parallel=False)
        
        stats = field.get_statistics()
        
        assert 'max' in stats
        assert 'min' in stats
        assert 'mean' in stats
        assert 'std' in stats
        assert 'median' in stats
        assert 'dangerous_cells_1pct' in stats
        
        assert 0 <= stats['min'] <= stats['max'] <= 1
        assert 0 <= stats['mean'] <= 1
    
    def test_compute_field_empty_uav_list(self, default_field):
        """빈 UAV 리스트로 계산 시 에러 테스트"""
        with pytest.raises(ValueError, match="비어있습니다"):
            default_field.compute_field(uavs=[], t0=0.0, delta_t=1.0)
    
    def test_repr(self, default_field):
        """문자열 표현 테스트"""
        repr_str = repr(default_field)
        
        assert "AirspaceSafetyField" in repr_str
        assert "bounds" in repr_str
        assert "grid_shape" in repr_str
        assert "미계산" in repr_str  # 아직 계산 안 됨


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
