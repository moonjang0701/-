"""
OLS 기하학 모델링 모듈

ICAO Annex 14 기준의 장애물제한표면을 수학적 함수로 모델링하여
각 위치(x, y)에서의 허용 고도 z_allow를 결정론적으로 계산합니다.
"""

import numpy as np
import pandas as pd
from typing import Tuple, Optional, Dict, List, Union
from dataclasses import dataclass
from abc import ABC, abstractmethod
from loguru import logger
import math


@dataclass
class OLSParameters:
    """OLS 표면 파라미터"""
    # 접근표면 (Approach Surface)
    approach_slope: float = 0.025          # 접근 기울기 (1:40 = 0.025)
    approach_inner_width_m: float = 300    # 내부 폭
    approach_divergence: float = 0.10      # 확산률 (10%)
    approach_length_m: float = 15000       # 접근표면 길이
    
    # 이륙표면 (Takeoff Surface)  
    takeoff_slope: float = 0.02            # 이륙 기울기 (1:50 = 0.02)
    takeoff_inner_width_m: float = 180     # 내부 폭
    takeoff_divergence: float = 0.10       # 확산률 (10%)
    takeoff_length_m: float = 15000        # 이륙표면 길이
    
    # 전이표면 (Transitional Surface)
    transitional_slope: float = 0.143      # 전이 기울기 (1:7 ≈ 0.143)
    transitional_height_cap_m: float = 45  # 전이표면 높이 제한
    
    # 내수평표면 (Inner Horizontal Surface)
    inner_horizontal_radius_m: float = 4000  # 내수평표면 반지름
    inner_horizontal_height_m: float = 45    # 내수평표면 높이
    
    # 원추표면 (Conical Surface)
    conical_slope: float = 0.05            # 원추 기울기 (1:20 = 0.05)
    conical_height_m: float = 100          # 원추표면 높이


class OLSSurface(ABC):
    """OLS 표면 추상 클래스"""
    
    def __init__(self, name: str, params: OLSParameters):
        self.name = name
        self.params = params
    
    @abstractmethod
    def get_allowable_elevation(self, x: float, y: float, 
                              thr_elev_m: float) -> Optional[float]:
        """
        지정된 위치에서의 허용 고도 계산
        
        Args:
            x: 활주로 프레임 X 좌표 (THR 기준)
            y: 활주로 프레임 Y 좌표 (THR 기준)
            thr_elev_m: THR 표고 (AMSL)
            
        Returns:
            허용 고도 (AMSL) 또는 None (표면 범위 밖)
        """
        pass
    
    @abstractmethod 
    def is_within_surface(self, x: float, y: float) -> bool:
        """지정된 위치가 표면 범위 내에 있는지 확인"""
        pass


class ApproachSurface(OLSSurface):
    """접근표면 (Approach Surface)"""
    
    def __init__(self, params: OLSParameters, direction: str = "approach"):
        super().__init__(f"{direction}_surface", params)
        self.direction = direction
    
    def is_within_surface(self, x: float, y: float) -> bool:
        """접근표면 범위 내 확인"""
        # 접근표면은 x >= 0 (THR에서 접근 방향)
        if x < 0:
            return False
            
        # 접근표면 길이 제한
        if x > self.params.approach_length_m:
            return False
        
        # 표면 폭 계산 (확산 고려)
        width_at_x = (self.params.approach_inner_width_m + 
                      2 * self.params.approach_divergence * x)
        half_width = width_at_x / 2
        
        # Y 좌표가 표면 폭 내에 있는지 확인
        return abs(y) <= half_width
    
    def get_allowable_elevation(self, x: float, y: float, 
                              thr_elev_m: float) -> Optional[float]:
        """접근표면 허용고도 계산"""
        if not self.is_within_surface(x, y):
            return None
        
        # 접근표면 고도 = THR 고도 + 기울기 × 거리
        z_allow = thr_elev_m + self.params.approach_slope * x
        
        logger.debug(f"접근표면 고도: ({x:.1f}, {y:.1f}) -> {z_allow:.2f}m")
        return z_allow


