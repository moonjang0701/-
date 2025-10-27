"""
시각화 모듈

논문의 Figure 11, 12, 13, 16을 재현할 수 있는 시각화 함수들을 제공합니다.
"""

import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from matplotlib import cm
from matplotlib.colors import Normalize, LinearSegmentedColormap
from typing import List, Optional, Tuple
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from core.safety_field import AirspaceSafetyField, UAV
from core.safety_envelope import SafetyEnvelope


# 논문 스타일 설정
plt.rcParams['font.size'] = 11
plt.rcParams['axes.labelsize'] = 12
plt.rcParams['axes.titlesize'] = 13
plt.rcParams['legend.fontsize'] = 10
plt.rcParams['figure.dpi'] = 100
plt.rcParams['savefig.dpi'] = 300
plt.rcParams['savefig.bbox'] = 'tight'


def plot_safety_field_3d(
    field: AirspaceSafetyField,
    uavs: Optional[List[UAV]] = None,
    threshold: float = 0.01,
    show_envelopes: bool = False,
    save_path: Optional[str] = None,
    figsize: Tuple[int, int] = (12, 9)
) -> None:
    """
    3D 안전 필드 시각화 (논문 Fig. 11-12 스타일)
    
    위험 영역을 voxel로 표시하고, UAV 위치와 안전 엔벨로프를 함께 표시합니다.
    
    Parameters
    ----------
    field : AirspaceSafetyField
        계산된 안전 필드
    uavs : Optional[List[UAV]]
        UAV 리스트 (위치 표시용)
    threshold : float, default=0.01
        표시할 최소 충돌 확률 (1%)
    show_envelopes : bool, default=False
        안전 엔벨로프 wireframe 표시 여부
    save_path : Optional[str]
        저장 경로 (None이면 화면 표시)
    figsize : Tuple[int, int]
        Figure 크기
    """
    if field.field is None:
        raise ValueError("안전 필드가 계산되지 않았습니다. compute_field()를 먼저 호출하세요.")
    
    fig = plt.figure(figsize=figsize)
    ax = fig.add_subplot(111, projection='3d')
    
    # 1. 위험 영역 추출 및 표시
    dangerous_regions = field.get_dangerous_regions(threshold=threshold)
    
    if len(dangerous_regions) > 0:
        # 각 위험 포인트의 충돌 확률 가져오기
        probabilities = []
        for pos in dangerous_regions:
            prob = field.get_value_at_position(pos)
            probabilities.append(prob)
        
        probabilities = np.array(probabilities)
        
        # 색상 매핑 (확률에 따라)
        norm = Normalize(vmin=threshold, vmax=probabilities.max())
        colors = cm.Reds(norm(probabilities))
        
        # Scatter plot으로 voxel 표현
        ax.scatter(
            dangerous_regions[:, 0],
            dangerous_regions[:, 1],
            dangerous_regions[:, 2],
            c=colors,
            marker='s',
            s=100,
            alpha=0.6,
            edgecolors='none',
            label=f'Dangerous Region (p > {threshold*100:.1f}%)'
        )
        
        # 컬러바
        sm = cm.ScalarMappable(cmap=cm.Reds, norm=norm)
        sm.set_array([])
        cbar = plt.colorbar(sm, ax=ax, pad=0.1, shrink=0.8)
        cbar.set_label('Conflict Probability', fontsize=11)
    
    # 2. UAV 위치 표시
    if uavs is not None and len(uavs) > 0:
        for i, uav in enumerate(uavs):
            ax.scatter(
                uav.position[0],
                uav.position[1],
                uav.position[2],
                marker='^',
                s=300,
                c='blue',
                edgecolors='black',
                linewidths=2,
                label=f'UAV {uav.id}',
                zorder=10
            )
            
            # 속도 벡터 표시 (화살표)
            if np.linalg.norm(uav.velocity) > 0:
                velocity_scale = 2.0
                ax.quiver(
                    uav.position[0],
                    uav.position[1],
                    uav.position[2],
                    uav.velocity[0] * velocity_scale,
                    uav.velocity[1] * velocity_scale,
                    uav.velocity[2] * velocity_scale,
                    color='blue',
                    arrow_length_ratio=0.3,
                    linewidth=2,
                    alpha=0.7
                )
            
            # 3. 안전 엔벨로프 표시
            if show_envelopes:
                envelope = SafetyEnvelope(
                    Vf=uav.Vf, Vb=uav.Vb, Va=uav.Va,
                    Vd=uav.Vd, Vl=uav.Vl,
                    response_time=uav.response_time
                )
                axes = envelope.compute_axes()
                
                plot_ellipsoid_wireframe(
                    ax,
                    center=uav.position,
                    a=axes['a'], b=axes['b'],
                    c=axes['c'], d=axes['d'], e=axes['e'],
                    color='blue',
                    alpha=0.15
                )
    
    # 축 설정
    ax.set_xlabel('X (km)', fontsize=12)
    ax.set_ylabel('Y (km)', fontsize=12)
    ax.set_zlabel('Z (km)', fontsize=12)
    ax.set_title('3D Airspace Safety Field', fontsize=14, fontweight='bold')
    
    # 공역 범위 설정
    ax.set_xlim([field.x_min, field.x_max])
    ax.set_ylim([field.y_min, field.y_max])
    ax.set_zlim([field.z_min, field.z_max])
    
    # 범례
    ax.legend(loc='upper left', fontsize=9)
    
    # 그리드
    ax.grid(True, alpha=0.3)
    
    # 저장 또는 표시
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"3D 안전 필드 저장: {save_path}")
    else:
        plt.show()
    
    plt.close()


