"""
충돌 확률 계산 엔진

논문 Section 2.3-2.4 구현
브라운 운동 기반 위치 불확실성 모델링 및 충돌 확률 계산
"""

import numpy as np
from scipy.stats import norm
from scipy.special import erf
from scipy.integrate import quad
from typing import Tuple, Optional
from .safety_envelope import SafetyEnvelope


class ConflictProbabilityCalculator:
    """
    충돌 확률 계산 엔진
    
    UAV의 위치 불확실성을 브라운 운동으로 모델링하고,
    특정 공간 좌표가 안전 엔벨로프에 침범될 확률을 계산합니다.
    
    Attributes
    ----------
    safety_envelope : SafetyEnvelope
        안전 엔벨로프 객체
    r_A1, r_A2, r_A3 : float
        분산 성장률 (along-track, cross-track-1, cross-track-2) [km·min^(-1/2)]
    r_eq : float
        등가 구 반경 (km)
    """
    
    def __init__(
        self,
        safety_envelope: SafetyEnvelope,
        r_A1: float,
        r_A2: float,
        r_A3: float
    ) -> None:
        """
        충돌 확률 계산기 초기화
        
        Parameters
        ----------
        safety_envelope : SafetyEnvelope
            안전 엔벨로프 객체
        r_A1 : float
            Along-track 분산 성장률 (km·min^(-1/2))
        r_A2 : float
            Cross-track 분산 성장률 1 (km·min^(-1/2))
        r_A3 : float
            Cross-track 분산 성장률 2 (km·min^(-1/2))
            
        Raises
        ------
        ValueError
            분산 성장률이 음수인 경우
        """
        if any(r <= 0 for r in [r_A1, r_A2, r_A3]):
            raise ValueError("모든 분산 성장률은 양수여야 합니다.")
        
        self.safety_envelope = safety_envelope
        self.r_A1 = r_A1
        self.r_A2 = r_A2
        self.r_A3 = r_A3
        
        # 등가 구 반경 미리 계산
        self.r_eq = safety_envelope.compute_equivalent_radius()
        
        # 수치 안정성을 위한 임계값
        self.EPSILON = 1e-10
        self.MAX_EXP_ARG = 700  # exp(700) ≈ 10^304 (안전 범위)
    
    def compute_p_k(self, t: float, r1: float, k_norm: float) -> float:
        """
        Eq. (27) 구현 - Hitting Probability 밀도 함수
        
        브라운 운동이 특정 경계에 도달할 확률 밀도를 계산합니다.
        
        수식:
        p_k(t) = (r₁ / √(2πt³)) × exp[-(r₁ - ||k||·t)² / (2t)]
        
        Parameters
        ----------
        t : float
            시간 (min) - 반드시 양수
        r1 : float
            r 벡터의 첫 번째 성분 (km)
        k_norm : float
            ||k|| - 벡터 k의 노름 (km/min)
        
        Returns
        -------
        float
            확률 밀도 p_k(t)
            
        Notes
        -----
        수치 안정성을 위해 exp 오버플로우를 방지합니다.
        t가 0에 가까우면 0을 반환합니다.
        """
        # Eq. (27) - Hitting Probability density
        
        # 수치 안정성: t가 너무 작으면 0 반환
        if t < self.EPSILON:
            return 0.0
        
        # 계수 부분: r₁ / √(2πt³)
        coefficient = r1 / np.sqrt(2.0 * np.pi * t**3)
        
        # 지수 부분: -(r₁ - ||k||·t)² / (2t)
        numerator = r1 - k_norm * t
        exponent = -(numerator**2) / (2.0 * t)
        
        # exp 오버플로우 방지
        if exponent < -self.MAX_EXP_ARG:
            return 0.0
        if exponent > self.MAX_EXP_ARG:
            return 0.0  # 비정상적인 경우
        
        result = coefficient * np.exp(exponent)
        
        return result
    
    def integrate_p_k(self, T: float, r1: float, k_norm: float) -> float:
        """
        Eq. (28) 구현 - p_k(t)의 시간 적분 (닫힌 형태)
        
        0부터 T까지 p_k(t)를 적분한 값을 계산합니다.
        수치 적분 대신 닫힌 형태의 해를 사용합니다.
        
        수식:
        ∫₀ᵀ p_k(t) dt = 1 - Φ((r₁ - ||k||T)/√T) 
                        + exp(2r₁||k||) × [1 - Φ((r₁ + ||k||T)/√T)]
        
        여기서 Φ는 표준정규분포의 누적분포함수(CDF)
        
        Parameters
        ----------
        T : float
            적분 상한 (min)
        r1 : float
            r 벡터의 첫 번째 성분 (km)
        k_norm : float
            ||k|| - 벡터 k의 노름 (km/min)
        
        Returns
        -------
        float
            적분 값 ∫₀ᵀ p_k(t) dt
        """
        # Eq. (28) - Closed-form integration of p_k(t)
        
        # 수치 안정성
        if T < self.EPSILON:
            return 0.0
        
        sqrt_T = np.sqrt(T)
        
        # 첫 번째 항: 1 - Φ((r₁ - ||k||T)/√T)
        arg1 = (r1 - k_norm * T) / sqrt_T
        term1 = 1.0 - norm.cdf(arg1)
        
        # 두 번째 항: exp(2r₁||k||) × [1 - Φ((r₁ + ||k||T)/√T)]
        exp_arg = 2.0 * r1 * k_norm
        
        # exp 오버플로우 방지
        if exp_arg > self.MAX_EXP_ARG:
            # exp가 너무 크면 근사값 사용 또는 상한 설정
            exp_term = np.exp(self.MAX_EXP_ARG)
        elif exp_arg < -self.MAX_EXP_ARG:
            exp_term = 0.0
        else:
            exp_term = np.exp(exp_arg)
        
        arg2 = (r1 + k_norm * T) / sqrt_T
        term2 = exp_term * (1.0 - norm.cdf(arg2))
        
        result = term1 + term2
        
        return result
    
    def integrate_t_p_k(self, T: float, r1: float, k_norm: float) -> float:
        """
        Eq. (29) 구현 - t·p_k(t)의 시간 적분
        
        대표 시간 T_h 계산에 사용됩니다.
        
        수식:
        ∫₀ᵀ t·p_k(t) dt
        
        이 적분은 닫힌 형태가 복잡하므로 수치 적분을 사용합니다.
        
        Parameters
        ----------
        T : float
            적분 상한 (min)
        r1 : float
            r 벡터의 첫 번째 성분 (km)
        k_norm : float
            ||k|| - 벡터 k의 노름 (km/min)
        
        Returns
        -------
        float
            적분 값 ∫₀ᵀ t·p_k(t) dt
        """
        # Eq. (29) - Integration of t·p_k(t)
        
        if T < self.EPSILON:
            return 0.0
        
        # 피적분 함수: t·p_k(t)
        def integrand(t):
            return t * self.compute_p_k(t, r1, k_norm)
        
        # 수치 적분 (scipy.integrate.quad)
        result, error = quad(integrand, 0, T, limit=100)
        
        return result
    
    def compute_T_h(
        self,
        t0: float,
        delta_t: float,
        r1: float,
        k_norm: float
    ) -> float:
        """
        Eq. (30) 구현 - 대표 시간(Representative Time) 계산
        
        시간 구간 [t0, t0+Δt] 내에서의 대표 시간을 계산합니다.
        이는 확률 분포의 무게 중심과 유사한 개념입니다.
        
        수식:
        T_h = (∫_{t₀}^{t₀+Δt} t·p_k(t) dt - ∫₀^{t₀} t·p_k(t) dt) / 
              (∫_{t₀}^{t₀+Δt} p_k(t) dt - ∫₀^{t₀} p_k(t) dt)
        
        Parameters
        ----------
        t0 : float
            시작 시간 (min)
        delta_t : float
            시간 구간 길이 (min)
        r1 : float
            r 벡터의 첫 번째 성분 (km)
        k_norm : float
            ||k|| - 벡터 k의 노름 (km/min)
        
        Returns
        -------
        float
            대표 시간 T_h (min)
        """
        # Eq. (30) - Representative time calculation
        
        t_end = t0 + delta_t
        
        # 분자: ∫_{t₀}^{t₀+Δt} t·p_k(t) dt - ∫₀^{t₀} t·p_k(t) dt
        #     = ∫₀^{t₀+Δt} t·p_k(t) dt - ∫₀^{t₀} t·p_k(t) dt
        numerator = (self.integrate_t_p_k(t_end, r1, k_norm) - 
                    self.integrate_t_p_k(t0, r1, k_norm))
        
        # 분모: ∫_{t₀}^{t₀+Δt} p_k(t) dt - ∫₀^{t₀} p_k(t) dt
        #     = ∫₀^{t₀+Δt} p_k(t) dt - ∫₀^{t₀} p_k(t) dt
        denominator = (self.integrate_p_k(t_end, r1, k_norm) - 
                      self.integrate_p_k(t0, r1, k_norm))
        
        # 수치 안정성: 분모가 0에 가까우면 구간 중점 반환
        if abs(denominator) < self.EPSILON:
            return t0 + delta_t / 2.0
        
        T_h = numerator / denominator
        
        # T_h가 [t0, t0+delta_t] 범위 내에 있도록 보장
        T_h = np.clip(T_h, t0, t_end)
        
        return T_h
    
    def compute_projection_probability(
        self,
        T_h: float,
        l2: float,
        l3: float,
        r_eq: float
    ) -> float:
        """
        Eq. (34) 구현 - 2D 투영 확률
        
        3D 안전 엔벨로프를 2D 평면에 투영한 확률을 계산합니다.
        Error function을 사용하여 효율적으로 계산합니다.
        
        수식:
        p(T_h) = (1/(2π·T_h)) × (1/4) × 
                 [erf((l₃ + r_eq)/√(2T_h)) - erf((l₃ - r_eq)/√(2T_h))] ×
                 [erf((l₂ + r_eq)/√(2T_h)) - erf((l₂ - r_eq)/√(2T_h))]
        
        Parameters
        ----------
        T_h : float
            대표 시간 (min)
        l2, l3 : float
            투영 좌표 (km)
        r_eq : float
            등가 구 반경 (km)
        
        Returns
        -------
        float
            투영 확률 p(T_h)
        """
        # Eq. (34) - 2D projection probability using error function
        
        # 수치 안정성
        if T_h < self.EPSILON:
            return 0.0
        
        # 정규화 상수: 1/(2π·T_h)
        normalization = 1.0 / (2.0 * np.pi * T_h)
        
        # Error function 인자의 분모: √(2T_h)
        sqrt_2Th = np.sqrt(2.0 * T_h)
        
        # l₃ 방향 기여도
        # erf((l₃ + r_eq)/√(2T_h)) - erf((l₃ - r_eq)/√(2T_h))
        arg_l3_plus = (l3 + r_eq) / sqrt_2Th
        arg_l3_minus = (l3 - r_eq) / sqrt_2Th
        contribution_l3 = erf(arg_l3_plus) - erf(arg_l3_minus)
        
        # l₂ 방향 기여도
        # erf((l₂ + r_eq)/√(2T_h)) - erf((l₂ - r_eq)/√(2T_h))
        arg_l2_plus = (l2 + r_eq) / sqrt_2Th
        arg_l2_minus = (l2 - r_eq) / sqrt_2Th
        contribution_l2 = erf(arg_l2_plus) - erf(arg_l2_minus)
        
        # 최종 확률: (1/4) × contribution_l3 × contribution_l2
        result = normalization * (1.0 / 4.0) * contribution_l3 * contribution_l2
        
        return max(0.0, result)  # 음수 방지
    
    def construct_transformation_matrices(
        self,
        v_A: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Eq. (15-16) 구현 - 좌표 변환 행렬 구성
        
        UAV의 속도 벡터를 기준으로 새로운 좌표계를 정의합니다.
        - Along-track (속도 방향)
        - Cross-track 1, 2 (속도에 수직)
        
        Parameters
        ----------
        v_A : np.ndarray, shape (3,)
            UAV 속도 벡터 [vx, vy, vz] (km/min)
        
        Returns
        -------
        F : np.ndarray, shape (3, 3)
            좌표 변환 행렬 (회전 행렬)
        P : np.ndarray, shape (3, 3)
            분산 행렬 (대각 행렬)
        """
        # Eq. (15-16) - Coordinate transformation matrices
        
        # Dv = -v_A (상대 속도)
        Dv = -v_A
        Dv_norm = np.linalg.norm(Dv)
        
        # 수치 안정성: 속도가 0에 가까우면 단위 행렬 사용
        if Dv_norm < self.EPSILON:
            F = np.eye(3)
        else:
            # Along-track 방향 (정규화된 Dv)
            e1 = Dv / Dv_norm
            
            # Cross-track 방향 1 (e1에 수직)
            # 기준 벡터 선택 (e1과 평행하지 않은 벡터)
            if abs(e1[0]) < 0.9:
                ref = np.array([1.0, 0.0, 0.0])
            else:
                ref = np.array([0.0, 1.0, 0.0])
            
            e2 = ref - np.dot(ref, e1) * e1
            e2 = e2 / np.linalg.norm(e2)
            
            # Cross-track 방향 2 (e1, e2에 수직)
            e3 = np.cross(e1, e2)
            
            # 변환 행렬 F (열이 기저 벡터)
            F = np.column_stack([e1, e2, e3])
        
        # 분산 행렬 P (대각 행렬)
        P = np.diag([self.r_A1**2, self.r_A2**2, self.r_A3**2])
        
        return F, P
    
    def compute_conflict_probability(
        self,
        X: np.ndarray,
        X_A0: np.ndarray,
        v_A: np.ndarray,
        t0: float,
        delta_t: float
    ) -> float:
        """
        Eq. (10)-(35) 전체 파이프라인 - 최종 충돌 확률 계산
        
        주어진 공간 좌표 X가 시간 구간 [t0, t0+Δt] 동안
        UAV의 안전 엔벨로프에 침범될 확률을 계산합니다.
        
        알고리즘:
        1. 초기 상대 위치 계산: ΔX₀ = X - X_A0
        2. 좌표 변환 행렬 F, P 구성
        3. 변환된 좌표계에서 r, k 계산
        4. 대표 시간 T_h 계산
        5. 투영 좌표 l 계산
        6. 투영 확률 p(T_h) 계산
        7. 최종 적분으로 충돌 확률 계산
        
        수식:
        p_A(X) = ∫_{t₀}^{t₀+Δt} p(T_h) · p_k(t) dt
        
        Parameters
        ----------
        X : np.ndarray, shape (3,)
            공간 좌표 [x, y, z] (km)
        X_A0 : np.ndarray, shape (3,)
            UAV 초기 위치 [x₀, y₀, z₀] (km)
        v_A : np.ndarray, shape (3,)
            UAV 속도 벡터 [vx, vy, vz] (km/min)
        t0 : float
            시작 시간 (min)
        delta_t : float
            시간 구간 길이 (min)
        
        Returns
        -------
        float
            충돌 확률 p_A(X) ∈ [0, 1]
        """
        # Eq. (10)-(35) - Complete conflict probability pipeline
        
        # Step 1: 초기 상대 위치 계산
        # ΔX₀ = X - X_A0
        DeltaX0 = X - X_A0
        
        # Step 2: 좌표 변환 행렬 구성
        F, P = self.construct_transformation_matrices(v_A)
        
        # Step 3: 변환된 좌표계에서 r, k 계산
        # Dv = -v_A
        Dv = -v_A
        
        # r = F^T · ΔX₀ (초기 위치를 새 좌표계로 변환)
        r = F.T @ DeltaX0
        
        # k = P^(-1) · F^T · Dv (속도를 새 좌표계로 변환 후 스케일링)
        P_inv = np.linalg.inv(P)
        k = P_inv @ (F.T @ Dv)
        
        # r, k의 첫 번째 성분과 k의 노름
        r1 = r[0]
        k_norm = np.linalg.norm(k)
        
        # 수치 안정성: k_norm이 0에 가까우면 충돌 확률 0
        if k_norm < self.EPSILON:
            return 0.0
        
        # Step 4: 대표 시간 T_h 계산
        T_h = self.compute_T_h(t0, delta_t, r1, k_norm)
        
        # Step 5: 투영 좌표 l 계산
        # l = r + k · T_h
        l = r + k * T_h
        l2 = l[1]  # Cross-track 1
        l3 = l[2]  # Cross-track 2
        
        # Step 6: 투영 확률 p(T_h) 계산
        p_Th = self.compute_projection_probability(T_h, l2, l3, self.r_eq)
        
        # Step 7: 최종 적분으로 충돌 확률 계산
        # p_A(X) = ∫_{t₀}^{t₀+Δt} p(T_h) · p_k(t) dt
        
        t_end = t0 + delta_t
        
        # 피적분 함수
        def integrand(t):
            return p_Th * self.compute_p_k(t, r1, k_norm)
        
        # 수치 적분
        try:
            result, error = quad(integrand, t0, t_end, limit=100)
        except Exception as e:
            # 적분 실패 시 0 반환
            result = 0.0
        
        # 확률 범위 제한 [0, 1]
        result = np.clip(result, 0.0, 1.0)
        
        return result
    
    def __repr__(self) -> str:
        """문자열 표현"""
        return (
            f"ConflictProbabilityCalculator(\n"
            f"  r_A1={self.r_A1:.3f} km·min^(-1/2),\n"
            f"  r_A2={self.r_A2:.3f} km·min^(-1/2),\n"
            f"  r_A3={self.r_A3:.3f} km·min^(-1/2),\n"
            f"  r_eq={self.r_eq:.3f} km\n"
            f")"
        )
