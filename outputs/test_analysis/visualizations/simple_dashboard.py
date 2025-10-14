#!/usr/bin/env python3
"""
간단한 OLS 분석 결과 대시보드
기존 분석 결과 파일들을 읽어서 시각화
"""

import streamlit as st
import pandas as pd
import geopandas as gpd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import folium
from streamlit_folium import folium_static
import json
from pathlib import Path

# 페이지 설정
st.set_page_config(
    page_title="OLS 침투 분석 결과 대시보드",
    page_icon="✈️", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# 제목
st.title("🛫 OLS 침투 분석 결과 대시보드")
st.markdown("---")

# 결과 파일 경로
results_dir = Path(__file__).parent.parent
penetration_file = results_dir / "penetration_results.gpkg"
summary_file = results_dir / "analysis_summary.json"

# 결과 파일 존재 확인
if not penetration_file.exists() or not summary_file.exists():
    st.error("분석 결과 파일을 찾을 수 없습니다.")
    st.info("먼저 OLS 분석을 실행해주세요:")
    st.code("""python -m src.ols_engine.main \\
  --input data/sample_project.gpkg \\
  --config data/example_config.json \\
  --output outputs/analysis \\
  --create-dashboard""")
    st.stop()

# 결과 데이터 로드
@st.cache_data
def load_analysis_results():
    """분석 결과 데이터 로드"""
    try:
        # GeoDataFrame 로드
        gdf = gpd.read_file(str(penetration_file))
        
        # 요약 데이터 로드
        with open(summary_file, 'r', encoding='utf-8') as f:
            summary = json.load(f)
        
        return gdf, summary
    except Exception as e:
        st.error(f"데이터 로드 실패: {str(e)}")
        return None, None

# 데이터 로드
gdf, summary = load_analysis_results()

if gdf is None or summary is None:
    st.stop()

# 사이드바 - 필터링 옵션
st.sidebar.header("🎛️ 필터링 옵션")

# 활주로 필터
runways = sorted(gdf['rwy_id'].unique())
selected_runways = st.sidebar.multiselect(
    "활주로 선택",
    runways,
    default=runways
)

# 침투 필터
show_penetrations_only = st.sidebar.checkbox("침투 장애물만 표시", value=False)
min_penetration = st.sidebar.slider("최소 침투량 (m)", 0.0, 50.0, 0.0)

# 데이터 필터링
filtered_gdf = gdf[gdf['rwy_id'].isin(selected_runways)].copy()

if show_penetrations_only:
    filtered_gdf = filtered_gdf[filtered_gdf['penetration_m'] > 0]

if min_penetration > 0:
    filtered_gdf = filtered_gdf[filtered_gdf['penetration_m'] >= min_penetration]

# 메인 컨텐츠
st.success(f"✅ 분석 결과 로드 완료! {len(filtered_gdf)}개 결과 표시 중")

# 요약 통계 (상단)
col1, col2, col3, col4 = st.columns(4)

total_obstacles = len(gdf)
total_penetrations = len(gdf[gdf['penetration_m'] > 0])
penetration_rate = total_penetrations / total_obstacles if total_obstacles > 0 else 0
max_penetration = gdf['penetration_m'].max()

with col1:
    st.metric("전체 장애물", f"{total_obstacles:,}개")

with col2:
    st.metric("침투 장애물", f"{total_penetrations}개", f"{penetration_rate:.1%}")

with col3:
    st.metric("최대 침투량", f"{max_penetration:.1f}m")

with col4:
    avg_penetration = gdf[gdf['penetration_m'] > 0]['penetration_m'].mean()
    st.metric("평균 침투량", f"{avg_penetration:.1f}m" if not pd.isna(avg_penetration) else "0.0m")

st.markdown("---")

# 탭으로 구성된 시각화
tab1, tab2, tab3, tab4 = st.tabs(["🗺️ 지도", "📊 차트", "📋 데이터", "📄 보고서"])

with tab1:
    st.subheader("침투 분석 지도")
    
    if not filtered_gdf.empty:
        # WGS84로 변환
        gdf_wgs84 = filtered_gdf.to_crs('EPSG:4326')
        
        # 지도 중심점 계산
        bounds = gdf_wgs84.total_bounds
        center_lat = (bounds[1] + bounds[3]) / 2
        center_lon = (bounds[0] + bounds[2]) / 2
        
        # Folium 지도 생성
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=12,
            tiles='OpenStreetMap'
        )
        
        # 침투/정상 장애물 분리
        penetrations = gdf_wgs84[gdf_wgs84['penetration_m'] > 0]
        normal = gdf_wgs84[gdf_wgs84['penetration_m'] <= 0]
        
        # 침투 장애물 마커
        for _, obs in penetrations.iterrows():
            folium.CircleMarker(
                location=[obs.geometry.y, obs.geometry.x],
                radius=max(5, min(15, obs['penetration_m'] / 5)),  # 침투량에 따른 크기
                popup=folium.Popup(
                    f"<b>{obs['obj_id']}</b><br>"
                    f"활주로: {obs['rwy_id']}<br>"
                    f"침투량: {obs['penetration_m']:.1f}m<br>"
                    f"장애물 높이: {obs['top_elev_m']:.1f}m<br>"
                    f"허용 높이: {obs['z_allow_m']:.1f}m",
                    max_width=200
                ),
                color='red',
                fill=True,
                fillColor='red',
                fillOpacity=0.8,
                weight=2
            ).add_to(m)
        
        # 정상 장애물 마커
        for _, obs in normal.iterrows():
            folium.CircleMarker(
                location=[obs.geometry.y, obs.geometry.x],
                radius=3,
                popup=folium.Popup(
                    f"<b>{obs['obj_id']}</b><br>"
                    f"활주로: {obs['rwy_id']}<br>"
                    f"상태: 정상<br>"
                    f"장애물 높이: {obs['top_elev_m']:.1f}m<br>"
                    f"허용 높이: {obs['z_allow_m']:.1f}m",
                    max_width=200
                ),
                color='green',
                fill=True,
                fillColor='green',
                fillOpacity=0.6,
                weight=1
            ).add_to(m)
        
        # 지도 표시
        folium_static(m, width=1200, height=600)
        
        # 범례
        st.markdown("""
        **범례:**
        - 🔴 **빨간색**: 침투 장애물 (마커 크기 = 침투량)
        - 🟢 **초록색**: 정상 장애물
        """)
    else:
        st.warning("필터 조건에 맞는 데이터가 없습니다.")

