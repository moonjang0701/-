"""
UAV 공역 안전성 측정 시스템 - 메인 실행 파일

사용법:
    python main.py [--config CONFIG_FILE] [--output-dir OUTPUT_DIR]

예제:
    python main.py
    python main.py --config my_config.yaml --output-dir results/
"""

import argparse
import yaml
from pathlib import Path
import logging
from typing import Dict, Any

# 핵심 모듈 import (구현 후 활성화)
# from core import SafetyEnvelope, ConflictProbability, SafetyField, TrajectoryPlanner
# from visualization import plot_safety_envelope, plot_safety_field, plot_trajectory

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('uav_safety_system.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def load_config(config_path: str) -> Dict[str, Any]:
    """
    YAML 설정 파일을 로드합니다.
    
    Args:
        config_path: 설정 파일 경로
        
    Returns:
        설정 딕셔너리
        
    Raises:
        FileNotFoundError: 설정 파일이 존재하지 않는 경우
        yaml.YAMLError: YAML 파싱 오류
    """
    config_file = Path(config_path)
    
    if not config_file.exists():
        raise FileNotFoundError(f"설정 파일을 찾을 수 없습니다: {config_path}")
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        logger.info(f"설정 파일 로드 완료: {config_path}")
        return config
    except yaml.YAMLError as e:
        logger.error(f"YAML 파싱 오류: {e}")
        raise


def setup_output_directory(output_dir: str) -> Path:
    """
    결과 출력 디렉토리를 생성합니다.
    
    Args:
        output_dir: 출력 디렉토리 경로
        
    Returns:
        생성된 디렉토리 Path 객체
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    logger.info(f"출력 디렉토리 설정: {output_path}")
    return output_path


def main():
    """
    메인 실행 함수
    """
    # 명령줄 인자 파싱
    parser = argparse.ArgumentParser(
        description='UAV 공역 안전성 측정 시스템',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예제:
  python main.py
  python main.py --config my_config.yaml
  python main.py --config my_config.yaml --output-dir my_results/
        """
    )
    
    parser.add_argument(
        '--config',
        type=str,
        default='config.yaml',
        help='설정 파일 경로 (기본값: config.yaml)'
    )
    
    parser.add_argument(
        '--output-dir',
        type=str,
        default='results',
        help='결과 출력 디렉토리 (기본값: results)'
    )
    
    args = parser.parse_args()
    
    try:
        # 설정 로드
        logger.info("=" * 60)
        logger.info("UAV 공역 안전성 측정 시스템 시작")
        logger.info("=" * 60)
        
        config = load_config(args.config)
        output_dir = setup_output_directory(args.output_dir)
        
        # 주요 파라미터 출력
        logger.info("\n[UAV 성능 파라미터]")
        for key, value in config['uav_performance'].items():
            logger.info(f"  {key}: {value}")
        
        logger.info("\n[경로 설정]")
        logger.info(f"  시작 위치: {config['trajectory']['start_position']}")
        logger.info(f"  목표 위치: {config['trajectory']['end_position']}")
        logger.info(f"  속도: {config['trajectory']['velocity']}")
        
        # TODO: 핵심 알고리즘 실행
        logger.info("\n[시스템 실행]")
        logger.info("Step 1: 안전 봉투 계산...")
        # safety_envelope = SafetyEnvelope(config['uav_performance'])
        
        logger.info("Step 2: 충돌 확률 분석...")
        # conflict_prob = ConflictProbability(config['uncertainty'])
        
        logger.info("Step 3: 안전장 생성...")
        # safety_field = SafetyField(config['airspace'])
        
        logger.info("Step 4: 경로 계획...")
        # trajectory_planner = TrajectoryPlanner(config['trajectory'])
        
        logger.info("Step 5: 시각화 및 결과 저장...")
        # plot_safety_envelope(safety_envelope, output_dir)
        # plot_safety_field(safety_field, output_dir)
        # plot_trajectory(trajectory_planner, output_dir)
        
        logger.info("\n" + "=" * 60)
        logger.info("시스템 실행 완료!")
        logger.info(f"결과 저장 위치: {output_dir.absolute()}")
        logger.info("=" * 60)
        
    except FileNotFoundError as e:
        logger.error(f"파일 오류: {e}")
        return 1
    except Exception as e:
        logger.error(f"예상치 못한 오류 발생: {e}", exc_info=True)
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