def plot_safety_field_2d_slice(
    field: AirspaceSafetyField,
    altitude: float,
    uavs: Optional[List[UAV]] = None,
    show_contours: bool = True,
    contour_levels: Optional[List[float]] = None,
    save_path: Optional[str] = None,
    figsize: Tuple[int, int] = (10, 8)
) -> None:
    """
    특정 고도의 2D 슬라이스 히트맵 (논문 Fig. 11-12 재현)
    
    Parameters
    ----------
    field : AirspaceSafetyField
        계산된 안전 필드
    altitude : float
        슬라이스 고도 (km)
    uavs : Optional[List[UAV]]
        UAV 리스트 (위치 표시용)
    show_contours : bool, default=True
        등고선 표시 여부
    contour_levels : Optional[List[float]]
        등고선 레벨 (None이면 자동)
    save_path : Optional[str]
        저장 경로
    figsize : Tuple[int, int]
        Figure 크기
    """
    if field.field is None:
        raise ValueError("안전 필드가 계산되지 않았습니다.")
    
    # 고도에 가장 가까운 z 인덱스 찾기
    z_idx = int(np.argmin(np.abs(field.z_coords - altitude)))
    actual_altitude = field.z_coords[z_idx]
    
    # 2D 슬라이스 추출
    slice_data = field.field[:, :, z_idx].T  # Transpose for correct orientation
    
    fig, ax = plt.subplots(figsize=figsize)
    
    # 히트맵 표시
    extent = [field.x_min, field.x_max, field.y_min, field.y_max]
    
    im = ax.imshow(
        slice_data,
        extent=extent,
        origin='lower',
        cmap='hot',
        aspect='auto',
        interpolation='bilinear',
        alpha=0.8
    )
    
    # 컬러바
    cbar = plt.colorbar(im, ax=ax, pad=0.02)
    cbar.set_label('Conflict Probability', fontsize=12)
    
    # 등고선
    if show_contours:
        if contour_levels is None:
            # 자동 레벨 (0.01, 0.05, 0.1, 0.2, 0.5)
            max_prob = np.max(slice_data)
            if max_prob > 0:
                contour_levels = [0.01, 0.05, 0.1, 0.2, 0.5]
                contour_levels = [l for l in contour_levels if l < max_prob]
        
        if contour_levels and len(contour_levels) > 0:
            X, Y = np.meshgrid(field.x_coords, field.y_coords)
            contours = ax.contour(
                X, Y, slice_data,
                levels=contour_levels,
                colors='white',
                linewidths=1.5,
                alpha=0.8
            )
            ax.clabel(contours, inline=True, fontsize=9, fmt='%.2f')
    
    # UAV 위치 표시
    if uavs is not None:
        for uav in uavs:
            # 고도가 비슷한 UAV만 표시
            if abs(uav.position[2] - actual_altitude) < field.grid_resolution:
                ax.plot(
                    uav.position[0],
                    uav.position[1],
                    marker='^',
                    markersize=15,
                    color='cyan',
                    markeredgecolor='black',
                    markeredgewidth=2,
                    label=f'UAV {uav.id}'
                )
                
                # 속도 벡터 (2D projection)
                if np.linalg.norm(uav.velocity[:2]) > 0:
                    velocity_scale = 3.0
                    ax.arrow(
                        uav.position[0],
                        uav.position[1],
                        uav.velocity[0] * velocity_scale,
                        uav.velocity[1] * velocity_scale,
                        head_width=0.5,
                        head_length=0.8,
                        fc='cyan',
                        ec='black',
                        linewidth=2,
                        alpha=0.7
                    )
    
    # 축 설정
    ax.set_xlabel('X (km)', fontsize=12)
    ax.set_ylabel('Y (km)', fontsize=12)
    ax.set_title(
        f'Safety Field at Altitude z = {actual_altitude:.1f} km',
        fontsize=13,
        fontweight='bold'
    )
    
    # 범례
    if uavs is not None and len(uavs) > 0:
        ax.legend(loc='upper right', fontsize=10)
    
    # 그리드
    ax.grid(True, alpha=0.3, linestyle='--')
    
    # 저장 또는 표시
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"2D 슬라이스 저장: {save_path}")
    else:
        plt.show()
    
    plt.close()