with tab2:
    st.subheader("통계 차트")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # 침투율 도넛 차트
        fig_pie = go.Figure(data=[go.Pie(
            labels=['침투', '정상'],
            values=[total_penetrations, total_obstacles - total_penetrations],
            hole=0.3,
            marker_colors=['#dc3545', '#28a745']
        )])
        fig_pie.update_layout(
            title='전체 침투율 현황',
            height=400
        )
        st.plotly_chart(fig_pie, use_container_width=True)
    
    with col2:
        # 활주로별 침투 분포
        runway_stats = gdf.groupby('rwy_id').agg({
            'penetration_m': lambda x: (x > 0).sum()
        }).reset_index()
        runway_stats.columns = ['활주로', '침투_개수']
        
        fig_bar = px.bar(
            runway_stats,
            x='활주로',
            y='침투_개수',
            title='활주로별 침투 분포',
            color='침투_개수',
            color_continuous_scale='Reds'
        )
        fig_bar.update_layout(height=400)
        st.plotly_chart(fig_bar, use_container_width=True)
    
    # 침투량 히스토그램
    penetrating_data = gdf[gdf['penetration_m'] > 0]['penetration_m']
    
    if not penetrating_data.empty:
        fig_hist = px.histogram(
            x=penetrating_data,
            nbins=20,
            title='침투량 분포',
            labels={'x': '침투량 (m)', 'y': '개수'},
            color_discrete_sequence=['#dc3545']
        )
        fig_hist.update_layout(height=400)
        st.plotly_chart(fig_hist, use_container_width=True)
    
    # 3D 산점도
    if len(filtered_gdf) > 0:
        st.subheader("3D 공간 분포")
        
        fig_3d = go.Figure()
        
        # 침투 장애물
        penetrations_3d = filtered_gdf[filtered_gdf['penetration_m'] > 0]
        if not penetrations_3d.empty:
            fig_3d.add_trace(go.Scatter3d(
                x=penetrations_3d['x'],
                y=penetrations_3d['y'],
                z=penetrations_3d['top_elev_m'],
                mode='markers',
                marker=dict(
                    size=8,
                    color=penetrations_3d['penetration_m'],
                    colorscale='Reds',
                    showscale=True,
                    colorbar=dict(title="침투량 (m)")
                ),
                text=[f"ID: {id}<br>침투량: {pen:.1f}m" 
                      for id, pen in zip(penetrations_3d['obj_id'], penetrations_3d['penetration_m'])],
                name='침투 장애물'
            ))
        
        # 정상 장애물
        normal_3d = filtered_gdf[filtered_gdf['penetration_m'] <= 0]
        if not normal_3d.empty:
            fig_3d.add_trace(go.Scatter3d(
                x=normal_3d['x'],
                y=normal_3d['y'],
                z=normal_3d['top_elev_m'],
                mode='markers',
                marker=dict(
                    size=4,
                    color='green',
                    opacity=0.6
                ),
                text=[f"ID: {id}<br>정상" for id in normal_3d['obj_id']],
                name='정상 장애물'
            ))
        
        fig_3d.update_layout(
            title='OLS 침투 분석 3D 뷰',
            scene=dict(
                xaxis_title='X (m)',
                yaxis_title='Y (m)',
                zaxis_title='높이 (m)'
            ),
            height=600
        )
        st.plotly_chart(fig_3d, use_container_width=True)

