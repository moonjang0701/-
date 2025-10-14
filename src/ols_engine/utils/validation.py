"""
설정 및 데이터 검증 모듈

입력 설정과 데이터의 유효성을 검증합니다.
"""

from typing import Dict, List, Tuple, Any, Optional
from loguru import logger
import jsonschema


class ConfigValidator:
    """설정 파일 검증 클래스"""
    
    def __init__(self):
        self.config_schema = self._create_config_schema()
    
    def _create_config_schema(self) -> Dict:
        """설정 파일 JSON 스키마 생성"""
        return {
            "type": "object",
            "required": ["crs_epsg", "runways"],
            "properties": {
                "crs_epsg": {
                    "type": "integer",
                    "enum": [5186]  # 중부 TM 좌표계 고정
                },
                "geoid": {
                    "type": "string",
                    "default": "KGEOID2020"
                },
                "arp_elev_m": {
                    "type": "number",
                    "minimum": -1000,
                    "maximum": 10000
                },
                "generate_validation_grid": {
                    "type": "boolean",
                    "default": False
                },
                "validation_grid_spacing_m": {
                    "type": "number",
                    "minimum": 50,
                    "maximum": 1000,
                    "default": 200
                },
                "validation_grid_extent_m": {
                    "type": "number", 
                    "minimum": 1000,
                    "maximum": 20000,
                    "default": 5000
                },
                "runways": {
                    "type": "array",
                    "minItems": 1,
                    "items": {
                        "type": "object",
                        "required": [
                            "rwy_id", "thr_x", "thr_y", "thr_elev_m", 
                            "bearing_deg", "annex14"
                        ],
                        "properties": {
                            "rwy_id": {"type": "string"},
                            "thr_x": {"type": "number"},
                            "thr_y": {"type": "number"},
                            "thr_elev_m": {
                                "type": "number",
                                "minimum": -1000,
                                "maximum": 10000
                            },
                            "bearing_deg": {
                                "type": "number",
                                "minimum": 0,
                                "maximum": 360
                            },
                            "annex14": {
                                "type": "object",
                                "required": [
                                    "approach", "takeoff", "transitional",
                                    "inner_horizontal", "conical"
                                ],
                                "properties": {
                                    "approach": {
                                        "type": "object",
                                        "required": [
                                            "slope", "inner_width_m", 
                                            "divergence", "length_m"
                                        ],
                                        "properties": {
                                            "slope": {
                                                "type": "number",
                                                "minimum": 0.001,
                                                "maximum": 0.1
                                            },
                                            "inner_width_m": {
                                                "type": "number",
                                                "minimum": 50,
                                                "maximum": 1000
                                            },
                                            "divergence": {
                                                "type": "number",
                                                "minimum": 0.05,
                                                "maximum": 0.3
                                            },
                                            "length_m": {
                                                "type": "number",
                                                "minimum": 1000,
                                                "maximum": 50000
                                            }
                                        }
                                    },
                                    "takeoff": {
                                        "type": "object",
                                        "required": [
                                            "slope", "inner_width_m",
                                            "divergence", "length_m"
                                        ],
                                        "properties": {
                                            "slope": {
                                                "type": "number", 
                                                "minimum": 0.001,
                                                "maximum": 0.1
                                            },
                                            "inner_width_m": {
                                                "type": "number",
                                                "minimum": 50,
                                                "maximum": 1000
                                            },
                                            "divergence": {
                                                "type": "number",
                                                "minimum": 0.05,
                                                "maximum": 0.3
                                            },
                                            "length_m": {
                                                "type": "number",
                                                "minimum": 1000,
                                                "maximum": 50000
                                            }
                                        }
                                    },
                                    "transitional": {
                                        "type": "object",
                                        "required": ["slope", "height_cap_m"],
                                        "properties": {
                                            "slope": {
                                                "type": "number",
                                                "minimum": 0.05,
                                                "maximum": 0.5
                                            },
                                            "height_cap_m": {
                                                "type": "number",
                                                "minimum": 10,
                                                "maximum": 200
                                            }
                                        }
                                    },
                                    "inner_horizontal": {
                                        "type": "object",
                                        "required": ["radius_m", "height_m"],
                                        "properties": {
                                            "radius_m": {
                                                "type": "number",
                                                "minimum": 1000,
                                                "maximum": 10000
                                            },
                                            "height_m": {
                                                "type": "number",
                                                "minimum": 10,
                                                "maximum": 200
                                            }
                                        }
                                    },
                                    "conical": {
                                        "type": "object",
                                        "required": ["slope", "height_m"],
                                        "properties": {
                                            "slope": {
                                                "type": "number",
                                                "minimum": 0.01,
                                                "maximum": 0.2
                                            },
                                            "height_m": {
                                                "type": "number",
                                                "minimum": 50,
                                                "maximum": 500
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    
    def validate_config(self, config: Dict) -> Tuple[bool, List[str]]:
        """
        설정 파일 검증
        
        Args:
            config: 설정 딕셔너리
            
        Returns:
            tuple: (검증 통과 여부, 에러 목록)
        """
        errors = []
        
        try:
            # JSON 스키마 검증
            jsonschema.validate(config, self.config_schema)
            
            # 추가 비즈니스 로직 검증
            additional_errors = self._validate_business_rules(config)
            errors.extend(additional_errors)
            
        except jsonschema.ValidationError as e:
            errors.append(f"스키마 검증 실패: {e.message}")
        except Exception as e:
            errors.append(f"설정 검증 중 오류: {str(e)}")
        
        # 경고 사항 확인 (에러는 아니지만 주의)
        warnings = self._check_configuration_warnings(config)
        if warnings:
            for warning in warnings:
                logger.warning(f"설정 경고: {warning}")
        
        is_valid = len(errors) == 0
        
        if is_valid:
            logger.info("설정 파일 검증 통과")
        else:
            logger.error(f"설정 파일 검증 실패: {len(errors)}개 오류")
            for error in errors:
                logger.error(f"  - {error}")
        
        return is_valid, errors
    
    def _validate_business_rules(self, config: Dict) -> List[str]:
        """비즈니스 로직 검증"""
        errors = []
        
        # 활주로 ID 중복 확인
        runway_ids = [rwy['rwy_id'] for rwy in config['runways']]
        if len(runway_ids) != len(set(runway_ids)):
            errors.append("활주로 ID가 중복됩니다")
        
        # 각 활주로별 세부 검증
        for i, runway in enumerate(config['runways']):
            rwy_id = runway.get('rwy_id', f'runway_{i}')
            
            # THR 좌표 검증 (대략적 한국 영역)
            thr_x = runway.get('thr_x', 0)
            thr_y = runway.get('thr_y', 0)
            
            # Extended validation for South Korea including Jeju Island  
            if not (100000 <= thr_x <= 400000):
                errors.append(f"활주로 {rwy_id}: THR X 좌표가 한국 영역을 벗어남 ({thr_x})")
            
            if not (400000 <= thr_y <= 1300000):
                errors.append(f"활주로 {rwy_id}: THR Y 좌표가 한국 영역을 벗어남 ({thr_y})")
            
            # Annex 14 파라미터 일관성 검증
            annex14 = runway.get('annex14', {})
            
            # 접근표면과 이륙표면 기울기 비교
            approach_slope = annex14.get('approach', {}).get('slope', 0)
            takeoff_slope = annex14.get('takeoff', {}).get('slope', 0)
            
            if approach_slope > 0 and takeoff_slope > 0:
                if approach_slope < takeoff_slope:
                    errors.append(f"활주로 {rwy_id}: 접근표면 기울기가 이륙표면보다 작습니다")
            
            # 내수평표면과 원추표면 높이 비교
            inner_h_height = annex14.get('inner_horizontal', {}).get('height_m', 0)
            conical_height = annex14.get('conical', {}).get('height_m', 0)
            
            if inner_h_height > 0 and conical_height > 0:
                if conical_height < inner_h_height:
                    errors.append(f"활주로 {rwy_id}: 원추표면 높이가 내수평표면보다 낮습니다")
        
        return errors
    
    def _check_configuration_warnings(self, config: Dict) -> List[str]:
        """설정 경고 사항 확인"""
        warnings = []
        
        # ARP 표고가 설정되지 않은 경우
        if 'arp_elev_m' not in config:
            warnings.append("ARP 표고가 설정되지 않음. 기본값 0m 사용.")
        
        # 검증 격자 미생성 경고
        if not config.get('generate_validation_grid', False):
            warnings.append("검증 격자 생성이 비활성화됨. 품질 검수가 제한될 수 있음.")
        
        # 각 활주로별 경고
        for runway in config['runways']:
            rwy_id = runway.get('rwy_id', 'unknown')
            annex14 = runway.get('annex14', {})
            
            # 비표준 파라미터 확인
            approach = annex14.get('approach', {})
            if approach.get('slope', 0) > 0.05:  # 1:20보다 급한 기울기
                warnings.append(f"활주로 {rwy_id}: 접근표면 기울기가 일반적 범위를 벗어남")
            
            takeoff = annex14.get('takeoff', {})
            if takeoff.get('slope', 0) > 0.04:  # 1:25보다 급한 기울기
                warnings.append(f"활주로 {rwy_id}: 이륙표면 기울기가 일반적 범위를 벗어남")
        
        return warnings
    
    def get_validation_summary(self, config: Dict) -> Dict:
        """검증 요약 정보 반환"""
        is_valid, errors = self.validate_config(config)
        warnings = self._check_configuration_warnings(config)
        
        return {
            'is_valid': is_valid,
            'errors_count': len(errors),
            'warnings_count': len(warnings),
            'errors': errors,
            'warnings': warnings,
            'runway_count': len(config.get('runways', [])),
            'crs_epsg': config.get('crs_epsg', 'unknown')
        }


class DataQualityChecker:
    """데이터 품질 검사 클래스"""
    
    @staticmethod
    def check_coordinate_precision(gdf, tolerance_m: float = 0.01) -> Dict:
        """좌표 정밀도 검사"""
        # 구현 예정: 좌표값의 정밀도가 충분한지 확인
        pass
    
    @staticmethod  
    def check_elevation_consistency(gdf, elevation_col: str = 'top_elev_m') -> Dict:
        """표고 일관성 검사"""
        # 구현 예정: 표고값의 일관성 및 이상값 검출
        pass
    
    @staticmethod
    def check_geometry_validity(gdf) -> Dict:
        """지오메트리 유효성 검사"""
        # 구현 예정: 지오메트리 토폴로지 오류 검출
        pass