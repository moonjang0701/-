"""
OLS 침투 판정 엔진 메인 실행 모듈

명령행 인터페이스를 통해 전체 분석 프로세스를 실행합니다.
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

from .core.engine import OLSEngine
from .utils.logger_config import setup_logger


def create_argument_parser() -> argparse.ArgumentParser:
    """명령행 인수 파서 생성"""
    parser = argparse.ArgumentParser(
        description="OLS 침투 판정 엔진 - ICAO/국내 기준 장애물제한표면 침투 분석",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  %(prog)s --input project.gpkg --config config.json --output outputs/
  %(prog)s -i project.gpkg -c config.json -o outputs/ --log-level DEBUG
  %(prog)s --input project.gpkg --config config.json --output outputs/ --generate-grid
  
입력 파일:
  project.gpkg   - GeoPackage 파일 (obstacles, runway_axes 레이어 포함)
  config.json    - 분석 설정 파일 (활주로 정보 및 OLS 파라미터)
  
출력 결과:
  penetration_results.gpkg    - 침투 분석 결과 (GeoPackage)
  penetration_summary.csv     - 요약 통계 (CSV)
  analysis_summary.json       - 분석 메타데이터 (JSON)
  ols_grid_*.gpkg            - OLS 검증 격자 (선택적)
        """)
    
    # 필수 인수
    parser.add_argument(
        '-i', '--input',
        required=True,
        type=str,
        help='입력 GeoPackage 파일 경로 (obstacles, runway_axes 레이어 포함)'
    )
    
    parser.add_argument(
        '-c', '--config',
        required=True,
        type=str,
        help='설정 JSON 파일 경로 (활주로 정보 및 OLS 파라미터)'
    )
    
    parser.add_argument(
        '-o', '--output',
        required=True,
        type=str,
        help='출력 디렉토리 경로'
    )
    
    # 선택적 인수
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='로그 레벨 (기본값: INFO)'
    )
    
    parser.add_argument(
        '--log-file',
        type=str,
        help='로그 파일 경로 (미지정시 콘솔만 출력)'
    )
    
    parser.add_argument(
        '--generate-grid',
        action='store_true',
        help='OLS 검증 격자 생성 (품질 검수용)'
    )
    
    parser.add_argument(
        '--grid-spacing',
        type=float,
        default=200.0,
        help='검증 격자 간격 (m, 기본값: 200)'
    )
    
    parser.add_argument(
        '--grid-extent',
        type=float,
        default=5000.0,
        help='검증 격자 범위 (m, 기본값: 5000)'
    )
    
    parser.add_argument(
        '--export-geojson',
        action='store_true',
        help='GeoJSON 형식으로 추가 출력'
    )
    
    parser.add_argument(
        '--export-cesium',
        action='store_true',
        help='Cesium 시각화 파일 생성'
    )
    
    parser.add_argument(
        '--create-dashboard',
        action='store_true',
        help='대화형 시각화 대시보드 생성 (지도, 차트, 3D)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='실제 분석 없이 입력 검증만 수행'
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version='%(prog)s 1.0.0'
    )
    
    return parser