def plot_trajectory_comparison(
    field: AirspaceSafetyField,
    original_path: List[np.ndarray],
    optimized_path: List[np.ndarray],
    altitude: float,
    save_path: Optional[str] = None,
    figsize: Tuple[int, int] = (12, 9)
) -> None:
    """
    경로 최적화 전/후 비교 (논문 Fig. 13 재현)
    
    Parameters
    ----------
    field : AirspaceSafetyField
        배경으로 사용할 안전 필드
    original_path : List[np.ndarray]
        원본 경로 waypoints
    optimized_path : List[np.ndarray]
        최적화된 경로 waypoints
    altitude : float
        표시할 고도 (km)
    save_path : Optional[str]
        저장 경로
    figsize : Tuple[int, int]
        Figure 크기
    """
    if field.field is None:
        raise ValueError("안전 필드가 계산되지 않았습니다.")
    
    # 고도 슬라이스 찾기
    z_idx = int(np.argmin(np.abs(field.z_coords - altitude)))
    actual_altitude = field.z_coords[z_idx]
    slice_data = field.field[:, :, z_idx].T
    
    fig, ax = plt.subplots(figsize=figsize)
    
    # 배경: 안전 필드
    extent = [field.x_min, field.x_max, field.y_min, field.y_max]
    im = ax.imshow(
        slice_data,
        extent=extent,
        origin='lower',
        cmap='hot',
        aspect='auto',
        interpolation='bilinear',
        alpha=0.6
    )
    
    # 컬러바
    cbar = plt.colorbar(im, ax=ax, pad=0.02)
    cbar.set_label('Conflict Probability', fontsize=12)
    
    # 원본 경로
    original_array = np.array(original_path)
    ax.plot(
        original_array[:, 0],
        original_array[:, 1],
        'r--',
        linewidth=3,
        label='Original Path',
        alpha=0.8
    )
    ax.scatter(
        original_array[:, 0],
        original_array[:, 1],
        c='red',
        s=50,
        marker='o',
        edgecolors='black',
        linewidths=1,
        alpha=0.8,
        zorder=5
    )
    
    # 최적화된 경로
    optimized_array = np.array(optimized_path)
    ax.plot(
        optimized_array[:, 0],
        optimized_array[:, 1],
        'b-',
        linewidth=3,
        label='Optimized Path',
        alpha=0.9
    )
    ax.scatter(
        optimized_array[:, 0],
        optimized_array[:, 1],
        c='blue',
        s=50,
        marker='s',
        edgecolors='black',
        linewidths=1,
        alpha=0.9,
        zorder=5
    )
    
    # 시작/끝 지점 강조
    ax.scatter(
        original_array[0, 0], original_array[0, 1],
        c='green', s=200, marker='*',
        edgecolors='black', linewidths=2,
        label='Start', zorder=10
    )
    ax.scatter(
        original_array[-1, 0], original_array[-1, 1],
        c='purple', s=200, marker='*',
        edgecolors='black', linewidths=2,
        label='Goal', zorder=10
    )
    
    # 축 설정
    ax.set_xlabel('X (km)', fontsize=12)
    ax.set_ylabel('Y (km)', fontsize=12)
    ax.set_title(
        f'Trajectory Comparison at z = {actual_altitude:.1f} km',
        fontsize=13,
        fontweight='bold'
    )
    
    # 범례
    ax.legend(loc='best', fontsize=11, framealpha=0.9)
    
    # 그리드
    ax.grid(True, alpha=0.3, linestyle='--')
    
    # 저장 또는 표시
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"경로 비교 저장: {save_path}")
    else:
        plt.show()
    
    plt.close()


