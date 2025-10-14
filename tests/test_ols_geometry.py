"""
OLS 기하학 모델 테스트
"""

import pytest
import math
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from ols_engine.core.geometry import (
    OLSParameters, OLSGeometry, ApproachSurface, 
    TakeoffSurface, TransitionalSurface, 
    InnerHorizontalSurface, ConicalSurface
)


class TestOLSParameters:
    
    def test_default_parameters(self):
        """기본 파라미터 테스트"""
        params = OLSParameters()
        
        # ICAO Annex 14 기본값 확인
        assert params.approach_slope == 0.025  # 1:40
        assert params.takeoff_slope == 0.02    # 1:50
        assert params.transitional_slope == 0.143  # 1:7
        assert params.inner_horizontal_radius_m == 4000
        assert params.inner_horizontal_height_m == 45
        assert params.conical_slope == 0.05  # 1:20


class TestApproachSurface:
    
    def setup_method(self):
        """테스트 설정"""
        self.params = OLSParameters()
        self.approach_surface = ApproachSurface(self.params)
        self.thr_elev_m = 10.0
    
    def test_approach_surface_within_range(self):
        """접근표면 범위 내 점 테스트"""
        # 중앙선 상의 점
        assert self.approach_surface.is_within_surface(1000, 0)
        
        # 표면 가장자리 점
        width_at_1000m = self.params.approach_inner_width_m + 2 * self.params.approach_divergence * 1000
        half_width = width_at_1000m / 2
        assert self.approach_surface.is_within_surface(1000, half_width - 1)
        assert not self.approach_surface.is_within_surface(1000, half_width + 1)
    
    def test_approach_surface_outside_range(self):
        """접근표면 범위 밖 점 테스트"""
        # x < 0 (THR 뒤쪽)
        assert not self.approach_surface.is_within_surface(-100, 0)
        
        # 길이 초과
        assert not self.approach_surface.is_within_surface(self.params.approach_length_m + 100, 0)
    
    def test_approach_allowable_elevation(self):
        """접근표면 허용고도 계산 테스트"""
        # 중앙선 상의 점
        x, y = 1000, 0
        z_allow = self.approach_surface.get_allowable_elevation(x, y, self.thr_elev_m)
        
        expected_elev = self.thr_elev_m + self.params.approach_slope * x
        assert abs(z_allow - expected_elev) < 1e-6
        
        # 범위 밖 점
        z_allow = self.approach_surface.get_allowable_elevation(-100, 0, self.thr_elev_m)
        assert z_allow is None


class TestTakeoffSurface:
    
    def setup_method(self):
        """테스트 설정"""
        self.params = OLSParameters()
        self.takeoff_surface = TakeoffSurface(self.params)
        self.thr_elev_m = 10.0
    
    def test_takeoff_allowable_elevation(self):
        """이륙표면 허용고도 계산 테스트"""
        x, y = 2000, 0
        z_allow = self.takeoff_surface.get_allowable_elevation(x, y, self.thr_elev_m)
        
        expected_elev = self.thr_elev_m + self.params.takeoff_slope * x
        assert abs(z_allow - expected_elev) < 1e-6


class TestTransitionalSurface:
    
    def setup_method(self):
        """테스트 설정"""
        self.params = OLSParameters()
        self.runway_width_m = 45
        self.transitional_surface = TransitionalSurface(self.params, self.runway_width_m)
        self.thr_elev_m = 10.0
    
    def test_transitional_within_surface(self):
        """전이표면 범위 확인 테스트"""
        half_runway = self.runway_width_m / 2
        
        # 활주로 내부 (전이표면 적용 안됨)
        assert not self.transitional_surface.is_within_surface(0, half_runway - 1)
        
        # 활주로 밖 (전이표면 적용)
        assert self.transitional_surface.is_within_surface(0, half_runway + 1)
    
    def test_transitional_allowable_elevation(self):
        """전이표면 허용고도 계산 테스트"""
        half_runway = self.runway_width_m / 2
        x, y = 0, half_runway + 100  # 활주로 가장자리에서 100m 떨어진 지점
        
        z_allow = self.transitional_surface.get_allowable_elevation(x, y, self.thr_elev_m)
        
        expected_elev = self.thr_elev_m + self.params.transitional_slope * 100
        expected_elev = min(expected_elev, self.thr_elev_m + self.params.transitional_height_cap_m)
        
        assert abs(z_allow - expected_elev) < 1e-6


class TestInnerHorizontalSurface:
    
    def setup_method(self):
        """테스트 설정"""
        self.params = OLSParameters()
        self.arp_elev_m = 10.0
        self.inner_horizontal = InnerHorizontalSurface(self.params, self.arp_elev_m)
    
    def test_inner_horizontal_within_surface(self):
        """내수평표면 범위 확인 테스트"""
        radius = self.params.inner_horizontal_radius_m
        
        # 반지름 내부
        assert self.inner_horizontal.is_within_surface(radius - 100, 0)
        
        # 반지름 외부
        assert not self.inner_horizontal.is_within_surface(radius + 100, 0)
        
        # 원형 경계 확인
        x, y = radius * 0.7, radius * 0.7  # 45도 지점
        distance = math.sqrt(x*x + y*y)
        if distance <= radius:
            assert self.inner_horizontal.is_within_surface(x, y)
    
    def test_inner_horizontal_allowable_elevation(self):
        """내수평표면 허용고도 계산 테스트"""
        x, y = 1000, 1000
        z_allow = self.inner_horizontal.get_allowable_elevation(x, y, 7.3)  # THR 표고는 무관
        
        expected_elev = self.arp_elev_m + self.params.inner_horizontal_height_m
        assert abs(z_allow - expected_elev) < 1e-6


