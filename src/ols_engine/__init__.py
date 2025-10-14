"""
OLS 침투 판정 엔진

ICAO/국내 기준의 장애물제한표면(OLS) 침투 판정을 위한 
결정론적 기하 연산 엔진
"""

__version__ = "1.0.0"
__author__ = "OLS Team"

from .main import main
from .core import OLSEngine
from .core.geometry import OLSSurface
from .core.coordinate_system import CoordinateTransform

__all__ = [
    "main",
    "OLSEngine", 
    "OLSSurface",
    "CoordinateTransform",
]