def plot_temporal_evolution(
    field_snapshots: List[AirspaceSafetyField],
    timestamps: List[float],
    altitude: float,
    subplot_layout: Tuple[int, int] = (2, 3),
    save_path: Optional[str] = None,
    figsize: Tuple[int, int] = (18, 12)
) -> None:
    """
    시간에 따른 안전 필드 변화 (논문 Fig. 16 재현)
    
    Parameters
    ----------
    field_snapshots : List[AirspaceSafetyField]
        각 시간대의 안전 필드
    timestamps : List[float]
        각 스냅샷의 시간 (min)
    altitude : float
        표시할 고도 (km)
    subplot_layout : Tuple[int, int]
        서브플롯 배치 (rows, cols)
    save_path : Optional[str]
        저장 경로
    figsize : Tuple[int, int]
        Figure 크기
    """
    if len(field_snapshots) != len(timestamps):
        raise ValueError("field_snapshots와 timestamps의 길이가 같아야 합니다.")
    
    rows, cols = subplot_layout
    n_plots = min(len(field_snapshots), rows * cols)
    
    fig, axes = plt.subplots(rows, cols, figsize=figsize)
    axes = axes.flatten() if rows * cols > 1 else [axes]
    
    # 전체 필드의 최대/최소 확률 (일관된 컬러 스케일)
    vmin = 0
    vmax = max([np.max(f.field) for f in field_snapshots if f.field is not None])
    
    for idx in range(n_plots):
        ax = axes[idx]
        field = field_snapshots[idx]
        t = timestamps[idx]
        
        if field.field is None:
            ax.text(0.5, 0.5, 'No Data', ha='center', va='center')
            ax.set_title(f't = {t:.1f} min')
            continue
        
        # 고도 슬라이스
        z_idx = int(np.argmin(np.abs(field.z_coords - altitude)))
        slice_data = field.field[:, :, z_idx].T
        
        # 히트맵
        extent = [field.x_min, field.x_max, field.y_min, field.y_max]
        im = ax.imshow(
            slice_data,
            extent=extent,
            origin='lower',
            cmap='hot',
            aspect='auto',
            interpolation='bilinear',
            vmin=vmin,
            vmax=vmax
        )
        
        # 제목
        ax.set_title(f't = {t:.1f} min', fontsize=12, fontweight='bold')
        ax.set_xlabel('X (km)', fontsize=10)
        ax.set_ylabel('Y (km)', fontsize=10)
        ax.grid(True, alpha=0.3)
    
    # 남은 subplot 제거
    for idx in range(n_plots, len(axes)):
        fig.delaxes(axes[idx])
    
    # 공통 컬러바
    fig.subplots_adjust(right=0.9)
    cbar_ax = fig.add_axes([0.92, 0.15, 0.02, 0.7])
    cbar = fig.colorbar(im, cax=cbar_ax)
    cbar.set_label('Conflict Probability', fontsize=12)
    
    # 전체 제목
    fig.suptitle(
        'Temporal Evolution of Safety Field',
        fontsize=15,
        fontweight='bold',
        y=0.98
    )
    
    # 저장 또는 표시
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"시간 진화 플롯 저장: {save_path}")
    else:
        plt.show()
    
    plt.close()