class TestConicalSurface:
    
    def setup_method(self):
        """테스트 설정"""
        self.params = OLSParameters()
        self.arp_elev_m = 10.0
        self.conical_surface = ConicalSurface(self.params, self.arp_elev_m)
    
    def test_conical_within_surface(self):
        """원추표면 범위 확인 테스트"""
        inner_radius = self.params.inner_horizontal_radius_m
        
        # 내수평표면 내부 (원추표면 적용 안됨)
        assert not self.conical_surface.is_within_surface(inner_radius - 100, 0)
        
        # 내수평표면과 원추표면 사이
        assert self.conical_surface.is_within_surface(inner_radius + 100, 0)
        
        # 원추표면 최대 범위 밖
        max_radius = inner_radius + self.params.conical_height_m / self.params.conical_slope
        assert not self.conical_surface.is_within_surface(max_radius + 100, 0)
    
    def test_conical_allowable_elevation(self):
        """원추표면 허용고도 계산 테스트"""
        inner_radius = self.params.inner_horizontal_radius_m
        x, y = inner_radius + 1000, 0
        
        z_allow = self.conical_surface.get_allowable_elevation(x, y, 7.3)  # THR 표고는 무관
        
        radial_distance = 1000
        inner_h_elev = self.arp_elev_m + self.params.inner_horizontal_height_m
        expected_elev = inner_h_elev + self.params.conical_slope * radial_distance
        max_elev = inner_h_elev + self.params.conical_height_m
        expected_elev = min(expected_elev, max_elev)
        
        assert abs(z_allow - expected_elev) < 1e-6


class TestOLSGeometry:
    
    def setup_method(self):
        """테스트 설정"""
        self.runway_config = {
            "rwy_id": "TEST-36",
            "annex14": {
                "approach": {"slope": 0.025, "inner_width_m": 300, "divergence": 0.10, "length_m": 15000},
                "takeoff": {"slope": 0.02, "inner_width_m": 180, "divergence": 0.10, "length_m": 15000},
                "transitional": {"slope": 0.143, "height_cap_m": 45},
                "inner_horizontal": {"radius_m": 4000, "height_m": 45},
                "conical": {"slope": 0.05, "height_m": 100}
            }
        }
        self.arp_elev_m = 10.0
        self.ols_geometry = OLSGeometry(self.runway_config, self.arp_elev_m)
    
    def test_ols_geometry_initialization(self):
        """OLS 기하학 모델 초기화 테스트"""
        assert len(self.ols_geometry.surfaces) == 5  # 5개 표면
        assert self.ols_geometry.arp_elev_m == self.arp_elev_m
    
    def test_minimum_allowable_elevation_thr(self):
        """THR 위치에서의 최소 허용고도 테스트"""
        thr_elev_m = 7.3
        z_allow, surface = self.ols_geometry.get_minimum_allowable_elevation(0, 0, thr_elev_m)
        
        # THR 위치에서는 내수평표면이 적용될 것으로 예상
        expected_inner_h = self.arp_elev_m + self.ols_geometry.params.inner_horizontal_height_m
        
        assert z_allow is not None
        assert z_allow <= expected_inner_h  # 최솟값이므로 내수평표면 이하
    
    def test_minimum_allowable_elevation_approach_centerline(self):
        """접근 중앙선상의 최소 허용고도 테스트"""
        thr_elev_m = 7.3
        x, y = 1000, 0  # 접근 중앙선 1km 지점
        
        z_allow, surface = self.ols_geometry.get_minimum_allowable_elevation(x, y, thr_elev_m)
        
        # 접근표면이 적용되어야 함
        expected_approach = thr_elev_m + self.ols_geometry.params.approach_slope * x
        
        assert z_allow is not None
        assert abs(z_allow - expected_approach) < 1e-6
        assert "approach" in surface.lower()
    
    def test_minimum_allowable_elevation_outside_ols(self):
        """OLS 범위 밖 위치 테스트"""
        thr_elev_m = 7.3
        x, y = 50000, 50000  # 매우 먼 거리
        
        z_allow, surface = self.ols_geometry.get_minimum_allowable_elevation(x, y, thr_elev_m)
        
        # OLS 범위 밖이므로 None 반환
        assert z_allow is None
        assert surface == "none"
    
    def test_generate_validation_grid(self):
        """검증 격자 생성 테스트"""
        thr_elev_m = 7.3
        grid_df = self.ols_geometry.generate_validation_grid(
            x_range=(-1000, 1000),
            y_range=(-1000, 1000),
            spacing_m=500,
            thr_elev_m=thr_elev_m
        )
        
        assert not grid_df.empty
        assert 'x' in grid_df.columns
        assert 'y' in grid_df.columns
        assert 'z_allow_m' in grid_df.columns
        assert 'controlling_surface' in grid_df.columns
        
        # 격자 간격 확인
        expected_points = ((1000 - (-1000)) // 500 + 1) ** 2
        assert len(grid_df) == expected_points


if __name__ == '__main__':
    pytest.main([__file__, '-v'])