"""
UAV 공역 안전성 측정 시스템 - 메인 실행 파일

논문 구현 완료 버전
- 모든 시나리오 지원
- 명령행 인터페이스
- 시각화 및 결과 저장

사용법:
    python main.py --scenario paper_reproduction
    python main.py --scenario custom --num_uavs 20 --gamma 2.0
    python main.py --scenario sensitivity
    python main.py --visualize_only --field_file results/safety_field.npy
"""

import argparse
import yaml
import numpy as np
import sys
from pathlib import Path
from typing import List, Dict, Any, Tuple
import time
import logging
import matplotlib.pyplot as plt

# 로컬 모듈 import
from core.safety_envelope import SafetyEnvelope
from core.conflict_probability import ConflictProbabilityCalculator
from core.safety_field import AirspaceSafetyField, UAV
from visualization.plotting import (
    plot_safety_field_3d,
    plot_safety_field_2d_slice,
    plot_trajectory_comparison,
    plot_temporal_evolution,
    plot_convergence_curve,
    plot_probability_distribution
)

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('uav_safety_system.log')
    ]
)
logger = logging.getLogger(__name__)


def load_config(config_path: str = 'config.yaml') -> dict:
    """
    YAML 설정 파일 로드
    
    Parameters
    ----------
    config_path : str
        설정 파일 경로
        
    Returns
    -------
    dict
        설정 딕셔너리
        
    Raises
    ------
    FileNotFoundError
        설정 파일이 없는 경우
    yaml.YAMLError
        YAML 파싱 오류
    """
    config_file = Path(config_path)
    
    if not config_file.exists():
        logger.error(f"설정 파일을 찾을 수 없습니다: {config_path}")
        raise FileNotFoundError(f"Config file not found: {config_path}")
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        logger.info(f"✓ 설정 파일 로드 완료: {config_path}")
        return config
    except yaml.YAMLError as e:
        logger.error(f"YAML 파싱 오류: {e}")
        raise


def create_uav_from_config(
    uav_id: int, 
    config: dict, 
    position: np.ndarray, 
    velocity: np.ndarray
) -> UAV:
    """
    config에서 UAV 객체 생성
    
    Parameters
    ----------
    uav_id : int
        UAV 식별자
    config : dict
        설정 딕셔너리
    position : np.ndarray
        UAV 위치 [x, y, z] (km)
    velocity : np.ndarray
        UAV 속도 [vx, vy, vz] (km/min)
        
    Returns
    -------
    UAV
        생성된 UAV 객체
    """
    perf = config['uav_performance']
    
    return UAV(
        id=uav_id,
        position=position,
        velocity=velocity,
        Vf=perf['Vf'],
        Vb=perf['Vb'],
        Va=perf['Va'],
        Vd=perf['Vd'],
        Vl=perf['Vl'],
        response_time=perf['response_time']
    )


def generate_random_uavs(
    num_uavs: int, 
    bounds: dict, 
    config: dict,
    seed: int = 42
) -> List[UAV]:
    """
    랜덤 UAV 생성 (테스트용)
    
    Parameters
    ----------
    num_uavs : int
        생성할 UAV 수
    bounds : dict
        공역 경계 {'x': (min, max), 'y': (min, max), 'z': (min, max)}
    config : dict
        설정 파라미터
    seed : int
        랜덤 시드
    
    Returns
    -------
    List[UAV]
        생성된 UAV 리스트
    """
    np.random.seed(seed)
    
    uavs = []
    perf = config['uav_performance']
    
    for i in range(num_uavs):
        # 위치: 공역 내 랜덤
        x = np.random.uniform(bounds['x'][0], bounds['x'][1])
        y = np.random.uniform(bounds['y'][0], bounds['y'][1])
        z = np.random.uniform(bounds['z'][0], bounds['z'][1])
        position = np.array([x, y, z])
        
        # 속도: 랜덤 방향, 크기는 0~Vf/2
        speed = np.random.uniform(0, perf['Vf'] / 2)
        
        # 2D 평면에서 주로 이동 (수평 비행)
        theta = np.random.uniform(0, 2 * np.pi)
        vx = speed * np.cos(theta)
        vy = speed * np.sin(theta)
        
        # 약간의 수직 속도 (상승/하강)
        vz = np.random.uniform(-perf['Va']/2, perf['Va']/2)
        
        velocity = np.array([vx, vy, vz])
        
        uav = UAV(
            id=i+1,
            position=position,
            velocity=velocity,
            Vf=perf['Vf'],
            Vb=perf['Vb'],
            Va=perf['Va'],
            Vd=perf['Vd'],
            Vl=perf['Vl'],
            response_time=perf['response_time']
        )
        
        uavs.append(uav)
        logger.debug(f"  UAV {i+1}: pos={position}, vel={velocity}")
    
    return uavs