class TakeoffSurface(OLSSurface):
    """이륙표면 (Takeoff Surface)"""
    
    def __init__(self, params: OLSParameters):
        super().__init__("takeoff_surface", params)
    
    def is_within_surface(self, x: float, y: float) -> bool:
        """이륙표면 범위 내 확인"""
        # 이륙표면은 x >= 0 (THR에서 이륙 방향)  
        if x < 0:
            return False
            
        # 이륙표면 길이 제한
        if x > self.params.takeoff_length_m:
            return False
        
        # 표면 폭 계산 (확산 고려)
        width_at_x = (self.params.takeoff_inner_width_m + 
                      2 * self.params.takeoff_divergence * x)
        half_width = width_at_x / 2
        
        return abs(y) <= half_width
    
    def get_allowable_elevation(self, x: float, y: float,
                              thr_elev_m: float) -> Optional[float]:
        """이륙표면 허용고도 계산"""
        if not self.is_within_surface(x, y):
            return None
        
        # 이륙표면 고도 = THR 고도 + 기울기 × 거리
        z_allow = thr_elev_m + self.params.takeoff_slope * x
        
        logger.debug(f"이륙표면 고도: ({x:.1f}, {y:.1f}) -> {z_allow:.2f}m")
        return z_allow


class TransitionalSurface(OLSSurface):
    """전이표면 (Transitional Surface)"""
    
    def __init__(self, params: OLSParameters, runway_width_m: float = 45):
        super().__init__("transitional_surface", params)
        self.runway_width_m = runway_width_m
        
    def is_within_surface(self, x: float, y: float) -> bool:
        """전이표면 범위 내 확인"""
        # 전이표면은 활주로 양측에서 시작
        half_runway_width = self.runway_width_m / 2
        
        # 활주로 중심선으로부터의 거리
        distance_from_centerline = abs(y)
        
        # 활주로 폭 밖에서만 전이표면 적용
        return distance_from_centerline > half_runway_width
    
    def get_allowable_elevation(self, x: float, y: float,
                              thr_elev_m: float) -> Optional[float]:
        """전이표면 허용고도 계산"""
        if not self.is_within_surface(x, y):
            return None
        
        half_runway_width = self.runway_width_m / 2
        distance_from_centerline = abs(y)
        
        # 활주로 가장자리로부터의 수평 거리
        horizontal_distance = distance_from_centerline - half_runway_width
        
        # 전이표면 고도 = 활주로 표고 + 기울기 × 수평거리
        z_allow = thr_elev_m + self.params.transitional_slope * horizontal_distance
        
        # 높이 제한 적용
        max_elevation = thr_elev_m + self.params.transitional_height_cap_m
        z_allow = min(z_allow, max_elevation)
        
        logger.debug(f"전이표면 고도: ({x:.1f}, {y:.1f}) -> {z_allow:.2f}m "
                    f"(거리: {horizontal_distance:.1f}m)")
        return z_allow


class InnerHorizontalSurface(OLSSurface):
    """내수평표면 (Inner Horizontal Surface)"""
    
    def __init__(self, params: OLSParameters, arp_elev_m: float):
        super().__init__("inner_horizontal_surface", params) 
        self.arp_elev_m = arp_elev_m  # 공항기준점 표고
    
    def is_within_surface(self, x: float, y: float) -> bool:
        """내수평표면 범위 내 확인"""
        # THR 중심으로부터의 거리
        distance_from_thr = math.sqrt(x**2 + y**2)
        return distance_from_thr <= self.params.inner_horizontal_radius_m
    
    def get_allowable_elevation(self, x: float, y: float,
                              thr_elev_m: float) -> Optional[float]:
        """내수평표면 허용고도 계산"""
        if not self.is_within_surface(x, y):
            return None
        
        # 내수평표면은 ARP 기준 일정 높이
        z_allow = self.arp_elev_m + self.params.inner_horizontal_height_m
        
        logger.debug(f"내수평표면 고도: ({x:.1f}, {y:.1f}) -> {z_allow:.2f}m")
        return z_allow


