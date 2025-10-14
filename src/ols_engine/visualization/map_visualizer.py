"""
대화형 지도 시각화 모듈

Folium을 사용하여 OLS 침투 분석 결과를 
대화형 웹 지도로 시각화합니다.
"""

import folium
import pandas as pd
import geopandas as gpd
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from loguru import logger
import json
import math
from shapely.geometry import Point, Polygon, LineString
from folium.plugins import HeatMap, MarkerCluster
import branca.colormap as cm


class MapVisualizer:
    """대화형 지도 시각화 클래스"""
    
    def __init__(self):
        # 침투량별 색상 매핑
        self.penetration_colors = {
            'none': '#28a745',      # 초록 - 침투 없음
            'low': '#ffc107',       # 노랑 - 1-5m
            'medium': '#fd7e14',    # 주황 - 5-15m  
            'high': '#dc3545',      # 빨강 - 15-30m
            'critical': '#6f42c1'   # 보라 - 30m+
        }
        
        # OLS 표면별 색상
        self.surface_colors = {
            'approach_surface': '#007bff',
            'takeoff_surface': '#20c997', 
            'transitional_surface': '#fd7e14',
            'inner_horizontal_surface': '#6c757d',
            'conical_surface': '#e83e8c',
            'outside_ols': '#6c757d'
        }
    
    def create_penetration_map(self, penetration_gdf: gpd.GeoDataFrame, 
                             runway_configs: List[dict],
                             output_file: str,
                             include_grid: bool = False,
                             ols_grid_gdf: Optional[gpd.GeoDataFrame] = None) -> str:
        """
        침투 분석 결과 대화형 지도 생성
        
        Args:
            penetration_gdf: 침투 결과 GeoDataFrame
            runway_configs: 활주로 설정 리스트
            output_file: 출력 HTML 파일 경로
            include_grid: OLS 격자 표시 여부
            ols_grid_gdf: OLS 격자 GeoDataFrame
            
        Returns:
            생성된 HTML 파일 경로
        """
        try:
            # WGS84로 변환
            penetration_wgs84 = penetration_gdf.to_crs('EPSG:4326')
            
            # 지도 중심점 계산
            bounds = penetration_wgs84.total_bounds
            center_lat = (bounds[1] + bounds[3]) / 2
            center_lon = (bounds[0] + bounds[2]) / 2
            
            # 기본 지도 생성
            m = folium.Map(
                location=[center_lat, center_lon],
                zoom_start=12,
                tiles='OpenStreetMap'
            )
            
            # 다양한 타일 레이어 추가
            folium.TileLayer('CartoDB positron', name='CartoDB Positron').add_to(m)
            folium.TileLayer('CartoDB dark_matter', name='CartoDB Dark').add_to(m)
            folium.TileLayer(
                tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
                attr='Esri',
                name='위성영상',
                overlay=False
            ).add_to(m)
            
            # 활주로 표시
            self._add_runways_to_map(m, runway_configs)
            
            # OLS 표면 영역 표시 (선택적)
            if include_grid and ols_grid_gdf is not None:
                self._add_ols_surfaces_to_map(m, ols_grid_gdf, runway_configs)
            
            # 장애물 표시 (침투량별 색상)
            self._add_obstacles_to_map(m, penetration_wgs84)
            
            # 침투 히트맵 (선택적)
            penetrations = penetration_wgs84[penetration_wgs84['penetration_m'] > 0]
            if not penetrations.empty:
                self._add_penetration_heatmap(m, penetrations)
            
            # 범례 추가
            self._add_legend_to_map(m)
            
            # 통계 정보 표시
            self._add_statistics_to_map(m, penetration_gdf)
            
            # 레이어 컨트롤 추가
            folium.LayerControl().add_to(m)
            
            # HTML 파일로 저장
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            m.save(str(output_path))
            
            logger.info(f"대화형 지도 생성 완료: {output_file}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"지도 시각화 생성 실패: {str(e)}")
            raise
    
    def _add_runways_to_map(self, m: folium.Map, runway_configs: List[dict]):
        """활주로 표시"""
        runway_group = folium.FeatureGroup(name='활주로', show=True)
        
        for rwy_config in runway_configs:
            rwy_id = rwy_config['rwy_id']
            thr_x = rwy_config['thr_x']
            thr_y = rwy_config['thr_y']
            bearing_deg = rwy_config['bearing_deg']
            
            # EPSG:5186 -> WGS84 변환을 위한 임시 GeoDataFrame 생성
            thr_point = gpd.GeoDataFrame(
                {'id': [1]}, 
                geometry=[Point(thr_x, thr_y)], 
                crs='EPSG:5186'
            ).to_crs('EPSG:4326')
            
            thr_lat = thr_point.geometry.iloc[0].y
            thr_lon = thr_point.geometry.iloc[0].x
            
            # THR 마커
            folium.Marker(
                location=[thr_lat, thr_lon],
                popup=f"<b>{rwy_id}</b><br>THR 위치<br>방위각: {bearing_deg:.1f}°",
                tooltip=f"활주로 {rwy_id}",
                icon=folium.Icon(color='blue', icon='plane')
            ).add_to(runway_group)
            
            # 활주로 방향 표시 (간단한 선)
            runway_length = 4000  # 4km
            bearing_rad = math.radians(bearing_deg)
            
            # 대략적인 경도/위도 변화량 계산 (간단한 근사)
            lat_offset = (runway_length * math.cos(bearing_rad)) / 111320  # 1도 ≈ 111.32km
            lon_offset = (runway_length * math.sin(bearing_rad)) / (111320 * math.cos(math.radians(thr_lat)))
            
            end_lat = thr_lat + lat_offset
            end_lon = thr_lon + lon_offset
            
            folium.PolyLine(
                locations=[[thr_lat, thr_lon], [end_lat, end_lon]],
                popup=f"활주로 {rwy_id}",
                color='blue',
                weight=5,
                opacity=0.8
            ).add_to(runway_group)
        
        runway_group.add_to(m)
    
    def _add_ols_surfaces_to_map(self, m: folium.Map, ols_grid_gdf: gpd.GeoDataFrame, 
                               runway_configs: List[dict]):
        """OLS 표면 영역 표시"""
        if ols_grid_gdf.empty:
            return
            
        ols_group = folium.FeatureGroup(name='OLS 표면', show=False)
        
        # WGS84로 변환
        grid_wgs84 = ols_grid_gdf.to_crs('EPSG:4326')
        
        # 표면별 그룹화
        for surface in grid_wgs84['controlling_surface'].unique():
            if surface == 'none':
                continue
                
            surface_data = grid_wgs84[grid_wgs84['controlling_surface'] == surface]
            if surface_data.empty:
                continue
            
            # 표면별 색상
            color = self.surface_colors.get(surface, '#6c757d')
            
            # 마커 클러스터로 표시 (성능 고려)
            surface_cluster = MarkerCluster(name=f'{surface} 영역')
            
            for _, point in surface_data.iterrows():
                if pd.notna(point['z_allow_m']):
                    folium.CircleMarker(
                        location=[point.geometry.y, point.geometry.x],
                        radius=2,
                        popup=f"표면: {surface}<br>허용고도: {point['z_allow_m']:.1f}m",
                        color=color,
                        fill=True,
                        opacity=0.3
                    ).add_to(surface_cluster)
            
            surface_cluster.add_to(ols_group)
        
        ols_group.add_to(m)
    
    def _add_obstacles_to_map(self, m: folium.Map, penetration_gdf: gpd.GeoDataFrame):
        """장애물 마커 추가"""
        # 침투 장애물과 비침투 장애물 분리
        penetrations = penetration_gdf[penetration_gdf['penetration_m'] > 0]
        non_penetrations = penetration_gdf[penetration_gdf['penetration_m'] <= 0]
        
        # 침투 장애물 그룹
        pen_group = folium.FeatureGroup(name='침투 장애물', show=True)
        
        for _, obs in penetrations.iterrows():
            color = self._get_penetration_color(obs['penetration_m'])
            
            folium.CircleMarker(
                location=[obs.geometry.y, obs.geometry.x],
                radius=8 + min(obs['penetration_m'] / 5, 15),  # 침투량에 비례한 크기
                popup=self._create_obstacle_popup(obs),
                tooltip=f"{obs['obj_id']} (침투: {obs['penetration_m']:.1f}m)",
                color='red',
                fill=True,
                fillColor=color,
                fillOpacity=0.7,
                weight=2
            ).add_to(pen_group)
        
        pen_group.add_to(m)
        
        # 비침투 장애물 그룹 (작게 표시)
        non_pen_group = folium.FeatureGroup(name='정상 장애물', show=False)
        
        for _, obs in non_penetrations.iterrows():
            folium.CircleMarker(
                location=[obs.geometry.y, obs.geometry.x],
                radius=3,
                popup=self._create_obstacle_popup(obs),
                tooltip=f"{obs['obj_id']} (정상)",
                color='green',
                fill=True,
                fillColor='green',
                fillOpacity=0.5,
                weight=1
            ).add_to(non_pen_group)
        
        non_pen_group.add_to(m)
    
    def _add_penetration_heatmap(self, m: folium.Map, penetrations: gpd.GeoDataFrame):
        """침투 히트맵 추가"""
        if penetrations.empty:
            return
            
        # 히트맵 데이터 준비
        heat_data = []
        for _, obs in penetrations.iterrows():
            heat_data.append([
                obs.geometry.y, 
                obs.geometry.x, 
                float(obs['penetration_m'])
            ])
        
        # 히트맵 레이어
        heat_layer = folium.FeatureGroup(name='침투 히트맵', show=False)
        
        HeatMap(
            heat_data,
            min_opacity=0.2,
            max_zoom=18,
            radius=25,
            blur=20,
            gradient={0.0: 'blue', 0.5: 'yellow', 1.0: 'red'}
        ).add_to(heat_layer)
        
        heat_layer.add_to(m)
    
    def _add_legend_to_map(self, m: folium.Map):
        """범례 추가"""
        legend_html = '''
        <div style="position: fixed; 
                    bottom: 50px; left: 50px; width: 200px; height: 120px; 
                    background-color: white; border:2px solid grey; z-index:9999; 
                    font-size:14px; padding: 10px">
        <h4>침투량 범례</h4>
        <p><i class="fa fa-circle" style="color:#28a745"></i> 침투 없음</p>
        <p><i class="fa fa-circle" style="color:#ffc107"></i> 1-5m</p>
        <p><i class="fa fa-circle" style="color:#fd7e14"></i> 5-15m</p>
        <p><i class="fa fa-circle" style="color:#dc3545"></i> 15-30m</p>
        <p><i class="fa fa-circle" style="color:#6f42c1"></i> 30m+</p>
        </div>
        '''
        m.get_root().html.add_child(folium.Element(legend_html))
    
    def _add_statistics_to_map(self, m: folium.Map, penetration_gdf: gpd.GeoDataFrame):
        """통계 정보 패널 추가"""
        total_obstacles = len(penetration_gdf)
        total_penetrations = len(penetration_gdf[penetration_gdf['penetration_m'] > 0])
        max_penetration = penetration_gdf['penetration_m'].max()
        avg_penetration = penetration_gdf[penetration_gdf['penetration_m'] > 0]['penetration_m'].mean()
        
        stats_html = f'''
        <div style="position: fixed; 
                    top: 10px; right: 10px; width: 250px; height: 150px; 
                    background-color: white; border:2px solid grey; z-index:9999; 
                    font-size:12px; padding: 10px">
        <h4>침투 분석 통계</h4>
        <p><b>전체 장애물:</b> {total_obstacles:,}개</p>
        <p><b>침투 장애물:</b> {total_penetrations}개</p>
        <p><b>침투율:</b> {(total_penetrations/total_obstacles*100):.1f}%</p>
        <p><b>최대 침투량:</b> {max_penetration:.1f}m</p>
        <p><b>평균 침투량:</b> {avg_penetration:.1f}m</p>
        </div>
        '''
        m.get_root().html.add_child(folium.Element(stats_html))
    
    def _get_penetration_color(self, penetration_m: float) -> str:
        """침투량에 따른 색상 반환"""
        if penetration_m <= 0:
            return self.penetration_colors['none']
        elif penetration_m <= 5:
            return self.penetration_colors['low'] 
        elif penetration_m <= 15:
            return self.penetration_colors['medium']
        elif penetration_m <= 30:
            return self.penetration_colors['high']
        else:
            return self.penetration_colors['critical']
    
    def _create_obstacle_popup(self, obs) -> str:
        """장애물 팝업 HTML 생성"""
        status = "🔴 침투" if obs['penetration_m'] > 0 else "🟢 정상"
        
        popup_html = f"""
        <div style="width: 200px;">
        <h4>{obs['obj_id']} {status}</h4>
        <p><b>활주로:</b> {obs['rwy_id']}</p>
        <p><b>장애물 표고:</b> {obs['top_elev_m']:.1f}m</p>
        <p><b>허용 고도:</b> {obs['z_allow_m']:.1f}m</p>
        <p><b>침투량:</b> {obs['penetration_m']:.1f}m</p>
        <p><b>제어 표면:</b> {obs['surface']}</p>
        <p><b>위치:</b> ({obs['x']:.0f}, {obs['y']:.0f})</p>
        </div>
        """
        return popup_html
    
    def create_profile_view(self, penetration_gdf: gpd.GeoDataFrame,
                          runway_config: dict, output_file: str,
                          profile_line: Optional[LineString] = None) -> str:
        """
        활주로 단면도 생성
        
        Args:
            penetration_gdf: 침투 결과 데이터
            runway_config: 활주로 설정
            output_file: 출력 파일 경로
            profile_line: 단면선 (None이면 활주로 중심선 사용)
            
        Returns:
            생성된 HTML 파일 경로
        """
        # 구현 예정: matplotlib 기반 단면도 생성
        pass