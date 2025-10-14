"""
장애물 침투 판정 모듈

각 장애물의 최고점과 OLS 허용고도를 비교하여 
침투 여부와 침투량을 결정론적으로 계산합니다.
"""

import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point, Polygon
from typing import List, Dict, Tuple, Optional, Union
from dataclasses import dataclass
from loguru import logger

from .geometry import OLSGeometry
from .coordinate_system import CoordinateTransform


@dataclass 
class PenetrationResult:
    """침투 판정 결과"""
    obj_id: str
    rwy_id: str
    x: float                    # 활주로 프레임 X 좌표
    y: float                    # 활주로 프레임 Y 좌표
    top_elev_m: float          # 장애물 최고점 표고 (AMSL)
    z_allow_m: Optional[float] # 허용고도 (AMSL)
    controlling_surface: str    # 제어 표면
    penetration_m: float       # 침투량 (양수=침투, 음수=여유)
    is_penetration: bool       # 침투 여부
    

class ObstaclePenetrationEngine:
    """장애물 침투 판정 엔진"""
    
    def __init__(self, coordinate_transform: CoordinateTransform):
        self.coord_transform = coordinate_transform
        self.validation_errors = []
        
    def analyze_penetrations(self, obstacles_gdf: gpd.GeoDataFrame,
                           runway_configs: List[dict],
                           arp_elev_m: float) -> List[PenetrationResult]:
        """
        전체 침투 분석 실행
        
        Args:
            obstacles_gdf: 장애물 GeoDataFrame (EPSG:5186)
            runway_configs: 활주로 설정 리스트
            arp_elev_m: 공항기준점 표고
            
        Returns:
            침투 결과 리스트
        """
        all_results = []
        
        # 각 활주로별 침투 분석
        for rwy_config in runway_configs:
            rwy_id = rwy_config['rwy_id']
            logger.info(f"활주로 {rwy_id} 침투 분석 시작")
            
            # 활주로별 침투 분석
            rwy_results = self._analyze_runway_penetrations(
                obstacles_gdf, rwy_config, arp_elev_m
            )
            
            all_results.extend(rwy_results)
            logger.info(f"활주로 {rwy_id}: {len(rwy_results)}개 결과")
        
        logger.info(f"전체 침투 분석 완료: {len(all_results)}개 결과")
        return all_results
    
    def _analyze_runway_penetrations(self, obstacles_gdf: gpd.GeoDataFrame,
                                   runway_config: dict,
                                   arp_elev_m: float) -> List[PenetrationResult]:
        """단일 활주로 침투 분석"""
        results = []
        
        rwy_id = runway_config['rwy_id']
        thr_x = runway_config['thr_x']
        thr_y = runway_config['thr_y'] 
        thr_elev_m = runway_config['thr_elev_m']
        bearing_deg = runway_config['bearing_deg']
        
        # OLS 기하학 모델 생성
        ols_geometry = OLSGeometry(runway_config, arp_elev_m)
        
        # 활주로 프레임으로 좌표 변환
        obstacles_aligned = self.coord_transform.get_runway_aligned_coordinates(
            obstacles_gdf, thr_x, thr_y, bearing_deg
        )
        
        # 각 장애물 침투 판정
        for idx, obstacle in obstacles_aligned.iterrows():
            try:
                result = self._analyze_single_obstacle(
                    obstacle, rwy_id, ols_geometry, thr_elev_m
                )
                if result:
                    results.append(result)
                    
            except Exception as e:
                self.validation_errors.append(
                    f"장애물 {obstacle.get('obj_id', idx)} 처리 실패: {str(e)}"
                )
                logger.warning(f"장애물 처리 실패: {str(e)}")
        
        return results
    
    def _analyze_single_obstacle(self, obstacle: pd.Series, rwy_id: str,
                               ols_geometry: OLSGeometry,
                               thr_elev_m: float) -> Optional[PenetrationResult]:
        """단일 장애물 침투 분석"""
        # 필수 속성 확인
        obj_id = obstacle.get('obj_id', 'unknown')
        top_elev_m = obstacle.get('top_elev_m')
        
        if pd.isna(top_elev_m):
            self.validation_errors.append(f"장애물 {obj_id}: 표고 정보 없음")
            return None
        
        # 장애물 위치 추출
        geom = obstacle.geometry
        if geom is None or geom.is_empty:
            self.validation_errors.append(f"장애물 {obj_id}: 유효하지 않은 지오메트리")
            return None
        
        # 대표점 계산 (Point는 그대로, Polygon은 중심점)
        if geom.geom_type == 'Point':
            x, y = geom.x, geom.y
        elif geom.geom_type == 'Polygon':
            centroid = geom.centroid
            x, y = centroid.x, centroid.y
            
            # Polygon의 경우 최고점이 실제로는 모서리에 있을 수 있으므로
            # 더 정확한 분석을 위해 여러 점을 검사할 수도 있음
            # 여기서는 단순화하여 중심점만 사용
        else:
            self.validation_errors.append(f"장애물 {obj_id}: 지원하지 않는 지오메트리 타입")
            return None
        
        # OLS 허용고도 계산
        z_allow_m, controlling_surface = ols_geometry.get_minimum_allowable_elevation(
            x, y, thr_elev_m
        )
        
        # 침투량 계산
        if z_allow_m is not None:
            penetration_m = float(top_elev_m) - z_allow_m
            is_penetration = penetration_m > 0
        else:
            # OLS 범위 밖인 경우
            penetration_m = 0.0
            is_penetration = False
            controlling_surface = "outside_ols"
        
        result = PenetrationResult(
            obj_id=str(obj_id),
            rwy_id=rwy_id,
            x=float(x),
            y=float(y),
            top_elev_m=float(top_elev_m),
            z_allow_m=z_allow_m,
            controlling_surface=controlling_surface,
            penetration_m=penetration_m,
            is_penetration=is_penetration
        )
        
        if is_penetration:
            logger.debug(f"침투 발견: {obj_id} - {penetration_m:.2f}m "
                        f"({controlling_surface})")
        
        return result
    
    def create_penetration_gdf(self, results: List[PenetrationResult],
                             crs_epsg: int = 5186) -> gpd.GeoDataFrame:
        """침투 결과를 GeoDataFrame으로 변환"""
        if not results:
            # 빈 결과인 경우 스키마만 생성
            return gpd.GeoDataFrame({
                'obj_id': [],
                'rwy_id': [],
                'surface': [],
                'x': [],
                'y': [],
                'top_elev_m': [],
                'z_allow_m': [],
                'penetration_m': [],
                'geometry': []
            }, crs=f'EPSG:{crs_epsg}')
        
        # 결과 데이터 변환
        data = []
        geometries = []
        
        for result in results:
            data.append({
                'obj_id': result.obj_id,
                'rwy_id': result.rwy_id,
                'surface': result.controlling_surface,
                'x': result.x,
                'y': result.y,
                'top_elev_m': result.top_elev_m,
                'z_allow_m': result.z_allow_m,
                'penetration_m': result.penetration_m
            })
            
            # Point 지오메트리 생성 (활주로 프레임 좌표)
            geometries.append(Point(result.x, result.y))
        
        gdf = gpd.GeoDataFrame(data, geometry=geometries, crs=f'EPSG:{crs_epsg}')
        
        logger.info(f"침투 GeoDataFrame 생성: {len(gdf)}개 결과")
        return gdf
    
    def get_penetration_summary(self, results: List[PenetrationResult]) -> Dict:
        """침투 결과 요약 통계"""
        if not results:
            return {
                'total_obstacles': 0,
                'total_penetrations': 0,
                'penetration_rate': 0.0,
                'max_penetration_m': 0.0,
                'avg_penetration_m': 0.0,
                'by_surface': {},
                'by_runway': {}
            }
        
        # 전체 통계
        penetrations = [r for r in results if r.is_penetration]
        total_obstacles = len(results)
        total_penetrations = len(penetrations)
        penetration_rate = total_penetrations / total_obstacles if total_obstacles > 0 else 0.0
        
        if penetrations:
            max_penetration = max(p.penetration_m for p in penetrations)
            avg_penetration = sum(p.penetration_m for p in penetrations) / len(penetrations)
        else:
            max_penetration = 0.0
            avg_penetration = 0.0
        
        # 표면별 통계
        by_surface = {}
        for result in penetrations:
            surface = result.controlling_surface
            if surface not in by_surface:
                by_surface[surface] = {
                    'count': 0,
                    'max_penetration_m': 0.0,
                    'avg_penetration_m': 0.0,
                    'penetrations': []
                }
            by_surface[surface]['count'] += 1
            by_surface[surface]['penetrations'].append(result.penetration_m)
        
        # 표면별 평균/최대값 계산
        for surface_stats in by_surface.values():
            pens = surface_stats['penetrations']
            surface_stats['max_penetration_m'] = max(pens)
            surface_stats['avg_penetration_m'] = sum(pens) / len(pens)
            del surface_stats['penetrations']  # 원본 데이터 제거
        
        # 활주로별 통계
        by_runway = {}
        for result in penetrations:
            rwy_id = result.rwy_id
            if rwy_id not in by_runway:
                by_runway[rwy_id] = {
                    'count': 0,
                    'max_penetration_m': 0.0,
                    'avg_penetration_m': 0.0,
                    'penetrations': []
                }
            by_runway[rwy_id]['count'] += 1
            by_runway[rwy_id]['penetrations'].append(result.penetration_m)
        
        # 활주로별 평균/최대값 계산
        for rwy_stats in by_runway.values():
            pens = rwy_stats['penetrations']
            rwy_stats['max_penetration_m'] = max(pens)
            rwy_stats['avg_penetration_m'] = sum(pens) / len(pens)
            del rwy_stats['penetrations']
        
        summary = {
            'total_obstacles': total_obstacles,
            'total_penetrations': total_penetrations,
            'penetration_rate': penetration_rate,
            'max_penetration_m': max_penetration,
            'avg_penetration_m': avg_penetration,
            'by_surface': by_surface,
            'by_runway': by_runway
        }
        
        logger.info(f"침투 요약: {total_penetrations}/{total_obstacles} "
                   f"({penetration_rate:.1%}), 최대 {max_penetration:.2f}m")
        
        return summary
    
    def get_top_penetrations(self, results: List[PenetrationResult],
                           top_n: int = 20) -> List[PenetrationResult]:
        """상위 N개 침투 장애물 반환"""
        penetrations = [r for r in results if r.is_penetration]
        
        # 침투량 기준 내림차순 정렬
        sorted_penetrations = sorted(penetrations, 
                                   key=lambda x: x.penetration_m, 
                                   reverse=True)
        
        return sorted_penetrations[:top_n]
    
    def validate_obstacle_data(self, obstacles_gdf: gpd.GeoDataFrame) -> Tuple[bool, List[str]]:
        """
        장애물 데이터 유효성 검증
        
        Args:
            obstacles_gdf: 장애물 GeoDataFrame
            
        Returns:
            tuple: (전체 유효성, 에러 목록)
        """
        errors = []
        
        # 필수 컬럼 확인
        required_cols = ['obj_id', 'top_elev_m']
        missing_cols = [col for col in required_cols if col not in obstacles_gdf.columns]
        if missing_cols:
            errors.append(f"필수 컬럼 누락: {missing_cols}")
        
        # 표고 데이터 검증
        if 'top_elev_m' in obstacles_gdf.columns:
            null_elevs = obstacles_gdf['top_elev_m'].isnull().sum()
            if null_elevs > 0:
                errors.append(f"표고 정보 없는 장애물: {null_elevs}개")
            
            # 비현실적 표고값 확인 (음수 또는 극값)
            if len(obstacles_gdf) > 0:
                elev_series = obstacles_gdf['top_elev_m'].dropna()
                if len(elev_series) > 0:
                    min_elev = elev_series.min()
                    max_elev = elev_series.max()
                    
                    if min_elev < -1000:  # 너무 낮은 값
                        errors.append(f"비현실적으로 낮은 표고: {min_elev:.1f}m")
                    if max_elev > 10000:  # 너무 높은 값  
                        errors.append(f"비현실적으로 높은 표고: {max_elev:.1f}m")
        
        # 지오메트리 검증
        invalid_geoms = ~obstacles_gdf.geometry.is_valid
        invalid_count = invalid_geoms.sum()
        if invalid_count > 0:
            errors.append(f"무효한 지오메트리: {invalid_count}개")
        
        null_geoms = obstacles_gdf.geometry.isnull().sum()
        if null_geoms > 0:
            errors.append(f"빈 지오메트리: {null_geoms}개")
        
        # 좌표계 확인
        coord_valid, coord_errors = self.coord_transform.validate_coordinates(obstacles_gdf)
        if not coord_valid:
            errors.extend(coord_errors)
        
        is_valid = len(errors) == 0
        
        if is_valid:
            logger.info("장애물 데이터 유효성 검증 통과")
        else:
            logger.warning(f"장애물 데이터 유효성 검증 실패: {'; '.join(errors)}")
        
        return is_valid, errors