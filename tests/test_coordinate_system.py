"""
좌표계 변환 모듈 테스트
"""

import pytest
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point, LineString
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from ols_engine.core.coordinate_system import CoordinateTransform


class TestCoordinateTransform:
    
    def setup_method(self):
        """각 테스트 메서드 실행 전 설정"""
        self.coord_transform = CoordinateTransform()
        
        # 테스트용 GeoDataFrame 생성 (EPSG:4326)
        self.test_points_wgs84 = gpd.GeoDataFrame({
            'id': ['P1', 'P2', 'P3'],
            'name': ['Point 1', 'Point 2', 'Point 3']
        }, geometry=[
            Point(127.0, 37.5),  # 서울 근처
            Point(127.1, 37.6),
            Point(126.9, 37.4)
        ], crs='EPSG:4326')
        
        # 테스트용 활주로 파라미터
        self.thr_x = 198345.12
        self.thr_y = 531234.88
        self.bearing_deg = 340.1
    
    def test_ensure_target_crs_conversion(self):
        """좌표계 변환 테스트"""
        # WGS84 -> EPSG:5186 변환
        converted_gdf = self.coord_transform.ensure_target_crs(self.test_points_wgs84)
        
        assert converted_gdf.crs.to_epsg() == 5186
        assert len(converted_gdf) == len(self.test_points_wgs84)
        
        # 좌표값이 EPSG:5186 범위에 있는지 확인
        bounds = converted_gdf.total_bounds
        min_x, min_y, max_x, max_y = bounds
        
        assert 100000 <= min_x <= 300000
        assert 400000 <= min_y <= 600000
    
    def test_ensure_target_crs_already_correct(self):
        """이미 올바른 좌표계인 경우 테스트"""
        # EPSG:5186으로 변환된 데이터
        converted_first = self.coord_transform.ensure_target_crs(self.test_points_wgs84)
        
        # 다시 변환 시도
        converted_second = self.coord_transform.ensure_target_crs(converted_first)
        
        assert converted_second.crs.to_epsg() == 5186
        assert len(converted_second) == len(converted_first)
        
        # 좌표값이 동일해야 함
        np.testing.assert_array_almost_equal(
            converted_first.geometry.x.values,
            converted_second.geometry.x.values,
            decimal=6
        )
    
    def test_create_runway_frame(self):
        """활주로 프레임 변환 행렬 생성 테스트"""
        transform_matrix, rotation_rad = self.coord_transform.create_runway_frame(
            self.thr_x, self.thr_y, self.bearing_deg
        )
        
        # 변환 행렬이 3x3인지 확인
        assert transform_matrix.shape == (3, 3)
        
        # 회전 행렬의 속성 확인 (직교 행렬)
        rotation_part = transform_matrix[:2, :2]
        identity = rotation_part @ rotation_part.T
        np.testing.assert_array_almost_equal(identity, np.eye(2), decimal=10)
        
        # 회전각이 올바른지 확인
        expected_rotation = -np.radians(self.bearing_deg)
        assert abs(rotation_rad - expected_rotation) < 1e-10
    
    def test_transform_point_geometry(self):
        """Point 지오메트리 변환 테스트"""
        # 변환 행렬 생성
        transform_matrix, _ = self.coord_transform.create_runway_frame(
            self.thr_x, self.thr_y, self.bearing_deg
        )
        
        # THR 위치 Point 생성
        thr_point = Point(self.thr_x, self.thr_y)
        
        # 변환 수행
        transformed_point = self.coord_transform._transform_point(thr_point, transform_matrix)
        
        # THR 위치는 원점 (0, 0)이 되어야 함
        assert abs(transformed_point.x) < 1e-10
        assert abs(transformed_point.y) < 1e-10
    
    def test_transform_linestring_geometry(self):
        """LineString 지오메트리 변환 테스트"""
        # 변환 행렬 생성
        transform_matrix, _ = self.coord_transform.create_runway_frame(
            self.thr_x, self.thr_y, self.bearing_deg
        )
        
        # 테스트용 LineString (THR에서 시작하는 선)
        line = LineString([
            (self.thr_x, self.thr_y),
            (self.thr_x + 1000, self.thr_y + 500)
        ])
        
        # 변환 수행
        transformed_line = self.coord_transform._transform_linestring(line, transform_matrix)
        
        # 첫 번째 점은 원점이어야 함
        coords = list(transformed_line.coords)
        assert abs(coords[0][0]) < 1e-10
        assert abs(coords[0][1]) < 1e-10
    
    def test_get_runway_aligned_coordinates(self):
        """전체 좌표 정렬 프로세스 테스트"""
        # EPSG:5186 데이터 생성
        projected_gdf = self.coord_transform.ensure_target_crs(self.test_points_wgs84)
        
        # 활주로 기준 정렬
        aligned_gdf = self.coord_transform.get_runway_aligned_coordinates(
            projected_gdf, self.thr_x, self.thr_y, self.bearing_deg
        )
        
        assert len(aligned_gdf) == len(projected_gdf)
        assert aligned_gdf.crs == projected_gdf.crs
        
        # 변환된 좌표가 합리적인 범위에 있는지 확인
        bounds = aligned_gdf.total_bounds
        assert all(abs(coord) < 1000000 for coord in bounds)  # 과도하게 크지 않은 값
    
    def test_validate_coordinates_valid_data(self):
        """유효한 좌표 데이터 검증 테스트"""
        # EPSG:5186으로 변환된 유효한 데이터
        projected_gdf = self.coord_transform.ensure_target_crs(self.test_points_wgs84)
        
        is_valid, errors = self.coord_transform.validate_coordinates(projected_gdf)
        
        assert is_valid
        assert len(errors) == 0
    
    def test_validate_coordinates_invalid_range(self):
        """좌표 범위를 벗어난 데이터 검증 테스트"""
        # 범위를 벗어난 좌표 데이터 생성
        invalid_gdf = gpd.GeoDataFrame({
            'id': ['P1']
        }, geometry=[
            Point(500000, 700000)  # 한국 영역을 벗어난 좌표
        ], crs='EPSG:5186')
        
        is_valid, errors = self.coord_transform.validate_coordinates(invalid_gdf)
        
        assert not is_valid
        assert len(errors) > 0
        assert any("좌표 범위" in error for error in errors)
    
    def test_validate_coordinates_null_geometry(self):
        """빈 지오메트리 검증 테스트"""
        # 빈 지오메트리가 포함된 데이터
        null_geom_gdf = gpd.GeoDataFrame({
            'id': ['P1', 'P2']
        }, geometry=[
            Point(200000, 500000),
            None
        ], crs='EPSG:5186')
        
        is_valid, errors = self.coord_transform.validate_coordinates(null_geom_gdf)
        
        assert not is_valid
        assert len(errors) > 0
        assert any("빈 지오메트리" in error for error in errors)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])