with tab3:
    st.subheader("침투 분석 데이터")
    
    # 데이터 테이블 표시
    display_columns = ['obj_id', 'rwy_id', 'penetration_m', 'top_elev_m', 'z_allow_m', 'surface']
    
    # 상태 컬럼 추가
    display_df = filtered_gdf[display_columns].copy()
    display_df['상태'] = display_df['penetration_m'].apply(lambda x: '침투' if x > 0 else '정상')
    
    st.dataframe(
        display_df,
        use_container_width=True,
        column_config={
            "penetration_m": st.column_config.NumberColumn(
                "침투량 (m)",
                help="양수는 침투, 0 이하는 정상",
                format="%.2f"
            ),
            "top_elev_m": st.column_config.NumberColumn(
                "장애물 높이 (m)",
                format="%.2f"
            ),
            "z_allow_m": st.column_config.NumberColumn(
                "허용 높이 (m)",
                format="%.2f"
            )
        }
    )
    
    # CSV 다운로드
    csv = display_df.to_csv(index=False, encoding='utf-8-sig')
    st.download_button(
        label="📥 CSV 다운로드",
        data=csv,
        file_name=f"ols_penetration_results_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv"
    )

with tab4:
    st.subheader("침투 분석 보고서")
    
    # 요약 통계
    summary_data = {
        '항목': [
            '전체 장애물 수',
            '침투 장애물 수',
            '침투율',
            '최대 침투량',
            '평균 침투량'
        ],
        '값': [
            f"{total_obstacles:,}개",
            f"{total_penetrations}개", 
            f"{penetration_rate:.1%}",
            f"{max_penetration:.1f}m",
            f"{avg_penetration:.1f}m" if not pd.isna(avg_penetration) else "0.0m"
        ]
    }
    
    st.table(pd.DataFrame(summary_data))
    
    # 활주로별 통계
    st.subheader("활주로별 침투 현황")
    
    runway_detail_stats = []
    for runway in runways:
        runway_data = gdf[gdf['rwy_id'] == runway]
        runway_penetrations = runway_data[runway_data['penetration_m'] > 0]
        
        runway_detail_stats.append({
            '활주로': runway,
            '전체 장애물': len(runway_data),
            '침투 개수': len(runway_penetrations),
            '침투율': f"{len(runway_penetrations)/len(runway_data)*100:.1f}%" if len(runway_data) > 0 else "0.0%",
            '최대 침투량 (m)': f"{runway_penetrations['penetration_m'].max():.1f}" if not runway_penetrations.empty else "0.0",
            '평균 침투량 (m)': f"{runway_penetrations['penetration_m'].mean():.1f}" if not runway_penetrations.empty else "0.0"
        })
    
    st.table(pd.DataFrame(runway_detail_stats))
    
    # 표면별 통계
    st.subheader("표면별 침투 현황")
    
    surface_penetrations = gdf[gdf['penetration_m'] > 0]
    if not surface_penetrations.empty:
        surface_stats = surface_penetrations.groupby('surface').agg({
            'penetration_m': ['count', 'max', 'mean']
        }).round(1)
        surface_stats.columns = ['침투 개수', '최대 침투량 (m)', '평균 침투량 (m)']
        surface_stats = surface_stats.reset_index()
        
        st.table(surface_stats)
    else:
        st.info("침투 장애물이 없습니다.")

# 푸터
st.markdown("---")
st.markdown("**OLS 침투 분석 엔진** | ICAO Annex 14 기준 | 한국 항공법 준수")