def create_safety_field_from_config(config: dict) -> AirspaceSafetyField:
    """
    config에서 AirspaceSafetyField 생성
    
    Parameters
    ----------
    config : dict
        설정 딕셔너리
        
    Returns
    -------
    AirspaceSafetyField
        생성된 안전 필드
    """
    airspace = config['airspace']
    uncertainty = config['uncertainty']
    
    bounds = {
        'x': (airspace['x_min'], airspace['x_max']),
        'y': (airspace['y_min'], airspace['y_max']),
        'z': (airspace['z_min'], airspace['z_max'])
    }
    
    field = AirspaceSafetyField(
        bounds=bounds,
        grid_resolution=airspace['grid_resolution'],
        r_A1=uncertainty['r_A1'],
        r_A2=uncertainty['r_A2'],
        r_A3=uncertainty['r_A3']
    )
    
    return field


def scenario_paper_reproduction(config: dict, output_dir: Path, parallel: bool = False):
    """
    시나리오 1: 논문 재현
    
    - Table 1 파라미터 사용
    - 5대 UAV (다양한 위치와 속도)
    - 안전 필드 계산
    - 2D/3D 시각화
    - 통계 결과 저장
    
    Parameters
    ----------
    config : dict
        설정 딕셔너리
    output_dir : Path
        출력 디렉토리
    parallel : bool
        병렬 처리 여부
    """
    print("\n" + "="*70)
    print("시나리오 1: 논문 재현 (Table 1 Parameters)")
    print("="*70)
    
    start_time = time.time()
    
    # 1. 안전 필드 생성
    logger.info("Step 1: 안전 필드 생성...")
    field = create_safety_field_from_config(config)
    logger.info(f"  공역 범위: X={field.bounds['x']}, Y={field.bounds['y']}, Z={field.bounds['z']}")
    logger.info(f"  그리드 해상도: {field.grid_resolution} km")
    logger.info(f"  그리드 shape: {field.grid_shape}")
    
    # 2. UAV 생성 (5대, 논문 시나리오)
    logger.info("\nStep 2: UAV 생성 (5대)...")
    
    # 중앙 영역에 분산된 UAV들
    uavs_configs = [
        {
            'position': np.array([50.0, 20.0, 10.0]),
            'velocity': np.array([0.0, 10.0, 0.0]),  # 북쪽으로
            'desc': 'UAV 1 (남→북)'
        },
        {
            'position': np.array([30.0, 50.0, 10.0]),
            'velocity': np.array([5.0, 0.0, 0.0]),  # 동쪽으로
            'desc': 'UAV 2 (서→동)'
        },
        {
            'position': np.array([70.0, 50.0, 10.0]),
            'velocity': np.array([-5.0, 0.0, 0.0]),  # 서쪽으로
            'desc': 'UAV 3 (동→서)'
        },
        {
            'position': np.array([50.0, 70.0, 10.0]),
            'velocity': np.array([0.0, -10.0, 0.0]),  # 남쪽으로
            'desc': 'UAV 4 (북→남)'
        },
        {
            'position': np.array([50.0, 50.0, 15.0]),
            'velocity': np.array([3.0, 3.0, 0.0]),  # 북동쪽으로
            'desc': 'UAV 5 (중앙, 고도 높음)'
        }
    ]
    
    uavs = []
    for i, uav_cfg in enumerate(uavs_configs):
        uav = create_uav_from_config(
            uav_id=i+1,
            config=config,
            position=uav_cfg['position'],
            velocity=uav_cfg['velocity']
        )
        uavs.append(uav)
        logger.info(f"  {uav_cfg['desc']}")
        logger.info(f"    위치: {uav_cfg['position']} km")
        logger.info(f"    속도: {uav_cfg['velocity']} km/min")
    
    # 3. 안전 필드 계산
    logger.info("\nStep 3: 안전 필드 계산...")
    logger.info(f"  병렬 처리: {'활성화' if parallel else '비활성화'}")
    
    compute_start = time.time()
    
    safety_values = field.compute_field(
        uavs=uavs,
        t0=0.0,
        delta_t=config['simulation']['time_step'],
        parallel=parallel,
        verbose=True
    )
    
    compute_time = time.time() - compute_start
    logger.info(f"✓ 계산 완료 (소요 시간: {compute_time:.2f}s)")
    
    # 4. 통계 계산
    logger.info("\nStep 4: 통계 분석...")
    stats = field.get_statistics()
    
    logger.info(f"  최대 충돌 확률: {stats['max']:.6e} ({stats['max']*100:.4f}%)")
    logger.info(f"  평균 충돌 확률: {stats['mean']:.6e} ({stats['mean']*100:.4f}%)")
    logger.info(f"  중간값: {stats['median']:.6e}")
    logger.info(f"  표준편차: {stats['std']:.6e}")
    logger.info(f"  위험 셀 (>1%): {stats['dangerous_cells_1pct']} 개")
    logger.info(f"  위험 셀 (>5%): {stats['dangerous_cells_5pct']} 개")
    
    # 5. 시각화
    logger.info("\nStep 5: 시각화 생성...")
    
    # 5.1 3D 시각화
    logger.info("  - 3D 안전 필드...")
    plot_safety_field_3d(
        field,
        uavs=uavs,
        threshold=0.001,
        show_envelopes=False,
        save_path=str(output_dir / 'paper_field_3d.png')
    )
    
    # 5.2 2D 슬라이스 (고도 10km)
    logger.info("  - 2D 슬라이스 (z=10km)...")
    plot_safety_field_2d_slice(
        field,
        altitude=10.0,
        uavs=uavs,
        show_contours=True,
        save_path=str(output_dir / 'paper_field_2d_z10.png')
    )
    
    # 5.3 2D 슬라이스 (고도 15km)
    logger.info("  - 2D 슬라이스 (z=15km)...")
    plot_safety_field_2d_slice(
        field,
        altitude=15.0,
        uavs=uavs,
        show_contours=True,
        save_path=str(output_dir / 'paper_field_2d_z15.png')
    )
    
    # 5.4 확률 분포
    logger.info("  - 확률 분포 히스토그램...")
    probabilities = safety_values[safety_values > 0]
    if len(probabilities) > 0:
        plot_probability_distribution(
            probabilities,
            bins=50,
            save_path=str(output_dir / 'paper_probability_distribution.png')
        )
    
    # 6. 결과 저장
    logger.info("\nStep 6: 결과 저장...")
    
    # 6.1 NumPy 파일
    np.save(output_dir / 'paper_safety_field.npy', safety_values)
    logger.info(f"  - 안전 필드 저장: paper_safety_field.npy")
    
    # 6.2 통계 텍스트 파일
    with open(output_dir / 'paper_results.txt', 'w', encoding='utf-8') as f:
        f.write("="*70 + "\n")
        f.write("UAV 공역 안전성 측정 시스템 - 논문 재현 결과\n")
        f.write("="*70 + "\n\n")
        
        f.write(f"계산 시간: {compute_time:.2f}s\n")
        f.write(f"총 실행 시간: {time.time() - start_time:.2f}s\n\n")
        
        f.write("--- 공역 정보 ---\n")
        f.write(f"X 범위: {field.bounds['x']} km\n")
        f.write(f"Y 범위: {field.bounds['y']} km\n")
        f.write(f"Z 범위: {field.bounds['z']} km\n")
        f.write(f"그리드 해상도: {field.grid_resolution} km\n")
        f.write(f"그리드 shape: {field.grid_shape}\n\n")
        
        f.write("--- UAV 정보 ---\n")
        f.write(f"UAV 수: {len(uavs)}\n")
        for i, uav in enumerate(uavs):
            f.write(f"\nUAV {i+1}:\n")
            f.write(f"  위치: {uav.position} km\n")
            f.write(f"  속도: {uav.velocity} km/min\n")
            f.write(f"  성능: Vf={uav.Vf}, Vb={uav.Vb}, Va={uav.Va}, "
                   f"Vd={uav.Vd}, Vl={uav.Vl} km/min\n")
            f.write(f"  응답 시간: {uav.response_time}s\n")
        
        f.write("\n--- 통계 ---\n")
        f.write(f"최대 충돌 확률: {stats['max']:.6e} ({stats['max']*100:.4f}%)\n")
        f.write(f"평균 충돌 확률: {stats['mean']:.6e} ({stats['mean']*100:.4f}%)\n")
        f.write(f"중간값: {stats['median']:.6e}\n")
        f.write(f"표준편차: {stats['std']:.6e}\n")
        f.write(f"위험 셀 (>1%): {stats['dangerous_cells_1pct']} 개\n")
        f.write(f"위험 셀 (>5%): {stats['dangerous_cells_5pct']} 개\n")
        
        f.write("\n--- 생성된 파일 ---\n")
        f.write("- paper_safety_field.npy (안전 필드 데이터)\n")
        f.write("- paper_field_3d.png (3D 시각화)\n")
        f.write("- paper_field_2d_z10.png (2D 슬라이스, z=10km)\n")
        f.write("- paper_field_2d_z15.png (2D 슬라이스, z=15km)\n")
        f.write("- paper_probability_distribution.png (확률 분포)\n")
        f.write("- paper_results.txt (본 파일)\n")
    
    logger.info(f"  - 결과 요약 저장: paper_results.txt")
    
    total_time = time.time() - start_time
    
    print("\n" + "="*70)
    print(f"✓ 시나리오 1 완료 (총 {total_time:.2f}초)")
    print(f"결과 저장 위치: {output_dir.absolute()}/")
    print("="*70)