def plot_ellipsoid_wireframe(
    ax: Axes3D,
    center: np.ndarray,
    a: float, b: float, c: float, d: float, e: float,
    color: str = 'blue',
    alpha: float = 0.2,
    resolution: int = 20
) -> None:
    """
    안전 엔벨로프(타원체) wireframe 그리기
    
    비대칭 타원체를 4개 사분면으로 나누어 표시합니다.
    
    Parameters
    ----------
    ax : Axes3D
        matplotlib 3D axes
    center : np.ndarray, shape (3,)
        중심 좌표 [x, y, z]
    a : float
        전방 반경 (km)
    b : float
        후방 반경 (km)
    c : float
        상승 반경 (km)
    d : float
        하강 반경 (km)
    e : float
        횡방향 반경 (km)
    color : str
        wireframe 색상
    alpha : float
        투명도
    resolution : int
        표면 해상도
    """
    u = np.linspace(0, 2 * np.pi, resolution)
    v = np.linspace(0, np.pi, resolution)
    
    # 4개 사분면 (octant) 각각에 대해 그리기
    quadrants = [
        (a, c, 0, np.pi/2, 0, np.pi/2),      # 전방-상승
        (a, d, 0, np.pi/2, np.pi/2, np.pi),  # 전방-하강
        (b, c, np.pi/2, np.pi, 0, np.pi/2),  # 후방-상승
        (b, d, np.pi/2, np.pi, np.pi/2, np.pi)  # 후방-하강
    ]
    
    for r_x, r_z, u_min, u_max, v_min, v_max in quadrants:
        u_range = np.linspace(u_min, u_max, resolution // 2)
        v_range = np.linspace(v_min, v_max, resolution // 2)
        u_grid, v_grid = np.meshgrid(u_range, v_range)
        
        # 파라메트릭 타원체
        x = center[0] + r_x * np.cos(u_grid) * np.sin(v_grid)
        y = center[1] + e * np.sin(u_grid) * np.sin(v_grid)
        z = center[2] + r_z * np.cos(v_grid)
        
        ax.plot_surface(
            x, y, z,
            color=color,
            alpha=alpha,
            edgecolor=color,
            linewidth=0.3,
            antialiased=True
        )


def plot_convergence_curve(
    costs: List[float],
    xlabel: str = 'Iteration',
    ylabel: str = 'Cost',
    title: str = 'Optimization Convergence',
    save_path: Optional[str] = None,
    figsize: Tuple[int, int] = (10, 6)
) -> None:
    """
    최적화 알고리즘의 수렴 곡선
    
    Parameters
    ----------
    costs : List[float]
        각 세대/반복의 비용 값
    xlabel : str
        X축 레이블
    ylabel : str
        Y축 레이블
    title : str
        플롯 제목
    save_path : Optional[str]
        저장 경로
    figsize : Tuple[int, int]
        Figure 크기
    """
    fig, ax = plt.subplots(figsize=figsize)
    
    iterations = range(1, len(costs) + 1)
    
    ax.plot(
        iterations, costs,
        'b-',
        linewidth=2,
        marker='o',
        markersize=4,
        markerfacecolor='blue',
        markeredgecolor='black',
        markeredgewidth=0.5
    )
    
    # 최소값 표시
    min_idx = np.argmin(costs)
    min_cost = costs[min_idx]
    ax.plot(
        min_idx + 1, min_cost,
        'r*',
        markersize=15,
        label=f'Best: {min_cost:.6f} at iter {min_idx + 1}'
    )
    
    ax.set_xlabel(xlabel, fontsize=12)
    ax.set_ylabel(ylabel, fontsize=12)
    ax.set_title(title, fontsize=13, fontweight='bold')
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.legend(fontsize=10)
    
    # 저장 또는 표시
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"수렴 곡선 저장: {save_path}")
    else:
        plt.show()
    
    plt.close()


def plot_probability_distribution(
    probabilities: np.ndarray,
    bins: int = 50,
    save_path: Optional[str] = None,
    figsize: Tuple[int, int] = (10, 6)
) -> None:
    """
    충돌 확률 분포 히스토그램
    
    Parameters
    ----------
    probabilities : np.ndarray
        충돌 확률 값들
    bins : int
        히스토그램 빈 개수
    save_path : Optional[str]
        저장 경로
    figsize : Tuple[int, int]
        Figure 크기
    """
    fig, ax = plt.subplots(figsize=figsize)
    
    # 0이 아닌 확률만 플롯
    non_zero_probs = probabilities[probabilities > 0]
    
    if len(non_zero_probs) > 0:
        ax.hist(
            non_zero_probs,
            bins=bins,
            color='red',
            alpha=0.7,
            edgecolor='black',
            linewidth=0.5
        )
        
        # 통계 정보
        mean_prob = np.mean(non_zero_probs)
        max_prob = np.max(non_zero_probs)
        
        ax.axvline(
            mean_prob,
            color='blue',
            linestyle='--',
            linewidth=2,
            label=f'Mean: {mean_prob:.6f}'
        )
        ax.axvline(
            max_prob,
            color='green',
            linestyle='--',
            linewidth=2,
            label=f'Max: {max_prob:.6f}'
        )
    
    ax.set_xlabel('Conflict Probability', fontsize=12)
    ax.set_ylabel('Frequency', fontsize=12)
    ax.set_title('Probability Distribution', fontsize=13, fontweight='bold')
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3, axis='y')
    
    # 저장 또는 표시
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"확률 분포 저장: {save_path}")
    else:
        plt.show()
    
    plt.close()
