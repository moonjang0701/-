"""
UAV 공역 안전성 측정 시스템 - 핵심 모듈

이 패키지는 UAV 공역 안전성 분석을 위한 핵심 알고리즘을 포함합니다:
- safety_envelope: 안전 봉투 계산
- conflict_probability: 충돌 확률 분석
- safety_field: 안전장 생성
- trajectory_planning: 경로 계획
"""

__version__ = "1.0.0"
__author__ = "UAV Safety Team"

from .safety_envelope import SafetyEnvelope
from .conflict_probability import ConflictProbabilityCalculator
from .safety_field import UAV, AirspaceSafetyField

# 다음 단계에서 구현 예정
# from .trajectory_planning import TrajectoryPlanner

__all__ = [
    "SafetyEnvelope",
    "ConflictProbabilityCalculator",
    "UAV",
    "AirspaceSafetyField",
    # "TrajectoryPlanner",
]
