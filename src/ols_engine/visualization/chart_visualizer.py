"""
차트 및 통계 시각화 모듈

Matplotlib과 Plotly를 사용하여 
침투 분석 결과를 차트로 시각화합니다.
"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import Circle, Rectangle
import seaborn as sns
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import geopandas as gpd
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from loguru import logger
import json


class ChartVisualizer:
    """차트 시각화 클래스"""
    
    def __init__(self):
        # 한글 폰트 설정
        plt.rcParams['font.family'] = ['DejaVu Sans', 'Liberation Sans', 'sans-serif']
        plt.rcParams['axes.unicode_minus'] = False
        
        # 색상 팔레트
        self.colors = {
            'penetration': '#dc3545',
            'normal': '#28a745', 
            'warning': '#ffc107',
            'info': '#17a2b8',
            'primary': '#007bff'
        }
        
        # 표면 색상
        self.surface_colors = {
            'approach_surface': '#007bff',
            'takeoff_surface': '#20c997',
            'transitional_surface': '#fd7e14', 
            'inner_horizontal_surface': '#6c757d',
            'conical_surface': '#e83e8c'
        }
    
    def create_penetration_dashboard(self, penetration_results: List, 
                                   summary: Dict, output_file: str) -> str:
        """
        종합 대시보드 차트 생성
        
        Args:
            penetration_results: 침투 분석 결과 리스트
            summary: 요약 통계
            output_file: 출력 파일 경로
            
        Returns:
            생성된 HTML 파일 경로
        """
        try:
            # 데이터 준비
            df = pd.DataFrame([{
                'obj_id': r.obj_id,
                'rwy_id': r.rwy_id,
                'penetration_m': r.penetration_m,
                'top_elev_m': r.top_elev_m,
                'z_allow_m': r.z_allow_m,
                'surface': r.controlling_surface,
                'is_penetration': r.is_penetration
            } for r in penetration_results])
            
            # Plotly 서브플롯 생성
            fig = make_subplots(
                rows=3, cols=2,
                subplot_titles=(
                    '침투율 현황', '표면별 침투 분포',
                    '침투량 히스토그램', '활주로별 침투 현황', 
                    '장애물 높이 vs 허용고도', '침투량 박스플롯'
                ),
                specs=[[{"type": "pie"}, {"type": "bar"}],
                       [{"type": "histogram"}, {"type": "bar"}],
                       [{"type": "scatter"}, {"type": "box"}]]
            )
            
            # 1. 침투율 파이차트
            penetration_counts = [
                summary['total_penetrations'], 
                summary['total_obstacles'] - summary['total_penetrations']
            ]
            fig.add_trace(
                go.Pie(
                    labels=['침투', '정상'],
                    values=penetration_counts,
                    hole=0.3,
                    marker_colors=['#dc3545', '#28a745']
                ),
                row=1, col=1
            )
            
            # 2. 표면별 침투 분포
            surface_data = summary.get('by_surface', {})
            if surface_data:
                surfaces = list(surface_data.keys())
                counts = [surface_data[s]['count'] for s in surfaces]
                
                fig.add_trace(
                    go.Bar(
                        x=surfaces,
                        y=counts,
                        marker_color=[self.surface_colors.get(s, '#6c757d') for s in surfaces],
                        text=counts,
                        textposition='auto'
                    ),
                    row=1, col=2
                )
            
            # 3. 침투량 히스토그램
            penetrations = df[df['is_penetration']]['penetration_m']
            if not penetrations.empty:
                fig.add_trace(
                    go.Histogram(
                        x=penetrations,
                        nbinsx=20,
                        marker_color='#fd7e14',
                        opacity=0.7
                    ),
                    row=2, col=1
                )
            
            # 4. 활주로별 침투 현황
            runway_data = summary.get('by_runway', {})
            if runway_data:
                runways = list(runway_data.keys())
                counts = [runway_data[r]['count'] for r in runways]
                
                fig.add_trace(
                    go.Bar(
                        x=runways,
                        y=counts,
                        marker_color='#17a2b8',
                        text=counts,
                        textposition='auto'
                    ),
                    row=2, col=2
                )
            
            # 5. 장애물 높이 vs 허용고도 산점도
            valid_data = df.dropna(subset=['z_allow_m'])
            if not valid_data.empty:
                fig.add_trace(
                    go.Scatter(
                        x=valid_data['z_allow_m'],
                        y=valid_data['top_elev_m'],
                        mode='markers',
                        marker=dict(
                            size=8,
                            color=valid_data['penetration_m'],
                            colorscale='RdYlGn_r',
                            showscale=True,
                            colorbar=dict(title="침투량 (m)")
                        ),
                        text=valid_data['obj_id'],
                        hovertemplate='<b>%{text}</b><br>허용고도: %{x:.1f}m<br>장애물고도: %{y:.1f}m<extra></extra>'
                    ),
                    row=3, col=1
                )
                
                # 1:1 라인 추가
                min_val = min(valid_data['z_allow_m'].min(), valid_data['top_elev_m'].min())
                max_val = max(valid_data['z_allow_m'].max(), valid_data['top_elev_m'].max())
                fig.add_trace(
                    go.Scatter(
                        x=[min_val, max_val],
                        y=[min_val, max_val],
                        mode='lines',
                        line=dict(dash='dash', color='red'),
                        name='침투 경계선'
                    ),
                    row=3, col=1
                )
            
            # 6. 침투량 박스플롯 (표면별)
            penetrating_df = df[df['is_penetration']]
            if not penetrating_df.empty:
                for surface in penetrating_df['surface'].unique():
                    surface_data = penetrating_df[penetrating_df['surface'] == surface]
                    fig.add_trace(
                        go.Box(
                            y=surface_data['penetration_m'],
                            name=surface,
                            marker_color=self.surface_colors.get(surface, '#6c757d')
                        ),
                        row=3, col=2
                    )
            
            # 레이아웃 업데이트
            fig.update_layout(
                height=1200,
                showlegend=False,
                title_text="OLS 침투 분석 대시보드",
                title_x=0.5,
                title_font_size=20
            )
            
            # 축 레이블 업데이트
            fig.update_xaxes(title_text="허용고도 (m)", row=3, col=1)
            fig.update_yaxes(title_text="장애물고도 (m)", row=3, col=1)
            fig.update_xaxes(title_text="침투량 (m)", row=2, col=1)
            fig.update_yaxes(title_text="빈도", row=2, col=1)
            fig.update_yaxes(title_text="침투량 (m)", row=3, col=2)
            
            # HTML 파일로 저장
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            fig.write_html(str(output_path))
            
            logger.info(f"대시보드 차트 생성 완료: {output_file}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"차트 생성 실패: {str(e)}")
            raise
    
    def create_runway_profile(self, penetration_gdf: gpd.GeoDataFrame,
                            runway_config: dict, ols_geometry,
                            output_file: str, profile_width: float = 1000) -> str:
        """
        활주로 중심선 단면도 생성
        
        Args:
            penetration_gdf: 침투 결과 데이터
            runway_config: 활주로 설정
            ols_geometry: OLS 기하학 모델
            output_file: 출력 파일 경로
            profile_width: 단면 폭 (m)
            
        Returns:
            생성된 이미지 파일 경로
        """
        try:
            # 활주로 중심선을 따라 단면 데이터 생성
            rwy_id = runway_config['rwy_id']
            thr_elev_m = runway_config['thr_elev_m']
            
            # X축 범위 설정 (THR 기준 -2km ~ +15km)
            x_range = np.linspace(-2000, 15000, 500)
            
            # 각 표면별 허용고도 계산
            surface_profiles = {}
            surface_names = ['approach_surface', 'takeoff_surface', 'transitional_surface', 
                           'inner_horizontal_surface', 'conical_surface']
            
            for x in x_range:
                z_allow, controlling_surface = ols_geometry.get_minimum_allowable_elevation(x, 0, thr_elev_m)
                if z_allow is not None:
                    if controlling_surface not in surface_profiles:
                        surface_profiles[controlling_surface] = {'x': [], 'z': []}
                    surface_profiles[controlling_surface]['x'].append(x)
                    surface_profiles[controlling_surface]['z'].append(z_allow)
            
            # 단면 범위 내 장애물 필터링
            profile_obstacles = penetration_gdf[
                (abs(penetration_gdf['y']) <= profile_width/2) &
                (penetration_gdf['rwy_id'] == rwy_id)
            ].copy()
            
            # 그래프 생성
            fig, ax = plt.subplots(figsize=(16, 10))
            
            # 지형/기준면
            ax.axhline(y=thr_elev_m, color='brown', linestyle='-', linewidth=2, 
                      label='지면 (THR 기준)', alpha=0.7)
            
            # 각 OLS 표면 그리기
            for surface, data in surface_profiles.items():
                if data['x']:
                    color = self.surface_colors.get(surface, '#6c757d')
                    ax.plot(data['x'], data['z'], color=color, linewidth=3, 
                           label=surface.replace('_', ' ').title(), alpha=0.8)
            
            # 장애물 표시
            if not profile_obstacles.empty:
                penetrating = profile_obstacles[profile_obstacles['penetration_m'] > 0]
                normal = profile_obstacles[profile_obstacles['penetration_m'] <= 0]
                
                # 침투 장애물
                if not penetrating.empty:
                    ax.scatter(penetrating['x'], penetrating['top_elev_m'], 
                             c='red', s=100, alpha=0.8, marker='^', 
                             label=f'침투 장애물 ({len(penetrating)}개)', zorder=5)
                
                # 정상 장애물
                if not normal.empty:
                    ax.scatter(normal['x'], normal['top_elev_m'],
                             c='green', s=50, alpha=0.6, marker='o',
                             label=f'정상 장애물 ({len(normal)}개)', zorder=4)
                
                # 장애물 ID 표시 (침투 장애물만)
                for _, obs in penetrating.iterrows():
                    ax.annotate(obs['obj_id'], 
                              (obs['x'], obs['top_elev_m']),
                              xytext=(5, 5), textcoords='offset points',
                              fontsize=8, alpha=0.8)
            
            # 그래프 설정
            ax.set_xlabel('THR로부터 거리 (m)', fontsize=12)
            ax.set_ylabel('표고 (m, AMSL)', fontsize=12)
            ax.set_title(f'활주로 {rwy_id} 중심선 단면도 (폭: ±{profile_width/2:.0f}m)', 
                        fontsize=14, fontweight='bold')
            ax.grid(True, alpha=0.3)
            ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
            
            # Y축 범위 조정
            if not profile_obstacles.empty:
                y_min = min(thr_elev_m - 10, profile_obstacles['top_elev_m'].min() - 20)
                y_max = profile_obstacles['top_elev_m'].max() + 30
                ax.set_ylim(y_min, y_max)
            
            plt.tight_layout()
            
            # 파일 저장
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            plt.savefig(str(output_path), dpi=300, bbox_inches='tight')
            plt.close()
            
            logger.info(f"단면도 생성 완료: {output_file}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"단면도 생성 실패: {str(e)}")
            raise
    
    def create_3d_visualization(self, penetration_gdf: gpd.GeoDataFrame,
                              ols_grid_gdf: Optional[gpd.GeoDataFrame],
                              runway_configs: List[dict],
                              output_file: str) -> str:
        """
        3D 시각화 생성
        
        Args:
            penetration_gdf: 침투 결과 데이터
            ols_grid_gdf: OLS 격자 데이터
            runway_configs: 활주로 설정 리스트
            output_file: 출력 파일 경로
            
        Returns:
            생성된 HTML 파일 경로
        """
        try:
            # 3D 산점도 생성
            fig = go.Figure()
            
            # 침투 장애물
            penetrations = penetration_gdf[penetration_gdf['penetration_m'] > 0]
            if not penetrations.empty:
                fig.add_trace(go.Scatter3d(
                    x=penetrations['x'],
                    y=penetrations['y'], 
                    z=penetrations['top_elev_m'],
                    mode='markers',
                    marker=dict(
                        size=8,
                        color=penetrations['penetration_m'],
                        colorscale='Reds',
                        colorbar=dict(title="침투량 (m)"),
                        showscale=True
                    ),
                    text=penetrations['obj_id'],
                    name='침투 장애물',
                    hovertemplate='<b>%{text}</b><br>위치: (%{x:.0f}, %{y:.0f})<br>높이: %{z:.1f}m<extra></extra>'
                ))
            
            # 정상 장애물
            normal = penetration_gdf[penetration_gdf['penetration_m'] <= 0]
            if not normal.empty:
                fig.add_trace(go.Scatter3d(
                    x=normal['x'],
                    y=normal['y'],
                    z=normal['top_elev_m'],
                    mode='markers',
                    marker=dict(
                        size=4,
                        color='green',
                        opacity=0.6
                    ),
                    text=normal['obj_id'],
                    name='정상 장애물',
                    hovertemplate='<b>%{text}</b><br>위치: (%{x:.0f}, %{y:.0f})<br>높이: %{z:.1f}m<extra></extra>'
                ))
            
            # OLS 표면 (격자가 있는 경우)
            if ols_grid_gdf is not None and not ols_grid_gdf.empty:
                # 표면별로 나누어서 표시
                for surface in ols_grid_gdf['controlling_surface'].unique():
                    if surface == 'none':
                        continue
                        
                    surface_data = ols_grid_gdf[ols_grid_gdf['controlling_surface'] == surface]
                    valid_data = surface_data.dropna(subset=['z_allow_m'])
                    
                    if not valid_data.empty:
                        fig.add_trace(go.Scatter3d(
                            x=valid_data['x'],
                            y=valid_data['y'],
                            z=valid_data['z_allow_m'],
                            mode='markers',
                            marker=dict(
                                size=2,
                                color=self.surface_colors.get(surface, '#6c757d'),
                                opacity=0.4
                            ),
                            name=f'{surface.replace("_", " ").title()}',
                            showlegend=True
                        ))
            
            # 활주로 표시
            for rwy_config in runway_configs:
                # THR 위치
                fig.add_trace(go.Scatter3d(
                    x=[0],  # 활주로 프레임에서 THR은 원점
                    y=[0],
                    z=[rwy_config['thr_elev_m']],
                    mode='markers',
                    marker=dict(
                        size=12,
                        color='blue',
                        symbol='diamond'
                    ),
                    name=f"THR {rwy_config['rwy_id']}",
                    hovertemplate=f"<b>THR {rwy_config['rwy_id']}</b><br>표고: {rwy_config['thr_elev_m']:.1f}m<extra></extra>"
                ))
            
            # 레이아웃 설정
            fig.update_layout(
                title='OLS 침투 분석 3D 시각화',
                scene=dict(
                    xaxis_title='X (m)',
                    yaxis_title='Y (m)', 
                    zaxis_title='높이 (m, AMSL)',
                    aspectmode='data'
                ),
                width=1000,
                height=700
            )
            
            # HTML 파일로 저장
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            fig.write_html(str(output_path))
            
            logger.info(f"3D 시각화 생성 완료: {output_file}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"3D 시각화 생성 실패: {str(e)}")
            raise
    
    def create_summary_report(self, summary: Dict, output_file: str) -> str:
        """
        요약 보고서 차트 생성 (PDF 출력용)
        
        Args:
            summary: 요약 통계
            output_file: 출력 파일 경로
            
        Returns:
            생성된 이미지 파일 경로
        """
        try:
            # 2x2 서브플롯 생성
            fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
            
            # 1. 침투율 도넛차트
            penetration_counts = [
                summary['total_penetrations'],
                summary['total_obstacles'] - summary['total_penetrations']
            ]
            colors = ['#dc3545', '#28a745']
            wedges, texts, autotexts = ax1.pie(
                penetration_counts, 
                labels=['침투', '정상'],
                colors=colors,
                autopct='%1.1f%%',
                pctdistance=0.85,
                wedgeprops=dict(width=0.5)
            )
            ax1.set_title('침투율 현황', fontsize=14, fontweight='bold')
            
            # 2. 표면별 침투 분포
            surface_data = summary.get('by_surface', {})
            if surface_data:
                surfaces = list(surface_data.keys())
                counts = [surface_data[s]['count'] for s in surfaces]
                bars = ax2.bar(surfaces, counts, 
                              color=[self.surface_colors.get(s, '#6c757d') for s in surfaces])
                ax2.set_title('표면별 침투 분포', fontsize=14, fontweight='bold')
                ax2.set_ylabel('침투 개수')
                ax2.tick_params(axis='x', rotation=45)
                
                # 값 표시
                for bar, count in zip(bars, counts):
                    ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1,
                            str(count), ha='center', va='bottom')
            
            # 3. 활주로별 침투 현황
            runway_data = summary.get('by_runway', {})
            if runway_data:
                runways = list(runway_data.keys())
                counts = [runway_data[r]['count'] for r in runways]
                max_pens = [runway_data[r]['max_penetration_m'] for r in runways]
                
                x_pos = np.arange(len(runways))
                
                bars1 = ax3.bar(x_pos - 0.2, counts, 0.4, label='침투 개수', color='#17a2b8')
                ax3_twin = ax3.twinx()
                bars2 = ax3_twin.bar(x_pos + 0.2, max_pens, 0.4, label='최대 침투량 (m)', color='#fd7e14')
                
                ax3.set_xlabel('활주로')
                ax3.set_ylabel('침투 개수', color='#17a2b8')
                ax3_twin.set_ylabel('최대 침투량 (m)', color='#fd7e14')
                ax3.set_title('활주로별 침투 현황', fontsize=14, fontweight='bold')
                ax3.set_xticks(x_pos)
                ax3.set_xticklabels(runways)
                
                # 범례
                lines1, labels1 = ax3.get_legend_handles_labels()
                lines2, labels2 = ax3_twin.get_legend_handles_labels()
                ax3.legend(lines1 + lines2, labels1 + labels2, loc='upper left')
            
            # 4. 통계 요약 테이블
            ax4.axis('tight')
            ax4.axis('off')
            
            table_data = [
                ['전체 장애물', f"{summary['total_obstacles']:,}개"],
                ['침투 장애물', f"{summary['total_penetrations']}개"],
                ['침투율', f"{summary['penetration_rate']:.1%}"],
                ['최대 침투량', f"{summary['max_penetration_m']:.1f}m"],
                ['평균 침투량', f"{summary['avg_penetration_m']:.1f}m"]
            ]
            
            table = ax4.table(cellText=table_data,
                             colLabels=['항목', '값'],
                             cellLoc='center',
                             loc='center',
                             colWidths=[0.6, 0.4])
            table.auto_set_font_size(False)
            table.set_fontsize(12)
            table.scale(1, 2)
            
            # 헤더 스타일
            for i in range(2):
                table[(0, i)].set_facecolor('#e9ecef')
                table[(0, i)].set_text_props(weight='bold')
            
            ax4.set_title('침투 분석 요약', fontsize=14, fontweight='bold')
            
            plt.suptitle('OLS 침투 분석 보고서', fontsize=18, fontweight='bold', y=0.98)
            plt.tight_layout()
            
            # 파일 저장
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            plt.savefig(str(output_path), dpi=300, bbox_inches='tight')
            plt.close()
            
            logger.info(f"요약 보고서 차트 생성 완료: {output_file}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"요약 보고서 생성 실패: {str(e)}")
            raise