class ConicalSurface(OLSSurface):
    """원추표면 (Conical Surface)"""
    
    def __init__(self, params: OLSParameters, arp_elev_m: float):
        super().__init__("conical_surface", params)
        self.arp_elev_m = arp_elev_m
        self.inner_horizontal_radius = params.inner_horizontal_radius_m
    
    def is_within_surface(self, x: float, y: float) -> bool:
        """원추표면 범위 내 확인"""
        distance_from_thr = math.sqrt(x**2 + y**2)
        
        # 내수평표면 반지름 밖에서 시작
        if distance_from_thr <= self.inner_horizontal_radius:
            return False
        
        # 원추표면 최대 범위 (내수평 + 원추높이/기울기)
        max_radius = (self.inner_horizontal_radius + 
                     self.params.conical_height_m / self.params.conical_slope)
        
        return distance_from_thr <= max_radius
    
    def get_allowable_elevation(self, x: float, y: float,
                              thr_elev_m: float) -> Optional[float]:
        """원추표면 허용고도 계산"""
        if not self.is_within_surface(x, y):
            return None
        
        distance_from_thr = math.sqrt(x**2 + y**2)
        
        # 내수평표면 가장자리로부터의 거리
        radial_distance = distance_from_thr - self.inner_horizontal_radius
        
        # 내수평표면 높이
        inner_horizontal_elev = (self.arp_elev_m + 
                               self.params.inner_horizontal_height_m)
        
        # 원추표면 고도 = 내수평표면 고도 + 기울기 × 반지름거리
        z_allow = inner_horizontal_elev + self.params.conical_slope * radial_distance
        
        # 원추표면 최대 높이 제한
        max_elevation = inner_horizontal_elev + self.params.conical_height_m
        z_allow = min(z_allow, max_elevation)
        
        logger.debug(f"원추표면 고도: ({x:.1f}, {y:.1f}) -> {z_allow:.2f}m "
                    f"(반지름거리: {radial_distance:.1f}m)")
        return z_allow