def validate_arguments(args) -> bool:
    """명령행 인수 유효성 검증"""
    errors = []
    
    # 입력 파일 존재 확인
    input_path = Path(args.input)
    if not input_path.exists():
        errors.append(f"입력 파일이 존재하지 않습니다: {args.input}")
    elif input_path.suffix.lower() != '.gpkg':
        errors.append(f"입력 파일이 GeoPackage가 아닙니다: {args.input}")
    
    # 설정 파일 존재 확인
    config_path = Path(args.config)
    if not config_path.exists():
        errors.append(f"설정 파일이 존재하지 않습니다: {args.config}")
    elif config_path.suffix.lower() != '.json':
        errors.append(f"설정 파일이 JSON이 아닙니다: {args.config}")
    
    # 출력 디렉토리 생성 가능 확인
    output_path = Path(args.output)
    try:
        output_path.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        errors.append(f"출력 디렉토리 생성 실패: {str(e)}")
    
    # 격자 파라미터 검증
    if args.grid_spacing <= 0:
        errors.append("격자 간격은 양수여야 합니다")
    
    if args.grid_extent <= 0:
        errors.append("격자 범위는 양수여야 합니다")
    
    if errors:
        print("인수 검증 실패:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return False
    
    return True


def setup_enhanced_config(args, base_config: dict) -> dict:
    """명령행 인수를 반영한 설정 강화"""
    enhanced_config = base_config.copy()
    
    # 격자 생성 설정
    if args.generate_grid:
        enhanced_config['generate_validation_grid'] = True
        enhanced_config['validation_grid_spacing_m'] = args.grid_spacing
        enhanced_config['validation_grid_extent_m'] = args.grid_extent
    
    # 출력 형식 설정
    enhanced_config['export_options'] = {
        'geojson': args.export_geojson,
        'cesium': args.export_cesium,
        'qgis_styles': True,  # 기본적으로 생성
        'visualization': args.create_dashboard  # 대시보드 생성 여부
    }
    
    return enhanced_config


def run_dry_run_validation(engine: OLSEngine, input_file: str, 
                         config_file: str) -> bool:
    """Dry run 검증 실행"""
    try:
        print("Dry run 모드: 입력 데이터 검증 중...")
        
        # 설정 로드 및 검증
        config = engine.data_loader.load_config(config_file)
        is_valid, errors = engine.config_validator.validate_config(config)
        
        if not is_valid:
            print("설정 파일 검증 실패:")
            for error in errors:
                print(f"  - {error}")
            return False
        
        # 입력 데이터 로드 및 검증
        input_data = engine.data_loader.load_input_data(input_file)
        
        obstacles_gdf = input_data.get('obstacles')
        if obstacles_gdf is not None:
            is_valid, errors = engine.penetration_engine.validate_obstacle_data(obstacles_gdf)
            if not is_valid:
                print("장애물 데이터 검증 실패:")
                for error in errors:
                    print(f"  - {error}")
                return False
        
        # 좌표계 검증
        coord_valid, coord_errors = engine.coord_transform.validate_coordinates(obstacles_gdf)
        if not coord_valid:
            print("좌표 데이터 검증 실패:")
            for error in coord_errors:
                print(f"  - {error}")
            return False
        
        print("✓ Dry run 검증 성공")
        print(f"  - 활주로: {len(config.get('runways', []))}개")
        print(f"  - 장애물: {len(obstacles_gdf)}개")
        print(f"  - 좌표계: EPSG:{obstacles_gdf.crs.to_epsg()}")
        
        return True
        
    except Exception as e:
        print(f"Dry run 검증 실패: {str(e)}")
        return False


def main():
    """메인 실행 함수"""
    # 명령행 인수 파싱
    parser = create_argument_parser()
    args = parser.parse_args()
    
    # 인수 유효성 검증
    if not validate_arguments(args):
        sys.exit(1)
    
    # 로거 설정
    setup_logger(args.log_level, args.log_file)
    
    try:
        # OLS 엔진 초기화
        engine = OLSEngine(log_level=args.log_level)
        
        # Dry run 모드
        if args.dry_run:
            success = run_dry_run_validation(engine, args.input, args.config)
            sys.exit(0 if success else 1)
        
        # 설정 강화 (명령행 옵션 반영)
        base_config = engine.data_loader.load_config(args.config)
        enhanced_config = setup_enhanced_config(args, base_config)
        
        # 임시로 강화된 설정 저장
        temp_config_file = Path(args.output) / "temp_config.json"
        import json
        with open(temp_config_file, 'w', encoding='utf-8') as f:
            json.dump(enhanced_config, f, indent=2, ensure_ascii=False)
        
        # 분석 실행
        print("OLS 침투 분석 시작...")
        result = engine.run_analysis(
            input_file=args.input,
            config_file=str(temp_config_file),
            output_dir=args.output
        )
        
        # 임시 설정 파일 삭제
        temp_config_file.unlink()
        
        # 결과 처리
        if result['success']:
            print("\\n✓ 분석 완료!")
            print(f"처리 시간: {result['processing_time']}")
            print(f"출력 경로: {args.output}")
            
            summary = result['summary']
            print(f"침투 장애물: {summary['total_penetrations']}/{summary['total_obstacles']}개")
            print(f"최대 침투량: {summary['max_penetration_m']:.2f}m")
            
            sys.exit(0)
        else:
            print(f"\\n✗ 분석 실패: {result['error']}", file=sys.stderr)
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\\n사용자에 의해 중단됨", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"\\n예기치 않은 오류: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()