def scenario_custom(config: dict, args, output_dir: Path):
    """
    시나리오 2: 커스텀 파라미터
    
    사용자가 명령행에서 지정한 파라미터로 실행
    - UAV 수 지정 가능
    - gamma (안전 가중치) 지정 가능
    - 랜덤 UAV 생성
    
    Parameters
    ----------
    config : dict
        설정 딕셔너리
    args : argparse.Namespace
        명령행 인자
    output_dir : Path
        출력 디렉토리
    """
    print("\n" + "="*70)
    print(f"시나리오 2: 커스텀 시뮬레이션")
    print(f"  - UAV 수: {args.num_uavs}")
    print(f"  - Gamma (안전 가중치): {args.gamma}")
    print("="*70)
    
    start_time = time.time()
    
    # 1. 안전 필드 생성
    logger.info("Step 1: 안전 필드 생성...")
    field = create_safety_field_from_config(config)
    logger.info(f"  그리드 shape: {field.grid_shape}")
    
    # 2. 랜덤 UAV 생성
    logger.info(f"\nStep 2: 랜덤 UAV 생성 ({args.num_uavs}대)...")
    uavs = generate_random_uavs(args.num_uavs, field.bounds, config)
    logger.info(f"✓ {len(uavs)}대 UAV 생성 완료")
    
    # 3. 안전 필드 계산
    logger.info("\nStep 3: 안전 필드 계산...")
    compute_start = time.time()
    
    safety_values = field.compute_field(
        uavs=uavs,
        t0=0.0,
        delta_t=config['simulation']['time_step'],
        parallel=args.parallel,
        verbose=True
    )
    
    compute_time = time.time() - compute_start
    logger.info(f"✓ 계산 완료 (소요 시간: {compute_time:.2f}s)")
    
    # 4. 통계
    logger.info("\nStep 4: 통계 분석...")
    stats = field.get_statistics()
    logger.info(f"  최대 충돌 확률: {stats['max']:.6e} ({stats['max']*100:.4f}%)")
    logger.info(f"  위험 셀 (>1%): {stats['dangerous_cells_1pct']} 개")
    
    # 5. 시각화
    logger.info("\nStep 5: 시각화 생성...")
    
    # 중앙 고도 선택
    z_mid = (field.bounds['z'][0] + field.bounds['z'][1]) / 2
    
    plot_safety_field_3d(
        field,
        uavs=uavs,
        threshold=0.001,
        save_path=str(output_dir / f'custom_{args.num_uavs}uavs_3d.png')
    )
    
    plot_safety_field_2d_slice(
        field,
        altitude=z_mid,
        uavs=uavs,
        show_contours=True,
        save_path=str(output_dir / f'custom_{args.num_uavs}uavs_2d.png')
    )
    
    # 6. 결과 저장
    logger.info("\nStep 6: 결과 저장...")
    
    np.save(output_dir / f'custom_{args.num_uavs}uavs_field.npy', safety_values)
    
    with open(output_dir / f'custom_{args.num_uavs}uavs_results.txt', 'w', encoding='utf-8') as f:
        f.write(f"커스텀 시나리오 결과\n")
        f.write(f"="*50 + "\n\n")
        f.write(f"UAV 수: {args.num_uavs}\n")
        f.write(f"Gamma: {args.gamma}\n")
        f.write(f"계산 시간: {compute_time:.2f}s\n\n")
        f.write(f"최대 충돌 확률: {stats['max']:.6e}\n")
        f.write(f"평균 충돌 확률: {stats['mean']:.6e}\n")
        f.write(f"위험 셀 (>1%): {stats['dangerous_cells_1pct']} 개\n")
    
    total_time = time.time() - start_time
    
    print("\n" + "="*70)
    print(f"✓ 시나리오 2 완료 (총 {total_time:.2f}초)")
    print(f"결과 저장 위치: {output_dir.absolute()}/")
    print("="*70)


