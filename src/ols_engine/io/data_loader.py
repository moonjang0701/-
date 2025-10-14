"""
데이터 로더 모듈

GeoPackage 및 JSON 설정 파일을 로드하고 검증합니다.
"""

import json
from pathlib import Path
from typing import Dict, Optional, List
import pandas as pd
import geopandas as gpd
from loguru import logger


class DataLoader:
    """데이터 로딩 클래스"""
    
    def __init__(self):
        self.supported_formats = ['.gpkg', '.json']
    
    def load_config(self, config_file: str) -> Dict:
        """
        JSON 설정 파일 로드
        
        Args:
            config_file: 설정 파일 경로
            
        Returns:
            설정 딕셔너리
            
        Raises:
            FileNotFoundError: 파일이 존재하지 않음
            ValueError: JSON 파싱 실패
        """
        config_path = Path(config_file)
        
        if not config_path.exists():
            raise FileNotFoundError(f"설정 파일을 찾을 수 없습니다: {config_file}")
        
        if config_path.suffix.lower() != '.json':
            raise ValueError(f"JSON 파일이 아닙니다: {config_file}")
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            logger.info(f"설정 파일 로드: {config_file}")
            return config
            
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON 파싱 실패: {str(e)}")
        except Exception as e:
            raise ValueError(f"설정 파일 로드 실패: {str(e)}")
    
    def load_input_data(self, input_file: str) -> Dict:
        """
        입력 데이터 파일 로드 (GeoPackage)
        
        Args:
            input_file: 입력 파일 경로
            
        Returns:
            로드된 데이터 딕셔너리
            
        Raises:
            FileNotFoundError: 파일이 존재하지 않음
            ValueError: 파일 형식 오류 또는 필수 레이어 누락
        """
        input_path = Path(input_file)
        
        if not input_path.exists():
            raise FileNotFoundError(f"입력 파일을 찾을 수 없습니다: {input_file}")
        
        if input_path.suffix.lower() != '.gpkg':
            raise ValueError(f"GeoPackage 파일이 아닙니다: {input_file}")
        
        try:
            # 사용 가능한 레이어 확인
            available_layers = gpd.list_layers(input_file)
            
            # DataFrame 형태로 반환되는 경우 처리
            if hasattr(available_layers, 'itertuples'):
                layer_names = available_layers['name'].tolist()
            else:
                # 튜플 리스트 형태인 경우
                layer_names = [layer[0] for layer in available_layers]
            
            logger.info(f"사용 가능한 레이어: {layer_names}")
            
            data = {}
            
            # 필수 레이어: obstacles
            if 'obstacles' not in layer_names:
                raise ValueError("필수 레이어 'obstacles'가 없습니다")
            
            data['obstacles'] = self._load_obstacles_layer(input_file)
            
            # 선택적 레이어: runway_axes  
            if 'runway_axes' in layer_names:
                data['runway_axes'] = self._load_runway_axes_layer(input_file)
            else:
                logger.warning("runway_axes 레이어가 없습니다. 설정 파일의 좌표 정보를 사용합니다.")
                data['runway_axes'] = None
            
            logger.info(f"입력 데이터 로드 완료: {input_file}")
            return data
            
        except Exception as e:
            raise ValueError(f"입력 데이터 로드 실패: {str(e)}")
    
    def _load_obstacles_layer(self, gpkg_file: str) -> gpd.GeoDataFrame:
        """장애물 레이어 로드 및 검증"""
        try:
            gdf = gpd.read_file(gpkg_file, layer='obstacles')
            
            # 필수 컬럼 확인
            required_cols = ['obj_id', 'top_elev_m']
            missing_cols = [col for col in required_cols if col not in gdf.columns]
            
            if missing_cols:
                raise ValueError(f"obstacles 레이어에 필수 컬럼이 없습니다: {missing_cols}")
            
            # 데이터 타입 확인 및 변환
            if 'obj_id' in gdf.columns:
                gdf['obj_id'] = gdf['obj_id'].astype(str)
            
            if 'top_elev_m' in gdf.columns:
                gdf['top_elev_m'] = pd.to_numeric(gdf['top_elev_m'], errors='coerce')
            
            logger.info(f"장애물 레이어 로드: {len(gdf)}개 장애물")
            return gdf
            
        except Exception as e:
            raise ValueError(f"장애물 레이어 로드 실패: {str(e)}")
    
    def _load_runway_axes_layer(self, gpkg_file: str) -> Optional[gpd.GeoDataFrame]:
        """활주로 중심선 레이어 로드 (선택적)"""
        try:
            gdf = gpd.read_file(gpkg_file, layer='runway_axes')
            
            # 필수 컬럼 확인
            required_cols = ['rwy_id', 'bearing_deg', 'thr_elev_m']
            missing_cols = [col for col in required_cols if col not in gdf.columns]
            
            if missing_cols:
                logger.warning(f"runway_axes 레이어에 권장 컬럼이 없습니다: {missing_cols}")
                # 경고만 하고 계속 진행
            
            logger.info(f"활주로 중심선 레이어 로드: {len(gdf)}개 활주로")
            return gdf
            
        except Exception as e:
            logger.warning(f"활주로 중심선 레이어 로드 실패: {str(e)}")
            return None
    
    def validate_file_format(self, file_path: str, expected_format: str) -> bool:
        """
        파일 형식 검증
        
        Args:
            file_path: 파일 경로
            expected_format: 예상 확장자 ('.gpkg', '.json' 등)
            
        Returns:
            형식 일치 여부
        """
        path = Path(file_path)
        
        if not path.exists():
            logger.error(f"파일이 존재하지 않습니다: {file_path}")
            return False
        
        if path.suffix.lower() != expected_format.lower():
            logger.error(f"파일 형식이 맞지 않습니다. 예상: {expected_format}, "
                        f"실제: {path.suffix}")
            return False
        
        return True
    
    def get_layer_info(self, gpkg_file: str) -> List[Dict]:
        """
        GeoPackage 레이어 정보 조회
        
        Args:
            gpkg_file: GeoPackage 파일 경로
            
        Returns:
            레이어 정보 리스트
        """
        try:
            layers_info = gpd.list_layers(gpkg_file)
            
            detailed_info = []
            for layer_name, geometry_type in layers_info:
                try:
                    gdf = gpd.read_file(gpkg_file, layer=layer_name)
                    
                    info = {
                        'layer_name': layer_name,
                        'geometry_type': geometry_type,
                        'feature_count': len(gdf),
                        'columns': list(gdf.columns),
                        'crs': str(gdf.crs) if gdf.crs else None,
                        'bounds': list(gdf.total_bounds) if len(gdf) > 0 else None
                    }
                    detailed_info.append(info)
                    
                except Exception as e:
                    logger.warning(f"레이어 {layer_name} 정보 조회 실패: {str(e)}")
            
            return detailed_info
            
        except Exception as e:
            logger.error(f"레이어 정보 조회 실패: {str(e)}")
            return []
    
    def preview_data(self, file_path: str, layer_name: Optional[str] = None, 
                    max_rows: int = 5) -> Optional[pd.DataFrame]:
        """
        데이터 미리보기
        
        Args:
            file_path: 파일 경로
            layer_name: 레이어 이름 (GeoPackage인 경우)
            max_rows: 최대 행 수
            
        Returns:
            미리보기 DataFrame
        """
        try:
            path = Path(file_path)
            
            if path.suffix.lower() == '.gpkg':
                if layer_name:
                    gdf = gpd.read_file(file_path, layer=layer_name)
                else:
                    # 첫 번째 레이어 사용
                    layers = gpd.list_layers(file_path)
                    if layers:
                        gdf = gpd.read_file(file_path, layer=layers[0][0])
                    else:
                        return None
                
                # 지오메트리 컬럼을 문자열로 변환 (미리보기용)
                preview_df = gdf.head(max_rows).copy()
                if 'geometry' in preview_df.columns:
                    preview_df['geometry'] = preview_df['geometry'].astype(str)
                
                return preview_df
                
            elif path.suffix.lower() == '.json':
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # JSON을 DataFrame으로 변환 (단순화)
                if isinstance(data, dict):
                    return pd.DataFrame([data]).head(max_rows)
                elif isinstance(data, list):
                    return pd.DataFrame(data).head(max_rows)
                else:
                    return pd.DataFrame({'content': [str(data)]})
            
            return None
            
        except Exception as e:
            logger.error(f"데이터 미리보기 실패: {str(e)}")
            return None