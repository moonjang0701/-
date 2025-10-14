"""
로거 설정 모듈

일관된 로깅 형식과 레벨을 제공합니다.
"""

import sys
from pathlib import Path
from loguru import logger
from typing import Optional


def setup_logger(level: str = "INFO", log_file: Optional[str] = None, 
                rotation: str = "10 MB", retention: int = 5):
    """
    로거 설정
    
    Args:
        level: 로그 레벨 ("DEBUG", "INFO", "WARNING", "ERROR")
        log_file: 로그 파일 경로 (None이면 콘솔만)
        rotation: 로그 파일 회전 기준
        retention: 보관할 로그 파일 수
    """
    # 기존 핸들러 제거
    logger.remove()
    
    # 콘솔 출력 설정
    logger.add(
        sys.stderr,
        level=level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
               "<level>{level: <8}</level> | "
               "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
               "<level>{message}</level>",
        colorize=True
    )
    
    # 파일 출력 설정 (지정된 경우)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.add(
            log_file,
            level=level,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | "
                   "{name}:{function}:{line} | {message}",
            rotation=rotation,
            retention=retention,
            encoding="utf-8"
        )
        
        logger.info(f"로그 파일 설정: {log_file}")
    
    logger.info(f"로거 초기화 완료 (레벨: {level})")


def get_logger(name: str):
    """
    네임스페이스별 로거 반환
    
    Args:
        name: 로거 이름
        
    Returns:
        로거 인스턴스
    """
    return logger.bind(name=name)