def scenario_sensitivity_analysis(config: dict, output_dir: Path):
    """
    시나리오 3: 민감도 분석
    
    Eq. (39) 검증 - 각 파라미터 변화에 따른 r_eq 변화
    논문의 Equation (39): r_eq = sqrt(V* × s* / 2)
    
    다음 파라미터들의 영향을 분석:
    - V* (최대 속도)
    - s* (표준 편차)
    - response_time
    
    Parameters
    ----------
    config : dict
        설정 딕셔너리
    output_dir : Path
        출력 디렉토리
    """
    print("\n" + "="*70)
    print("시나리오 3: 민감도 분석 (Eq. 39 검증)")
    print("="*70)
    
    start_time = time.time()
    
    logger.info("Equation (39) 민감도 분석 수행 중...")
    logger.info("r_eq = sqrt(V* × s* / 2)")
    
    # 기준 파라미터
    base_V = 5.0  # km/min (Vf)
    base_s = 0.2  # km·min^(-1/2) (r_A1)
    base_response_time = 60.0  # seconds
    
    # 변화 범위 (-50% ~ +50%)
    variation_range = np.linspace(0.5, 1.5, 21)
    
    # 1. V* 변화 분석
    logger.info("\n1. 최대 속도 (V*) 변화 분석...")
    
    V_values = base_V * variation_range
    r_eq_V_predicted = []
    r_eq_V_actual = []
    
    for V in V_values:
        # 예측값 (Eq. 39)
        r_predicted = np.sqrt(V * base_s / 2)
        r_eq_V_predicted.append(r_predicted)
        
        # 실제값 (SafetyEnvelope 계산)
        envelope = SafetyEnvelope(
            Vf=V, Vb=base_V/2.5, Va=base_V/5.5, Vd=base_V/3.3, Vl=base_V/1.7,
            response_time=base_response_time,
            sigma_x=base_s, sigma_y=base_s/2, sigma_z=base_s/2
        )
        velocity = np.array([V, 0.0, 0.0])
        a, b, c, d, e = envelope.compute_axes(velocity)
        r_actual = (a + b) / 2  # 평균 반경
        r_eq_V_actual.append(r_actual)
    
    logger.info(f"  변화 범위: {V_values[0]:.2f} ~ {V_values[-1]:.2f} km/min")
    logger.info(f"  r_eq 범위: {min(r_eq_V_predicted):.3f} ~ {max(r_eq_V_predicted):.3f} km")
    
    # 2. s* 변화 분석
    logger.info("\n2. 표준 편차 (s*) 변화 분석...")
    
    s_values = base_s * variation_range
    r_eq_s_predicted = []
    r_eq_s_actual = []
    
    for s in s_values:
        # 예측값
        r_predicted = np.sqrt(base_V * s / 2)
        r_eq_s_predicted.append(r_predicted)
        
        # 실제값
        envelope = SafetyEnvelope(
            Vf=base_V, Vb=base_V/2.5, Va=base_V/5.5, Vd=base_V/3.3, Vl=base_V/1.7,
            response_time=base_response_time,
            sigma_x=s, sigma_y=s/2, sigma_z=s/2
        )
        velocity = np.array([base_V, 0.0, 0.0])
        a, b, c, d, e = envelope.compute_axes(velocity)
        r_actual = (a + b) / 2
        r_eq_s_actual.append(r_actual)
    
    logger.info(f"  변화 범위: {s_values[0]:.3f} ~ {s_values[-1]:.3f} km·min^(-1/2)")
    logger.info(f"  r_eq 범위: {min(r_eq_s_predicted):.3f} ~ {max(r_eq_s_predicted):.3f} km")
    
    # 3. 응답 시간 변화 분석
    logger.info("\n3. 응답 시간 (response_time) 변화 분석...")
    
    rt_values = base_response_time * variation_range
    r_eq_rt = []
    
    for rt in rt_values:
        envelope = SafetyEnvelope(
            Vf=base_V, Vb=base_V/2.5, Va=base_V/5.5, Vd=base_V/3.3, Vl=base_V/1.7,
            response_time=rt,
            sigma_x=base_s, sigma_y=base_s/2, sigma_z=base_s/2
        )
        velocity = np.array([base_V, 0.0, 0.0])
        a, b, c, d, e = envelope.compute_axes(velocity)
        r_actual = (a + b) / 2
        r_eq_rt.append(r_actual)
    
    logger.info(f"  변화 범위: {rt_values[0]:.1f} ~ {rt_values[-1]:.1f} s")
    logger.info(f"  r_eq 범위: {min(r_eq_rt):.3f} ~ {max(r_eq_rt):.3f} km")
    
    # 4. 시각화
    logger.info("\n4. 결과 시각화...")
    
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    
    # 4.1 V* 영향
    ax = axes[0]
    ax.plot(variation_range * 100, r_eq_V_predicted, 'b-', linewidth=2, 
            label='Predicted (Eq. 39)')
    ax.plot(variation_range * 100, r_eq_V_actual, 'ro', markersize=6, 
            label='Actual (SafetyEnvelope)')
    ax.set_xlabel('V* Variation (%)', fontsize=12)
    ax.set_ylabel('r_eq (km)', fontsize=12)
    ax.set_title('(a) Maximum Velocity (V*) Impact', fontsize=13, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=10)
    
    # 4.2 s* 영향
    ax = axes[1]
    ax.plot(variation_range * 100, r_eq_s_predicted, 'b-', linewidth=2, 
            label='Predicted (Eq. 39)')
    ax.plot(variation_range * 100, r_eq_s_actual, 'ro', markersize=6, 
            label='Actual (SafetyEnvelope)')
    ax.set_xlabel('s* Variation (%)', fontsize=12)
    ax.set_ylabel('r_eq (km)', fontsize=12)
    ax.set_title('(b) Standard Deviation (s*) Impact', fontsize=13, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=10)
    
    # 4.3 응답 시간 영향
    ax = axes[2]
    ax.plot(variation_range * 100, r_eq_rt, 'g-', linewidth=2, marker='o', 
            markersize=6, label='Actual (SafetyEnvelope)')
    ax.set_xlabel('Response Time Variation (%)', fontsize=12)
    ax.set_ylabel('r_eq (km)', fontsize=12)
    ax.set_title('(c) Response Time Impact', fontsize=13, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=10)
    
    plt.tight_layout()
    plt.savefig(output_dir / 'sensitivity_analysis.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    logger.info(f"  - 그래프 저장: sensitivity_analysis.png")
    
    # 5. 결과 저장
    logger.info("\n5. 수치 결과 저장...")
    
    with open(output_dir / 'sensitivity_results.txt', 'w', encoding='utf-8') as f:
        f.write("="*70 + "\n")
        f.write("민감도 분석 결과 (Eq. 39 검증)\n")
        f.write("="*70 + "\n\n")
        
        f.write("Equation (39): r_eq = sqrt(V* × s* / 2)\n\n")
        
        f.write("기준 파라미터:\n")
        f.write(f"  V* (최대 속도): {base_V} km/min\n")
        f.write(f"  s* (표준 편차): {base_s} km·min^(-1/2)\n")
        f.write(f"  response_time: {base_response_time} s\n\n")
        
        f.write("--- 1. V* 변화 영향 ---\n")
        for i, var in enumerate([0.5, 0.75, 1.0, 1.25, 1.5]):
            idx = int((var - 0.5) / 1.0 * (len(variation_range) - 1))
            f.write(f"  {var*100:5.0f}%: predicted={r_eq_V_predicted[idx]:.4f} km, "
                   f"actual={r_eq_V_actual[idx]:.4f} km, "
                   f"error={(abs(r_eq_V_predicted[idx]-r_eq_V_actual[idx])/r_eq_V_predicted[idx]*100):.2f}%\n")
        
        f.write("\n--- 2. s* 변화 영향 ---\n")
        for i, var in enumerate([0.5, 0.75, 1.0, 1.25, 1.5]):
            idx = int((var - 0.5) / 1.0 * (len(variation_range) - 1))
            f.write(f"  {var*100:5.0f}%: predicted={r_eq_s_predicted[idx]:.4f} km, "
                   f"actual={r_eq_s_actual[idx]:.4f} km, "
                   f"error={(abs(r_eq_s_predicted[idx]-r_eq_s_actual[idx])/r_eq_s_predicted[idx]*100):.2f}%\n")
        
        f.write("\n--- 3. 응답 시간 변화 영향 ---\n")
        for i, var in enumerate([0.5, 0.75, 1.0, 1.25, 1.5]):
            idx = int((var - 0.5) / 1.0 * (len(variation_range) - 1))
            f.write(f"  {var*100:5.0f}%: r_eq={r_eq_rt[idx]:.4f} km\n")
        
        # 상관관계 분석
        f.write("\n--- 상관관계 ---\n")
        corr_V = np.corrcoef(r_eq_V_predicted, r_eq_V_actual)[0, 1]
        corr_s = np.corrcoef(r_eq_s_predicted, r_eq_s_actual)[0, 1]
        f.write(f"  V* 예측-실제 상관계수: {corr_V:.6f}\n")
        f.write(f"  s* 예측-실제 상관계수: {corr_s:.6f}\n")
        
        f.write("\n결론:\n")
        if corr_V > 0.99 and corr_s > 0.99:
            f.write("  Eq. (39)가 실제 안전 반경을 매우 잘 예측합니다 (r > 0.99)\n")
        else:
            f.write("  Eq. (39)와 실제값 사이에 약간의 차이가 있습니다.\n")
    
    logger.info(f"  - 수치 결과 저장: sensitivity_results.txt")
    
    total_time = time.time() - start_time
    
    print("\n" + "="*70)
    print(f"✓ 시나리오 3 완료 (총 {total_time:.2f}초)")
    print(f"결과 저장 위치: {output_dir.absolute()}/")
    print("="*70)


def visualize_existing_field(field_path: str, config: dict, output_dir: Path):
    """
    저장된 안전 필드 시각화만 수행
    
    Parameters
    ----------
    field_path : str
        저장된 안전 필드 .npy 파일 경로
    config : dict
        설정 딕셔너리
    output_dir : Path
        출력 디렉토리
    """
    print("\n" + "="*70)
    print("시각화 전용 모드")
    print("="*70)
    
    # 1. 필드 로드
    logger.info(f"Step 1: 안전 필드 로드 중: {field_path}")
    
    if not Path(field_path).exists():
        logger.error(f"파일을 찾을 수 없습니다: {field_path}")
        raise FileNotFoundError(f"Field file not found: {field_path}")
    
    safety_values = np.load(field_path)
    logger.info(f"✓ 필드 로드 완료: shape={safety_values.shape}")
    
    # 2. AirspaceSafetyField 재구성
    logger.info("\nStep 2: 안전 필드 재구성...")
    field = create_safety_field_from_config(config)
    
    # 필드 데이터 할당
    if safety_values.shape != field.grid_shape:
        logger.warning(f"경고: 로드된 필드 shape {safety_values.shape}가 "
                      f"설정 파일의 shape {field.grid_shape}와 다릅니다.")
        logger.warning("설정 파일이 원래 계산과 동일한지 확인하세요.")
    
    field.field = safety_values
    
    # 3. 통계
    logger.info("\nStep 3: 통계 분석...")
    stats = field.get_statistics()
    logger.info(f"  최대 충돌 확률: {stats['max']:.6e}")
    logger.info(f"  위험 셀 (>1%): {stats['dangerous_cells_1pct']} 개")
    
    # 4. 시각화
    logger.info("\nStep 4: 시각화 생성...")
    
    z_mid = (field.bounds['z'][0] + field.bounds['z'][1]) / 2
    
    plot_safety_field_3d(
        field,
        uavs=None,
        threshold=0.001,
        save_path=str(output_dir / 'visualized_field_3d.png')
    )
    logger.info("  - 3D 시각화 저장")
    
    plot_safety_field_2d_slice(
        field,
        altitude=z_mid,
        uavs=None,
        show_contours=True,
        save_path=str(output_dir / 'visualized_field_2d.png')
    )
    logger.info("  - 2D 시각화 저장")
    
    probabilities = safety_values[safety_values > 0]
    if len(probabilities) > 0:
        plot_probability_distribution(
            probabilities,
            bins=50,
            save_path=str(output_dir / 'visualized_distribution.png')
        )
        logger.info("  - 확률 분포 저장")
    
    print("\n" + "="*70)
    print(f"✓ 시각화 완료")
    print(f"결과 저장 위치: {output_dir.absolute()}/")
    print("="*70)


def main():
    """메인 실행 함수"""
    
    parser = argparse.ArgumentParser(
        description='UAV 공역 안전성 측정 시스템',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예제:
  # 논문 재현 (기본)
  python main.py --scenario paper_reproduction
  
  # 커스텀 시뮬레이션
  python main.py --scenario custom --num_uavs 20 --gamma 2.0
  
  # 민감도 분석
  python main.py --scenario sensitivity
  
  # 저장된 필드 시각화
  python main.py --visualize_only --field_file results/paper_safety_field.npy
  
  # 병렬 처리 활성화
  python main.py --scenario paper_reproduction --parallel
        """
    )
    
    # 기본 인자
    parser.add_argument(
        '--config',
        default='config.yaml',
        help='설정 파일 경로 (기본값: config.yaml)'
    )
    
    parser.add_argument(
        '--output_dir',
        default='results/',
        help='결과 출력 디렉토리 (기본값: results/)'
    )
    
    # 시나리오 선택
    parser.add_argument(
        '--scenario',
        choices=['paper_reproduction', 'custom', 'sensitivity'],
        default='paper_reproduction',
        help='실행할 시나리오 선택'
    )
    
    # 커스텀 파라미터
    parser.add_argument(
        '--num_uavs',
        type=int,
        default=5,
        help='UAV 수 (커스텀 시나리오, 기본값: 5)'
    )
    
    parser.add_argument(
        '--gamma',
        type=float,
        default=1.0,
        help='안전 가중치 (커스텀 시나리오, 기본값: 1.0)'
    )
    
    parser.add_argument(
        '--parallel',
        action='store_true',
        help='병렬 처리 활성화'
    )
    
    # 시각화 전용 모드
    parser.add_argument(
        '--visualize_only',
        action='store_true',
        help='저장된 필드 시각화만 수행'
    )
    
    parser.add_argument(
        '--field_file',
        type=str,
        help='시각화할 필드 파일 경로 (.npy)'
    )
    
    args = parser.parse_args()
    
    # 로고 출력
    print("\n" + "="*70)
    print(" " * 15 + "UAV 공역 안전성 측정 시스템")
    print(" " * 10 + "UAV Airspace Safety Measurement System")
    print("="*70)
    
    try:
        # 출력 디렉토리 생성
        output_dir = Path(args.output_dir)
        output_dir.mkdir(exist_ok=True, parents=True)
        logger.info(f"출력 디렉토리: {output_dir.absolute()}")
        
        # 설정 로드
        config = load_config(args.config)
        
        # 시나리오 실행
        if args.visualize_only:
            # 시각화 전용 모드
            if not args.field_file:
                logger.error("오류: 시각화 전용 모드는 --field_file 옵션이 필요합니다")
                print("\n사용법: python main.py --visualize_only --field_file <파일경로>")
                sys.exit(1)
            
            visualize_existing_field(args.field_file, config, output_dir)
            
        else:
            # 시나리오 실행
            scenarios = {
                'paper_reproduction': lambda: scenario_paper_reproduction(
                    config, output_dir, args.parallel
                ),
                'custom': lambda: scenario_custom(config, args, output_dir),
                'sensitivity': lambda: scenario_sensitivity_analysis(config, output_dir)
            }
            
            scenarios[args.scenario]()
        
        print("\n" + "="*70)
        print("✓ 모든 작업이 성공적으로 완료되었습니다!")
        print("="*70 + "\n")
        
        return 0
        
    except FileNotFoundError as e:
        logger.error(f"파일 오류: {e}")
        return 1
    except ValueError as e:
        logger.error(f"값 오류: {e}")
        return 1
    except Exception as e:
        logger.error(f"예상치 못한 오류: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())
