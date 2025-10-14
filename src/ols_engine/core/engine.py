"""
OLS 침투 판정 엔진 메인 클래스

전체 처리 프로세스를 통합 관리합니다.
"""

import json
import hashlib
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import pandas as pd
import geopandas as gpd
from loguru import logger

from .coordinate_system import CoordinateTransform
from .geometry import OLSGeometry
from .penetration import ObstaclePenetrationEngine, PenetrationResult
from ..io.data_loader import DataLoader
from ..io.data_exporter import DataExporter
from ..utils.logger_config import setup_logger
from ..utils.validation import ConfigValidator
from shapely.geometry import Point


class OLSEngine:
    """OLS 침투 판정 엔진 메인 클래스"""
    
    def __init__(self, log_level: str = "INFO"):
        """
        Args:
            log_level: 로그 레벨 ("DEBUG", "INFO", "WARNING", "ERROR")
        """
        self.log_level = log_level
        self.setup_logging()
        
        # 핵심 컴포넌트 초기화
        self.coord_transform = CoordinateTransform()
        self.penetration_engine = ObstaclePenetrationEngine(self.coord_transform)
        self.data_loader = DataLoader()
        self.data_exporter = DataExporter()
        self.config_validator = ConfigValidator()
        
        # 처리 결과 저장
        self.config = None
        self.input_data = {}
        self.results = []
        self.summary = {}
        self.validation_errors = []
        
        logger.info("OLS 침투 판정 엔진 초기화 완료")
    
    def setup_logging(self):
        """로깅 설정"""
        setup_logger(self.log_level)
        
    def run_analysis(self, input_file: str, config_file: str, 
                    output_dir: str) -> Dict:
        """
        전체 분석 실행
        
        Args:
            input_file: 입력 GeoPackage 파일 경로
            config_file: 설정 JSON 파일 경로  
            output_dir: 출력 디렉토리 경로
            
        Returns:
            분석 결과 요약
        """
        try:
            # 처리 시작 로그
            start_time = datetime.now()
            logger.info("="*60)
            logger.info("OLS 침투 판정 분석 시작")
            logger.info(f"시작 시간: {start_time}")
            logger.info(f"입력 파일: {input_file}")
            logger.info(f"설정 파일: {config_file}")
            logger.info(f"출력 경로: {output_dir}")
            
            # 1단계: 입력 검증 및 로드
            self._load_and_validate_inputs(input_file, config_file)
            
            # 2단계: 침투 분석 실행
            self._run_penetration_analysis()
            
            # 3단계: 결과 출력
            self._export_results(output_dir)
            
            # 4단계: 검증 및 요약 
            self._generate_summary_report()
            
            # 처리 완료
            end_time = datetime.now()
            processing_time = end_time - start_time
            
            logger.info("="*60)
            logger.info("OLS 침투 판정 분석 완료")
            logger.info(f"완료 시간: {end_time}")
            logger.info(f"처리 시간: {processing_time}")
            logger.info("="*60)
            
            return {
                'success': True,
                'processing_time': str(processing_time),
                'summary': self.summary,
                'validation_errors': self.validation_errors
            }
            
        except Exception as e:
            error_msg = f"분석 실행 실패: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'validation_errors': self.validation_errors
            }
    
    def _load_and_validate_inputs(self, input_file: str, config_file: str):
        """입력 데이터 로드 및 검증"""
        logger.info("1단계: 입력 데이터 로드 및 검증")
        
        # 설정 파일 로드
        self.config = self.data_loader.load_config(config_file)
        logger.info(f"설정 로드 완료: {len(self.config.get('runways', []))}개 활주로")
        
        # 설정 검증
        is_valid, errors = self.config_validator.validate_config(self.config)
        if not is_valid:
            self.validation_errors.extend(errors)
            raise ValueError(f"설정 파일 검증 실패: {'; '.join(errors)}")
        
        # 입력 데이터 로드
        self.input_data = self.data_loader.load_input_data(input_file)
        logger.info(f"입력 데이터 로드 완료: "
                   f"활주로 {len(self.input_data.get('runway_axes', []))}개, "
                   f"장애물 {len(self.input_data.get('obstacles', []))}개")
        
        # 데이터 검증
        self._validate_input_data()
        
        # 설정 해시 생성 (재현성 확보)
        config_str = json.dumps(self.config, sort_keys=True)
        self.config_hash = hashlib.sha256(config_str.encode()).hexdigest()[:16]
        logger.info(f"설정 해시: {self.config_hash}")
    
    def _validate_input_data(self):
        """입력 데이터 유효성 검증"""
        # 장애물 데이터 검증
        obstacles_gdf = self.input_data.get('obstacles')
        if obstacles_gdf is not None:
            is_valid, errors = self.penetration_engine.validate_obstacle_data(obstacles_gdf)
            if not is_valid:
                self.validation_errors.extend(errors)
                
        # 활주로 데이터 검증
        runway_axes_gdf = self.input_data.get('runway_axes') 
        if runway_axes_gdf is not None:
            coord_valid, coord_errors = self.coord_transform.validate_coordinates(runway_axes_gdf)
            if not coord_valid:
                self.validation_errors.extend(coord_errors)
        
        if self.validation_errors:
            logger.warning(f"검증 오류 {len(self.validation_errors)}개 발견")
            for error in self.validation_errors:
                logger.warning(f"  - {error}")
    
    def _run_penetration_analysis(self):
        """침투 분석 실행"""
        logger.info("2단계: 침투 분석 실행")
        
        obstacles_gdf = self.input_data['obstacles']
        runway_configs = self.config['runways']
        
        # ARP 표고 (설정에서 가져오거나 기본값 사용)
        arp_elev_m = self.config.get('arp_elev_m', 0.0)
        
        # 침투 분석 실행
        self.results = self.penetration_engine.analyze_penetrations(
            obstacles_gdf, runway_configs, arp_elev_m
        )
        
        logger.info(f"침투 분석 완료: {len(self.results)}개 결과")
        
        # 침투 발견 개수 로그
        penetrations = [r for r in self.results if r.is_penetration]
        logger.info(f"침투 장애물: {len(penetrations)}개")
    
    def _export_results(self, output_dir: str):
        """결과 출력"""
        logger.info("3단계: 결과 출력")
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # 침투 결과 GeoPackage 출력
        penetration_gdf = self.penetration_engine.create_penetration_gdf(self.results)
        gpkg_file = output_path / "penetration_results.gpkg"
        
        # 기존 프로젝트 파일이 있으면 레이어 추가, 없으면 새로 생성
        self.data_exporter.export_penetration_results(penetration_gdf, str(gpkg_file))
        
        # 검증 격자 생성 (선택사항)
        if self.config.get('generate_validation_grid', False):
            self._export_validation_grid(output_path)
        
        # 요약 보고서 출력
        self._export_summary_reports(output_path)
        
        logger.info(f"결과 출력 완료: {output_path}")
    
    def _export_validation_grid(self, output_path: Path):
        """검증 격자 출력"""
        logger.info("검증 격자 생성")
        
        grid_spacing = self.config.get('validation_grid_spacing_m', 200)
        grid_extent = self.config.get('validation_grid_extent_m', 5000)
        
        for rwy_config in self.config['runways']:
            rwy_id = rwy_config['rwy_id']
            thr_elev_m = rwy_config['thr_elev_m']
            arp_elev_m = self.config.get('arp_elev_m', 0.0)
            
            # OLS 기하학 모델 생성
            ols_geometry = OLSGeometry(rwy_config, arp_elev_m)
            
            # 격자 생성
            grid_df = ols_geometry.generate_validation_grid(
                x_range=(-grid_extent, grid_extent),
                y_range=(-grid_extent, grid_extent),
                spacing_m=grid_spacing,
                thr_elev_m=thr_elev_m
            )
            
            # GeoDataFrame 변환
            if not grid_df.empty:
                geometries = [Point(row['x'], row['y']) for _, row in grid_df.iterrows()]
                grid_gdf = gpd.GeoDataFrame(grid_df, geometry=geometries, crs='EPSG:5186')
                
                # 파일 출력
                grid_file = output_path / f"ols_grid_{rwy_id.replace('-', '_')}.gpkg"
                grid_gdf.to_file(grid_file, driver='GPKG', layer='ols_grid')
                
                logger.info(f"검증 격자 출력: {grid_file} ({len(grid_gdf)}개 점)")
    
    def _export_summary_reports(self, output_path: Path):
        """요약 보고서 출력"""
        # 침투 요약 통계
        summary = self.penetration_engine.get_penetration_summary(self.results)
        
        # 상위 침투 장애물
        top_penetrations = self.penetration_engine.get_top_penetrations(self.results)
        
        # CSV 보고서 출력
        self.data_exporter.export_summary_csv(summary, top_penetrations, 
                                            str(output_path / "penetration_summary.csv"))
        
        # JSON 요약 출력  
        summary_with_meta = {
            'metadata': {
                'analysis_time': datetime.now().isoformat(),
                'config_hash': self.config_hash,
                'validation_errors_count': len(self.validation_errors)
            },
            'summary': summary,
            'validation_errors': self.validation_errors
        }
        
        with open(output_path / "analysis_summary.json", 'w', encoding='utf-8') as f:
            json.dump(summary_with_meta, f, indent=2, ensure_ascii=False)
        
        logger.info("요약 보고서 출력 완료")
    
    def _generate_summary_report(self):
        """요약 리포트 생성 및 콘솔 출력"""
        logger.info("4단계: 요약 리포트 생성")
        
        # 요약 통계 계산
        self.summary = self.penetration_engine.get_penetration_summary(self.results)
        
        # 콘솔 요약 출력
        self._print_console_summary()
        
        # 샘플 검증 출력
        self._print_sample_validation()
    
    def _print_console_summary(self):
        """콘솔 요약 출력"""
        print("\\n" + "="*60)
        print("OLS 침투 분석 결과 요약")
        print("="*60)
        
        summary = self.summary
        
        print(f"전체 장애물:     {summary['total_obstacles']:,}개")
        print(f"침투 장애물:     {summary['total_penetrations']:,}개")
        print(f"침투율:          {summary['penetration_rate']:.1%}")
        print(f"최대 침투량:     {summary['max_penetration_m']:.2f}m")
        print(f"평균 침투량:     {summary['avg_penetration_m']:.2f}m")
        
        # 표면별 통계
        if summary['by_surface']:
            print("\\n표면별 침투 현황:")
            for surface, stats in summary['by_surface'].items():
                print(f"  {surface:20s}: {stats['count']:3d}개 "
                     f"(최대 {stats['max_penetration_m']:6.2f}m)")
        
        # 활주로별 통계  
        if summary['by_runway']:
            print("\\n활주로별 침투 현황:")
            for rwy_id, stats in summary['by_runway'].items():
                print(f"  {rwy_id:20s}: {stats['count']:3d}개 "
                     f"(최대 {stats['max_penetration_m']:6.2f}m)")
        
        # 검증 오류
        if self.validation_errors:
            print(f"\\n검증 오류:       {len(self.validation_errors)}개")
        
        print("="*60)
    
    def _print_sample_validation(self):
        """샘플 검증값 출력"""
        if not self.config or not self.config.get('runways'):
            return
            
        print("\\nOLS 허용고도 샘플 검증:")
        print("-" * 60)
        
        # 첫 번째 활주로 사용
        rwy_config = self.config['runways'][0]
        rwy_id = rwy_config['rwy_id']
        thr_elev_m = rwy_config['thr_elev_m']
        arp_elev_m = self.config.get('arp_elev_m', 0.0)
        
        # OLS 기하학 모델 생성
        ols_geometry = OLSGeometry(rwy_config, arp_elev_m)
        
        # 샘플 포인트들 정의
        sample_points = [
            (0, 0, "THR 위치"),
            (1000, 0, "접근 중앙선 1km"),
            (1000, 200, "접근 가장자리"), 
            (0, 100, "전이표면"),
            (2000, 2000, "내수평표면")
        ]
        
        for x, y, description in sample_points:
            z_allow, surface = ols_geometry.get_minimum_allowable_elevation(x, y, thr_elev_m)
            if z_allow is not None:
                print(f"{description:15s}: ({x:4.0f}, {y:4.0f}) -> "
                     f"{z_allow:6.2f}m ({surface})")
            else:
                print(f"{description:15s}: ({x:4.0f}, {y:4.0f}) -> "
                     f"OLS 범위 밖")
    
    def get_processing_statistics(self) -> Dict:
        """처리 통계 반환"""
        return {
            'config_hash': getattr(self, 'config_hash', 'unknown'),
            'input_statistics': {
                'runways': len(self.config.get('runways', [])) if self.config else 0,
                'obstacles': len(self.input_data.get('obstacles', [])),
            },
            'results_count': len(self.results),
            'validation_errors_count': len(self.validation_errors),
            'summary': self.summary
        }