class OLSGeometry:
    """OLS 통합 기하학 모델"""
    
    def __init__(self, runway_config: dict, arp_elev_m: float):
        """
        Args:
            runway_config: 활주로 설정 (annex14 파라미터 포함)
            arp_elev_m: 공항기준점 표고
        """
        self.runway_config = runway_config
        self.arp_elev_m = arp_elev_m
        
        # OLS 파라미터 로드
        annex14_config = runway_config.get('annex14', {})
        self.params = self._load_ols_parameters(annex14_config)
        
        # 각 표면 인스턴스 생성
        self.surfaces = self._create_surfaces()
        
        logger.info(f"OLS 기하학 모델 초기화: {len(self.surfaces)}개 표면")
    
    def _load_ols_parameters(self, annex14_config: dict) -> OLSParameters:
        """Annex 14 설정에서 OLS 파라미터 로드"""
        params = OLSParameters()
        
        # 접근표면 파라미터
        if 'approach' in annex14_config:
            approach = annex14_config['approach']
            params.approach_slope = approach.get('slope', params.approach_slope)
            params.approach_inner_width_m = approach.get('inner_width_m', 
                                                       params.approach_inner_width_m)
            params.approach_divergence = approach.get('divergence', 
                                                    params.approach_divergence)
            params.approach_length_m = approach.get('length_m', 
                                                  params.approach_length_m)
        
        # 이륙표면 파라미터  
        if 'takeoff' in annex14_config:
            takeoff = annex14_config['takeoff']
            params.takeoff_slope = takeoff.get('slope', params.takeoff_slope)
            params.takeoff_inner_width_m = takeoff.get('inner_width_m',
                                                     params.takeoff_inner_width_m)
            params.takeoff_divergence = takeoff.get('divergence',
                                                  params.takeoff_divergence)
            params.takeoff_length_m = takeoff.get('length_m',
                                                params.takeoff_length_m)
        
        # 전이표면 파라미터
        if 'transitional' in annex14_config:
            transitional = annex14_config['transitional']
            params.transitional_slope = transitional.get('slope', 
                                                       params.transitional_slope)
            params.transitional_height_cap_m = transitional.get('height_cap_m',
                                                              params.transitional_height_cap_m)
        
        # 내수평표면 파라미터
        if 'inner_horizontal' in annex14_config:
            inner_h = annex14_config['inner_horizontal']
            params.inner_horizontal_radius_m = inner_h.get('radius_m',
                                                         params.inner_horizontal_radius_m)
            params.inner_horizontal_height_m = inner_h.get('height_m',
                                                         params.inner_horizontal_height_m)
        
        # 원추표면 파라미터
        if 'conical' in annex14_config:
            conical = annex14_config['conical']
            params.conical_slope = conical.get('slope', params.conical_slope)
            params.conical_height_m = conical.get('height_m', params.conical_height_m)
        
        return params
    
    def _create_surfaces(self) -> List[OLSSurface]:
        """OLS 표면 인스턴스들 생성"""
        surfaces = []
        
        # 접근표면
        surfaces.append(ApproachSurface(self.params, "approach"))
        
        # 이륙표면
        surfaces.append(TakeoffSurface(self.params))
        
        # 전이표면 (양쪽)
        surfaces.append(TransitionalSurface(self.params))
        
        # 내수평표면
        surfaces.append(InnerHorizontalSurface(self.params, self.arp_elev_m))
        
        # 원추표면
        surfaces.append(ConicalSurface(self.params, self.arp_elev_m))
        
        return surfaces
    
    def get_minimum_allowable_elevation(self, x: float, y: float,
                                      thr_elev_m: float) -> Tuple[Optional[float], str]:
        """
        모든 표면을 고려한 최소 허용고도 계산
        
        Args:
            x: 활주로 프레임 X 좌표
            y: 활주로 프레임 Y 좌표  
            thr_elev_m: THR 표고
            
        Returns:
            tuple: (최소 허용고도, 해당 표면명)
        """
        min_elevation = None
        controlling_surface = "none"
        
        applicable_elevations = []
        
        for surface in self.surfaces:
            z_allow = surface.get_allowable_elevation(x, y, thr_elev_m)
            if z_allow is not None:
                applicable_elevations.append((z_allow, surface.name))
        
        # 적용 가능한 표면이 있으면 최솟값 선택
        if applicable_elevations:
            min_elevation, controlling_surface = min(applicable_elevations, 
                                                   key=lambda x: x[0])
        
        logger.debug(f"위치 ({x:.1f}, {y:.1f}): 최소허용고도 {min_elevation} "
                    f"(제어표면: {controlling_surface})")
        
        return min_elevation, controlling_surface
    
    def generate_validation_grid(self, x_range: Tuple[float, float],
                               y_range: Tuple[float, float], 
                               spacing_m: float,
                               thr_elev_m: float) -> pd.DataFrame:
        """
        검증용 격자 생성
        
        Args:
            x_range: X 좌표 범위 (min, max)
            y_range: Y 좌표 범위 (min, max)
            spacing_m: 격자 간격 (m)
            thr_elev_m: THR 표고
            
        Returns:
            격자점별 허용고도 DataFrame
        """
        x_min, x_max = x_range
        y_min, y_max = y_range
        
        # 격자점 생성
        x_coords = np.arange(x_min, x_max + spacing_m, spacing_m)
        y_coords = np.arange(y_min, y_max + spacing_m, spacing_m)
        
        grid_points = []
        
        for x in x_coords:
            for y in y_coords:
                z_allow, surface = self.get_minimum_allowable_elevation(x, y, thr_elev_m)
                
                grid_points.append({
                    'x': x,
                    'y': y, 
                    'z_allow_m': z_allow,
                    'controlling_surface': surface
                })
        
        grid_df = pd.DataFrame(grid_points)
        logger.info(f"검증 격자 생성: {len(grid_df)}개 점 "
                   f"(간격 {spacing_m}m)")
        
        return grid_df