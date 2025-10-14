"""
좌표계 변환 및 프레임 정렬 모듈

EPSG:5186으로 강제 변환하고, 활주로 THR을 원점으로 하여
활주로 방향을 +x축으로 정렬하는 좌표 변환을 수행합니다.
"""

import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point, LineString
from shapely.affinity import translate, rotate
from pyproj import CRS, Transformer
from typing import Tuple, Optional, Union
from loguru import logger


class CoordinateTransform:
    """좌표계 변환 및 활주로 기준 프레임 정렬"""
    
    TARGET_EPSG = 5186  # 중부 TM 좌표계
    
    def __init__(self):
        self.target_crs = CRS.from_epsg(self.TARGET_EPSG)
        self.transformers = {}  # 소스 CRS별 변환기 캐시
        
    def ensure_target_crs(self, gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """
        모든 GeoDataFrame을 EPSG:5186으로 강제 변환
        
        Args:
            gdf: 입력 GeoDataFrame
            
        Returns:
            EPSG:5186으로 변환된 GeoDataFrame
            
        Raises:
            ValueError: CRS 정보가 없거나 변환 실패시
        """
        if gdf.crs is None:
            raise ValueError("입력 데이터에 CRS 정보가 없습니다. CRS를 명시적으로 설정하세요.")
            
        if gdf.crs.to_epsg() == self.TARGET_EPSG:
            logger.debug(f"이미 EPSG:{self.TARGET_EPSG} 좌표계입니다.")
            return gdf.copy()
            
        source_epsg = gdf.crs.to_epsg()
        logger.info(f"좌표계 변환: EPSG:{source_epsg} → EPSG:{self.TARGET_EPSG}")
        
        try:
            # 변환기 캐시 확인
            cache_key = source_epsg
            if cache_key not in self.transformers:
                self.transformers[cache_key] = Transformer.from_crs(
                    gdf.crs, self.target_crs, always_xy=True
                )
            
            # 좌표 변환 수행
            transformed_gdf = gdf.to_crs(epsg=self.TARGET_EPSG)
            
            # 변환 결과 검증
            if len(transformed_gdf) != len(gdf):
                raise ValueError("좌표 변환 중 데이터 손실이 발생했습니다.")
                
            logger.debug(f"좌표 변환 완료: {len(transformed_gdf)} 개 피처")
            return transformed_gdf
            
        except Exception as e:
            raise ValueError(f"좌표계 변환 실패: {str(e)}")
    
    def create_runway_frame(self, thr_x: float, thr_y: float, 
                          bearing_deg: float) -> Tuple[np.ndarray, float]:
        """
        활주로 THR을 원점으로 하는 변환 행렬 생성
        
        Args:
            thr_x: THR X 좌표 (EPSG:5186)
            thr_y: THR Y 좌표 (EPSG:5186) 
            bearing_deg: 활주로 방위각 (진북 기준, 도)
            
        Returns:
            tuple: (변환 행렬 3x3, 회전각도 라디안)
        """
        # 활주로 방향을 +x축으로 만드는 회전각 계산
        # bearing_deg가 활주로가 향하는 방향이므로, 이를 +x축(0도)으로 회전
        rotation_rad = -np.radians(bearing_deg)
        
        cos_r = np.cos(rotation_rad)
        sin_r = np.sin(rotation_rad)
        
        # 1단계: THR을 원점으로 평행이동 -> 2단계: 회전
        # 최종 변환: T = R * T_translate
        transform_matrix = np.array([
            [cos_r, -sin_r, -thr_x * cos_r + thr_y * sin_r],
            [sin_r,  cos_r, -thr_x * sin_r - thr_y * cos_r],
            [0,      0,      1]
        ])
        
        logger.debug(f"활주로 프레임 생성: THR({thr_x:.2f}, {thr_y:.2f}), "
                    f"방위각 {bearing_deg:.1f}°")
        
        return transform_matrix, rotation_rad
    
    def transform_to_runway_frame(self, gdf: gpd.GeoDataFrame,
                                transform_matrix: np.ndarray) -> gpd.GeoDataFrame:
        """
        GeoDataFrame을 활주로 기준 좌표계로 변환
        
        Args:
            gdf: 변환할 GeoDataFrame
            transform_matrix: 변환 행렬 (3x3)
            
        Returns:
            변환된 GeoDataFrame
        """
        result_gdf = gdf.copy()
        
        # 각 지오메트리를 변환
        transformed_geoms = []
        
        for geom in gdf.geometry:
            if geom is None:
                transformed_geoms.append(None)
                continue
                
            transformed_geom = self._transform_geometry(geom, transform_matrix)
            transformed_geoms.append(transformed_geom)
        
        result_gdf.geometry = transformed_geoms
        logger.debug(f"활주로 프레임 변환 완료: {len(result_gdf)} 개 피처")
        
        return result_gdf
    
    def _transform_geometry(self, geom, transform_matrix: np.ndarray):
        """단일 지오메트리 변환"""
        if geom.geom_type == 'Point':
            return self._transform_point(geom, transform_matrix)
        elif geom.geom_type == 'LineString':
            return self._transform_linestring(geom, transform_matrix)
        elif geom.geom_type == 'Polygon':
            return self._transform_polygon(geom, transform_matrix)
        else:
            # MultiPoint, MultiLineString 등 복합 지오메트리
            return self._transform_multi_geometry(geom, transform_matrix)
    
    def _transform_point(self, point: Point, transform_matrix: np.ndarray) -> Point:
        """Point 변환"""
        x, y = point.x, point.y
        
        # 동차 좌표 변환
        coords_homo = np.array([x, y, 1])
        transformed_homo = transform_matrix @ coords_homo
        
        return Point(transformed_homo[0], transformed_homo[1])
    
    def _transform_linestring(self, line: LineString, 
                            transform_matrix: np.ndarray) -> LineString:
        """LineString 변환"""
        coords = np.array(line.coords)
        
        # 모든 좌표점을 동차 좌표로 변환
        n_points = len(coords)
        coords_homo = np.ones((n_points, 3))
        coords_homo[:, :2] = coords
        
        # 행렬 변환 적용
        transformed_homo = (transform_matrix @ coords_homo.T).T
        
        return LineString(transformed_homo[:, :2])
    
    def _transform_polygon(self, polygon, transform_matrix: np.ndarray):
        """Polygon 변환 (외곽선만 처리, 구멍 무시)"""
        # 외곽선만 변환 (구멍은 복잡성 때문에 생략)
        exterior_coords = np.array(polygon.exterior.coords)
        
        # 동차 좌표 변환
        n_points = len(exterior_coords)
        coords_homo = np.ones((n_points, 3))
        coords_homo[:, :2] = exterior_coords
        
        transformed_homo = (transform_matrix @ coords_homo.T).T
        
        from shapely.geometry import Polygon
        return Polygon(transformed_homo[:, :2])
    
    def _transform_multi_geometry(self, multi_geom, transform_matrix: np.ndarray):
        """Multi* 지오메트리 변환"""
        transformed_parts = []
        
        for part in multi_geom.geoms:
            transformed_part = self._transform_geometry(part, transform_matrix)
            transformed_parts.append(transformed_part)
        
        # 원래 타입에 맞는 Multi 지오메트리 생성
        if multi_geom.geom_type == 'MultiPoint':
            from shapely.geometry import MultiPoint
            return MultiPoint(transformed_parts)
        elif multi_geom.geom_type == 'MultiLineString':
            from shapely.geometry import MultiLineString  
            return MultiLineString(transformed_parts)
        elif multi_geom.geom_type == 'MultiPolygon':
            from shapely.geometry import MultiPolygon
            return MultiPolygon(transformed_parts)
        else:
            return multi_geom  # 처리할 수 없는 타입은 원본 반환
    
    def get_runway_aligned_coordinates(self, gdf: gpd.GeoDataFrame,
                                     thr_x: float, thr_y: float,
                                     bearing_deg: float) -> gpd.GeoDataFrame:
        """
        전체 프로세스: CRS 변환 + 활주로 프레임 정렬
        
        Args:
            gdf: 입력 GeoDataFrame
            thr_x: THR X 좌표
            thr_y: THR Y 좌표  
            bearing_deg: 활주로 방위각
            
        Returns:
            활주로 기준으로 정렬된 GeoDataFrame
        """
        # 1단계: EPSG:5186으로 변환
        gdf_projected = self.ensure_target_crs(gdf)
        
        # 2단계: 활주로 프레임 변환 행렬 생성
        transform_matrix, _ = self.create_runway_frame(thr_x, thr_y, bearing_deg)
        
        # 3단계: 활주로 기준 좌표계로 변환
        gdf_aligned = self.transform_to_runway_frame(gdf_projected, transform_matrix)
        
        return gdf_aligned
    
    def validate_coordinates(self, gdf: gpd.GeoDataFrame) -> Tuple[bool, list]:
        """
        좌표 유효성 검증
        
        Args:
            gdf: 검증할 GeoDataFrame
            
        Returns:
            tuple: (전체 유효성, 에러 목록)
        """
        errors = []
        
        # 빈 지오메트리 체크
        null_geoms = gdf.geometry.isnull().sum()
        if null_geoms > 0:
            errors.append(f"빈 지오메트리 {null_geoms}개 발견")
        
        # 무효한 지오메트리 체크  
        invalid_geoms = ~gdf.geometry.is_valid
        invalid_count = invalid_geoms.sum()
        if invalid_count > 0:
            errors.append(f"무효한 지오메트리 {invalid_count}개 발견")
        
        # 좌표 범위 체크 (EPSG:5186 기준 대략적 한국 영역)
        bounds = gdf.total_bounds
        if len(bounds) == 4:
            min_x, min_y, max_x, max_y = bounds
            
            # EPSG:5186 대략적 유효 범위 (한국)
            if not (100000 <= min_x <= 300000 and 400000 <= min_y <= 600000):
                errors.append(f"좌표 범위가 EPSG:5186 한국 영역을 벗어남: "
                            f"X({min_x:.0f}~{max_x:.0f}), Y({min_y:.0f}~{max_y:.0f})")
        
        is_valid = len(errors) == 0
        
        if is_valid:
            logger.info("좌표 유효성 검증 통과")
        else:
            logger.warning(f"좌표 유효성 검증 실패: {'; '.join(errors)}")
        
        return is_valid, errors