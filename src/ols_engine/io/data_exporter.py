"""
데이터 출력 모듈

분석 결과를 다양한 형태로 출력합니다.
"""

import json
import csv
from pathlib import Path
from typing import Dict, List, Optional
import pandas as pd
import geopandas as gpd
from datetime import datetime
from loguru import logger

from ..core.penetration import PenetrationResult


class DataExporter:
    """데이터 출력 클래스"""
    
    def __init__(self):
        self.output_formats = ['gpkg', 'csv', 'json', 'geojson']
    
    def export_penetration_results(self, penetration_gdf: gpd.GeoDataFrame,
                                 output_file: str, layer_name: str = 'penetrations'):
        """
        침투 결과를 GeoPackage로 출력
        
        Args:
            penetration_gdf: 침투 결과 GeoDataFrame
            output_file: 출력 파일 경로
            layer_name: 레이어 이름
        """
        try:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # GeoPackage로 저장
            penetration_gdf.to_file(
                output_file, 
                driver='GPKG', 
                layer=layer_name
            )
            
            logger.info(f"침투 결과 출력: {output_file} ({len(penetration_gdf)}개 결과)")
            
        except Exception as e:
            logger.error(f"침투 결과 출력 실패: {str(e)}")
            raise
    
    def export_summary_csv(self, summary: Dict, top_penetrations: List[PenetrationResult],
                          output_file: str):
        """
        요약 통계를 CSV로 출력
        
        Args:
            summary: 요약 통계 딕셔너리
            top_penetrations: 상위 침투 장애물 리스트
            output_file: 출력 파일 경로
        """
        try:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                
                # 헤더 및 전체 요약
                writer.writerow(['OLS 침투 분석 결과 요약'])
                writer.writerow(['분석 시간', datetime.now().strftime('%Y-%m-%d %H:%M:%S')])
                writer.writerow([])
                
                # 전체 통계
                writer.writerow(['전체 통계'])
                writer.writerow(['전체 장애물 수', summary['total_obstacles']])
                writer.writerow(['침투 장애물 수', summary['total_penetrations']])
                writer.writerow(['침투율 (%)', f"{summary['penetration_rate']*100:.1f}"])
                writer.writerow(['최대 침투량 (m)', f"{summary['max_penetration_m']:.2f}"])
                writer.writerow(['평균 침투량 (m)', f"{summary['avg_penetration_m']:.2f}"])
                writer.writerow([])
                
                # 표면별 통계
                if summary['by_surface']:
                    writer.writerow(['표면별 침투 현황'])
                    writer.writerow(['표면', '침투 개수', '최대 침투량(m)', '평균 침투량(m)'])
                    
                    for surface, stats in summary['by_surface'].items():
                        writer.writerow([
                            surface,
                            stats['count'],
                            f"{stats['max_penetration_m']:.2f}",
                            f"{stats['avg_penetration_m']:.2f}"
                        ])
                    writer.writerow([])
                
                # 활주로별 통계
                if summary['by_runway']:
                    writer.writerow(['활주로별 침투 현황'])
                    writer.writerow(['활주로', '침투 개수', '최대 침투량(m)', '평균 침투량(m)'])
                    
                    for rwy_id, stats in summary['by_runway'].items():
                        writer.writerow([
                            rwy_id,
                            stats['count'],
                            f"{stats['max_penetration_m']:.2f}",
                            f"{stats['avg_penetration_m']:.2f}"
                        ])
                    writer.writerow([])
                
                # 상위 침투 장애물
                if top_penetrations:
                    writer.writerow(['상위 침투 장애물 (상위 20개)'])
                    writer.writerow([
                        '순위', '장애물 ID', '활주로', '침투량(m)', 
                        '장애물 표고(m)', '허용고도(m)', '제어 표면'
                    ])
                    
                    for i, result in enumerate(top_penetrations, 1):
                        writer.writerow([
                            i,
                            result.obj_id,
                            result.rwy_id,
                            f"{result.penetration_m:.2f}",
                            f"{result.top_elev_m:.2f}",
                            f"{result.z_allow_m:.2f}" if result.z_allow_m else "N/A",
                            result.controlling_surface
                        ])
            
            logger.info(f"요약 CSV 출력: {output_file}")
            
        except Exception as e:
            logger.error(f"요약 CSV 출력 실패: {str(e)}")
            raise
    
    def export_geojson(self, gdf: gpd.GeoDataFrame, output_file: str, 
                      coordinate_precision: int = 6):
        """
        GeoDataFrame을 GeoJSON으로 출력
        
        Args:
            gdf: 출력할 GeoDataFrame
            output_file: 출력 파일 경로
            coordinate_precision: 좌표 정밀도 (소수점 자릿수)
        """
        try:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # WGS84로 변환 (GeoJSON 표준)
            gdf_wgs84 = gdf.to_crs('EPSG:4326')
            
            # GeoJSON 출력 (좌표 정밀도 설정)
            gdf_wgs84.to_file(output_file, driver='GeoJSON')
            
            logger.info(f"GeoJSON 출력: {output_file} ({len(gdf_wgs84)}개 피처)")
            
        except Exception as e:
            logger.error(f"GeoJSON 출력 실패: {str(e)}")
            raise
    
    def export_qgis_style(self, output_file: str, style_type: str = 'penetration'):
        """
        QGIS 스타일 파일 생성 (QML)
        
        Args:
            output_file: 출력 파일 경로
            style_type: 스타일 타입 ('penetration', 'ols_grid')
        """
        try:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            if style_type == 'penetration':
                qml_content = self._generate_penetration_style()
            elif style_type == 'ols_grid':
                qml_content = self._generate_ols_grid_style()
            else:
                raise ValueError(f"지원하지 않는 스타일 타입: {style_type}")
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(qml_content)
            
            logger.info(f"QGIS 스타일 파일 생성: {output_file}")
            
        except Exception as e:
            logger.error(f"QGIS 스타일 파일 생성 실패: {str(e)}")
            raise
    
    def _generate_penetration_style(self) -> str:
        """침투 결과용 QGIS 스타일 생성"""
        return '''<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
<qgis version="3.22" styleCategories="AllStyleCategories">
  <renderer-v2 type="graduatedSymbol" attr="penetration_m" graduatedMethod="GraduatedColor">
    <ranges>
      <range render="true" symbol="0" lower="0.000000" upper="1.000000" label="0.0 - 1.0m"/>
      <range render="true" symbol="1" lower="1.000000" upper="3.000000" label="1.0 - 3.0m"/>  
      <range render="true" symbol="2" lower="3.000000" upper="5.000000" label="3.0 - 5.0m"/>
      <range render="true" symbol="3" lower="5.000000" upper="10.000000" label="5.0 - 10.0m"/>
      <range render="true" symbol="4" lower="10.000000" upper="999.000000" label="> 10.0m"/>
    </ranges>
    <symbols>
      <symbol type="marker" name="0" alpha="1">
        <layer class="SimpleMarker" enabled="1">
          <prop k="color" v="255,255,0,255"/>
          <prop k="size" v="3"/>
        </layer>
      </symbol>
      <symbol type="marker" name="1" alpha="1">
        <layer class="SimpleMarker" enabled="1">
          <prop k="color" v="255,165,0,255"/>
          <prop k="size" v="4"/>
        </layer>
      </symbol>
      <symbol type="marker" name="2" alpha="1">
        <layer class="SimpleMarker" enabled="1">
          <prop k="color" v="255,69,0,255"/>
          <prop k="size" v="5"/>
        </layer>
      </symbol>
      <symbol type="marker" name="3" alpha="1">
        <layer class="SimpleMarker" enabled="1">
          <prop k="color" v="220,20,60,255"/>
          <prop k="size" v="6"/>
        </layer>
      </symbol>
      <symbol type="marker" name="4" alpha="1">
        <layer class="SimpleMarker" enabled="1">
          <prop k="color" v="139,0,0,255"/>
          <prop k="size" v="8"/>
        </layer>
      </symbol>
    </symbols>
  </renderer-v2>
  <labeling type="simple">
    <settings>
      <text-style fontFamily="Arial" fontSize="8" fieldName="obj_id"/>
      <text-buffer bufferDraw="1" bufferSize="0.5" bufferColor="255,255,255,255"/>
    </settings>
  </labeling>
</qgis>'''
    
    def _generate_ols_grid_style(self) -> str:
        """OLS 격자용 QGIS 스타일 생성"""
        return '''<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
<qgis version="3.22" styleCategories="AllStyleCategories">
  <renderer-v2 type="graduatedSymbol" attr="z_allow_m" graduatedMethod="GraduatedColor">
    <colorramp type="gradient" name="[source]">
      <prop k="color1" v="0,0,255,255"/>
      <prop k="color2" v="255,0,0,255"/>
      <prop k="discrete" v="0"/>
    </colorramp>
    <mode name="Quantile"/>
    <classificationMethod id="Quantile">
      <symmetricMode enabled="0" astride="0" symmetrypoint="0"/>
      <labelFormat format="%1 - %2" precision="1" trimtrailingzeroes="1"/>
    </classificationMethod>
  </renderer-v2>
  <symbols>
    <symbol type="marker" name="default" alpha="0.7">
      <layer class="SimpleMarker" enabled="1">
        <prop k="size" v="1"/>
        <prop k="outline_style" v="no"/>
      </layer>
    </symbol>
  </symbols>
</qgis>'''
    
    def export_detailed_results(self, results: List[PenetrationResult], 
                              output_file: str):
        """
        상세 결과를 CSV로 출력
        
        Args:
            results: 침투 분석 결과 리스트
            output_file: 출력 파일 경로
        """
        try:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # DataFrame 변환
            data = []
            for result in results:
                data.append({
                    'obj_id': result.obj_id,
                    'rwy_id': result.rwy_id,
                    'x_runway_frame': result.x,
                    'y_runway_frame': result.y,
                    'top_elev_m': result.top_elev_m,
                    'z_allow_m': result.z_allow_m,
                    'controlling_surface': result.controlling_surface,
                    'penetration_m': result.penetration_m,
                    'is_penetration': result.is_penetration
                })
            
            df = pd.DataFrame(data)
            
            # CSV 출력
            df.to_csv(output_file, index=False, encoding='utf-8-sig')
            
            logger.info(f"상세 결과 CSV 출력: {output_file} ({len(df)}개 결과)")
            
        except Exception as e:
            logger.error(f"상세 결과 CSV 출력 실패: {str(e)}")
            raise
    
    def export_cesium_visualization(self, penetration_gdf: gpd.GeoDataFrame,
                                  ols_grid_gdf: Optional[gpd.GeoDataFrame],
                                  output_dir: str):
        """
        Cesium 시각화용 파일 생성
        
        Args:
            penetration_gdf: 침투 결과 GeoDataFrame
            ols_grid_gdf: OLS 격자 GeoDataFrame (선택)
            output_dir: 출력 디렉토리
        """
        try:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            # 침투 결과 GeoJSON
            if not penetration_gdf.empty:
                penetration_file = output_path / "penetrations.geojson"
                self.export_geojson(penetration_gdf, str(penetration_file))
            
            # OLS 격자 GeoJSON (선택)
            if ols_grid_gdf is not None and not ols_grid_gdf.empty:
                grid_file = output_path / "ols_grid.geojson"
                self.export_geojson(ols_grid_gdf, str(grid_file))
            
            # Cesium 시각화 HTML 템플릿 생성
            html_file = output_path / "cesium_viewer.html"
            self._generate_cesium_html(html_file)
            
            logger.info(f"Cesium 시각화 파일 생성: {output_dir}")
            
        except Exception as e:
            logger.error(f"Cesium 시각화 파일 생성 실패: {str(e)}")
            raise
    
    def _generate_cesium_html(self, output_file: Path):
        """Cesium 시각화 HTML 생성"""
        html_content = '''<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="utf-8">
    <title>OLS 침투 분석 결과 - Cesium Viewer</title>
    <script src="https://cesium.com/downloads/cesiumjs/releases/1.95/Build/Cesium/Cesium.js"></script>
    <link href="https://cesium.com/downloads/cesiumjs/releases/1.95/Build/Cesium/Widgets/widgets.css" rel="stylesheet">
    <style>
        html, body, #cesiumContainer {
            width: 100%; height: 100%; margin: 0; padding: 0; overflow: hidden;
        }
        #toolbar {
            position: absolute; top: 10px; left: 10px; background: rgba(42, 42, 42, 0.8);
            padding: 10px; border-radius: 5px; color: white;
        }
    </style>
</head>
<body>
    <div id="cesiumContainer"></div>
    <div id="toolbar">
        <button onclick="loadPenetrations()">침투 장애물 로드</button>
        <button onclick="loadOLSGrid()">OLS 격자 로드</button>
        <button onclick="clearAll()">모두 지우기</button>
    </div>
    
    <script>
        // Cesium 뷰어 초기화
        const viewer = new Cesium.Viewer('cesiumContainer', {
            terrainProvider: Cesium.createWorldTerrain()
        });
        
        // 한국 지역으로 카메라 이동
        viewer.camera.setView({
            destination: Cesium.Cartesian3.fromDegrees(127.0, 37.5, 100000)
        });
        
        function loadPenetrations() {
            fetch('penetrations.geojson')
                .then(response => response.json())
                .then(data => {
                    const dataSource = Cesium.GeoJsonDataSource.load(data, {
                        stroke: Cesium.Color.RED,
                        fill: Cesium.Color.RED.withAlpha(0.7),
                        strokeWidth: 3
                    });
                    viewer.dataSources.add(dataSource);
                })
                .catch(error => console.error('침투 데이터 로드 실패:', error));
        }
        
        function loadOLSGrid() {
            fetch('ols_grid.geojson')
                .then(response => response.json())
                .then(data => {
                    const dataSource = Cesium.GeoJsonDataSource.load(data, {
                        stroke: Cesium.Color.BLUE,
                        fill: Cesium.Color.BLUE.withAlpha(0.3),
                        strokeWidth: 1
                    });
                    viewer.dataSources.add(dataSource);
                })
                .catch(error => console.error('OLS 격자 로드 실패:', error));
        }
        
        function clearAll() {
            viewer.dataSources.removeAll();
        }
    </script>
</body>
</html>'''
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
    
    def create_output_directory_structure(self, base_output_dir: str) -> Dict[str, str]:
        """
        출력 디렉토리 구조 생성
        
        Args:
            base_output_dir: 기본 출력 디렉토리
            
        Returns:
            출력 경로 딕셔너리
        """
        base_path = Path(base_output_dir)
        
        paths = {
            'base': str(base_path),
            'geopackage': str(base_path / 'geopackage'),
            'csv': str(base_path / 'csv'),
            'geojson': str(base_path / 'geojson'), 
            'qgis_styles': str(base_path / 'qgis_styles'),
            'cesium': str(base_path / 'cesium'),
            'logs': str(base_path / 'logs')
        }
        
        # 디렉토리 생성
        for path in paths.values():
            Path(path).mkdir(parents=True, exist_ok=True)
        
        logger.info(f"출력 디렉토리 구조 생성: {base_output_dir}")
        return paths