"""
테스트용 샘플 데이터 생성 스크립트

실제 OLS 침투 판정 엔진을 테스트하기 위한 
GeoPackage 형태의 샘플 데이터를 생성합니다.
"""

import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point, LineString
from pathlib import Path
import sys

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))


def create_sample_obstacles(thr_x: float, thr_y: float, num_obstacles: int = 50) -> gpd.GeoDataFrame:
    """
    샘플 장애물 데이터 생성
    
    Args:
        thr_x: THR X 좌표 (EPSG:5186)
        thr_y: THR Y 좌표 (EPSG:5186) 
        num_obstacles: 생성할 장애물 수
        
    Returns:
        장애물 GeoDataFrame
    """
    np.random.seed(42)  # 재현 가능한 결과
    
    obstacles_data = []
    geometries = []
    
    for i in range(num_obstacles):
        # THR 중심으로부터 반경 10km 내 랜덤 위치
        angle = np.random.uniform(0, 2 * np.pi)
        distance = np.random.uniform(100, 10000)
        
        x = thr_x + distance * np.cos(angle)
        y = thr_y + distance * np.sin(angle)
        
        # 장애물 높이: THR 기준으로 -5m ~ +50m 범위
        base_elev = 7.3  # THR 표고
        top_elev = base_elev + np.random.uniform(-5, 50)
        
        # 장애물 타입별 특성
        obstacle_types = ['building', 'tower', 'antenna', 'tree', 'crane']
        obj_type = np.random.choice(obstacle_types)
        
        # 침투 가능성을 높이기 위해 일부 장애물을 접근/이륙 경로에 배치
        if i < 10:  # 처음 10개는 의도적으로 접근 경로에 배치
            bearing_rad = np.radians(340.1)  # 활주로 방위각
            approach_x = thr_x + np.random.uniform(500, 5000) * np.cos(bearing_rad)
            approach_y = thr_y + np.random.uniform(500, 5000) * np.sin(bearing_rad)
            
            # 접근 경로 폭 내로 제한
            lateral_offset = np.random.uniform(-200, 200)
            x = approach_x + lateral_offset * np.cos(bearing_rad + np.pi/2)
            y = approach_y + lateral_offset * np.sin(bearing_rad + np.pi/2)
            
            # 침투하도록 높이 조정
            top_elev = base_elev + np.random.uniform(15, 40)
        
        obstacles_data.append({
            'obj_id': f'OBS_{i+1:03d}',
            'top_elev_m': round(top_elev, 2),
            'name': f'{obj_type.title()} {i+1}',
            'type': obj_type,
            'height_agl': round(np.random.uniform(5, 35), 1)
        })
        
        geometries.append(Point(x, y))
    
    obstacles_gdf = gpd.GeoDataFrame(
        obstacles_data,
        geometry=geometries,
        crs='EPSG:5186'
    )
    
    return obstacles_gdf


def create_sample_runway_axes() -> gpd.GeoDataFrame:
    """샘플 활주로 중심선 데이터 생성"""
    
    # 인천공항 34L/16R 활주로 근사 좌표
    runway_data = [
        {
            'rwy_id': 'RKSI-34L',
            'bearing_deg': 340.1,
            'thr_elev_m': 7.3,
            'tora_m': 4000,
            'toda_m': 4000,
            'lda_m': 4000
        }
    ]
    
    # THR과 DER 좌표로 LineString 생성
    thr_x, thr_y = 198345.12, 531234.88
    bearing_rad = np.radians(340.1)
    runway_length = 4000
    
    der_x = thr_x + runway_length * np.cos(bearing_rad)
    der_y = thr_y + runway_length * np.sin(bearing_rad)
    
    geometry = LineString([(thr_x, thr_y), (der_x, der_y)])
    
    runway_gdf = gpd.GeoDataFrame(
        runway_data,
        geometry=[geometry],
        crs='EPSG:5186'
    )
    
    return runway_gdf


def create_sample_project_gpkg(output_file: str):
    """샘플 프로젝트 GeoPackage 생성"""
    
    # THR 좌표 (인천공항 34L 근사)
    thr_x, thr_y = 198345.12, 531234.88
    
    print(f"샘플 데이터 생성 중: {output_file}")
    
    # 장애물 데이터 생성
    print("  - 장애물 데이터 생성...")
    obstacles_gdf = create_sample_obstacles(thr_x, thr_y, num_obstacles=100)
    
    # 활주로 중심선 데이터 생성
    print("  - 활주로 데이터 생성...")
    runway_gdf = create_sample_runway_axes()
    
    # GeoPackage 저장
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"  - GeoPackage 저장: {output_file}")
    obstacles_gdf.to_file(output_file, layer='obstacles', driver='GPKG')
    runway_gdf.to_file(output_file, layer='runway_axes', driver='GPKG', mode='a')
    
    # 데이터 요약 출력
    print("\\n생성된 데이터 요약:")
    print(f"  - 장애물: {len(obstacles_gdf)}개")
    print(f"  - 활주로: {len(runway_gdf)}개")
    print(f"  - 좌표계: EPSG:5186")
    
    # 장애물 분포 정보
    print(f"\\n장애물 분포:")
    print(f"  - 표고 범위: {obstacles_gdf['top_elev_m'].min():.1f} ~ {obstacles_gdf['top_elev_m'].max():.1f}m")
    print(f"  - 평균 표고: {obstacles_gdf['top_elev_m'].mean():.1f}m")
    
    # 좌표 범위
    bounds = obstacles_gdf.total_bounds
    print(f"\\n좌표 범위:")
    print(f"  - X: {bounds[0]:.1f} ~ {bounds[2]:.1f}")
    print(f"  - Y: {bounds[1]:.1f} ~ {bounds[3]:.1f}")
    
    return output_file


if __name__ == '__main__':
    # 샘플 데이터 생성
    output_file = project_root / "data" / "sample_project.gpkg"
    create_sample_project_gpkg(str(output_file))
    
    print(f"\\n✓ 샘플 데이터 생성 완료: {output_file}")
    print("\\n다음 명령으로 분석을 실행할 수 있습니다:")
    print(f"python -m ols_engine.main \\\\")
    print(f"  --input {output_file} \\\\")
    print(f"  --config {project_root}/data/example_config.json \\\\")
    print(f"  --output {project_root}/outputs/sample_analysis")