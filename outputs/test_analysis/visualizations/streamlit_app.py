
import streamlit as st
import pandas as pd
import geopandas as gpd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import folium
from streamlit_folium import folium_static
import tempfile
import sys
from pathlib import Path
import json

# OLS 엔진 import
# Streamlit 앱이 visualizations 디렉토리에서 실행되므로 상위 디렉토리 경로 추가
webapp_root = Path(__file__).parent.parent.parent.parent  # /home/user/webapp
sys.path.insert(0, str(webapp_root))

try:
    from src.ols_engine.core.engine import OLSEngine
    from src.ols_engine.visualization.map_visualizer import MapVisualizer
    from src.ols_engine.visualization.chart_visualizer import ChartVisualizer
    st.success("✅ OLS 엔진 로드 성공!")
except ImportError as e:
    st.error(f"❌ OLS 엔진을 찾을 수 없습니다: {str(e)}")
    st.info("현재 경로 정보:")
    st.code(f"현재 파일 위치: {__file__}\n웹앱 루트: {webapp_root}\nPython 경로: {sys.path[:3]}...")
    st.stop()

# 페이지 설정
st.set_page_config(
    page_title="OLS 침투 분석 대시보드",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 제목
st.title("🛫 OLS 침투 분석 대시보드")
st.markdown("---")

# 사이드바 - 파일 업로드
st.sidebar.header("📁 입력 파일")

uploaded_gpkg = st.sidebar.file_uploader(
    "GeoPackage 파일 업로드",
    type=['gpkg'],
    help="obstacles, runway_axes 레이어가 포함된 GeoPackage 파일"
)

uploaded_config = st.sidebar.file_uploader(
    "설정 JSON 파일 업로드", 
    type=['json'],
    help="활주로 정보 및 OLS 파라미터가 포함된 JSON 파일"
)

# 분석 옵션
st.sidebar.header("⚙️ 분석 옵션")
generate_grid = st.sidebar.checkbox("검증 격자 생성", value=True)
grid_spacing = st.sidebar.slider("격자 간격 (m)", 50, 500, 200)

# 시각화 옵션
st.sidebar.header("🎨 시각화 옵션")
show_heatmap = st.sidebar.checkbox("침투 히트맵", value=True)
show_3d = st.sidebar.checkbox("3D 시각화", value=False)
map_style = st.sidebar.selectbox(
    "지도 스타일",
    ["OpenStreetMap", "CartoDB Positron", "위성영상"]
)

# 메인 컨텐츠
if uploaded_gpkg is not None and uploaded_config is not None:
    
    # 파일 임시 저장
    with tempfile.NamedTemporaryFile(delete=False, suffix='.gpkg') as tmp_gpkg:
        tmp_gpkg.write(uploaded_gpkg.read())
        gpkg_path = tmp_gpkg.name
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='.json') as tmp_config:
        tmp_config.write(uploaded_config.read())
        config_path = tmp_config.name
    
    try:
        # 분석 실행
        with st.spinner("OLS 침투 분석 실행 중..."):
            
            # 엔진 초기화
            engine = OLSEngine()
            
            # 설정 로드
            config = engine.data_loader.load_config(config_path)
            input_data = engine.data_loader.load_input_data(gpkg_path)
            
            # 침투 분석 수행
            penetration_engine = engine.penetration_engine
            results = penetration_engine.analyze_penetrations(
                input_data['obstacles'], 
                config['runways'],
                config.get('arp_elev_m', 0.0)
            )
            
            # 결과 변환
            penetration_gdf = penetration_engine.create_penetration_gdf(results)
            summary = penetration_engine.get_penetration_summary(results)
        
        # 성공 메시지
        st.success(f"✅ 분석 완료! {len(results)}개 결과 생성")
        
        # 요약 통계 (상단)
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "전체 장애물", 
                f"{summary['total_obstacles']:,}개"
            )
        
        with col2:
            st.metric(
                "침투 장애물", 
                f"{summary['total_penetrations']}개",
                f"{summary['penetration_rate']:.1%}"
            )
        
        with col3:
            st.metric(
                "최대 침투량",
                f"{summary['max_penetration_m']:.1f}m"
            )
        
        with col4:
            st.metric(
                "평균 침투량",
                f"{summary['avg_penetration_m']:.1f}m"
            )
        
        st.markdown("---")
        
        # 탭으로 구성된 시각화
        tab1, tab2, tab3, tab4 = st.tabs(["🗺️ 지도", "📊 차트", "📋 데이터", "📄 보고서"])
        
        with tab1:
            st.subheader("대화형 침투 분석 지도")
            
            # Folium 지도 생성
            map_viz = MapVisualizer()
            
            # WGS84로 변환
            penetration_wgs84 = penetration_gdf.to_crs('EPSG:4326')
            bounds = penetration_wgs84.total_bounds
            center_lat = (bounds[1] + bounds[3]) / 2
            center_lon = (bounds[0] + bounds[2]) / 2
            
            # 기본 지도
            m = folium.Map(
                location=[center_lat, center_lon],
                zoom_start=12,
                tiles='OpenStreetMap' if map_style == 'OpenStreetMap' else None
            )
            
            if map_style == "CartoDB Positron":
                folium.TileLayer('CartoDB positron').add_to(m)
            elif map_style == "위성영상":
                folium.TileLayer(
                    tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
                    attr='Esri'
                ).add_to(m)
            
            # 침투 장애물 표시
            penetrations = penetration_wgs84[penetration_wgs84['penetration_m'] > 0]
            normal = penetration_wgs84[penetration_wgs84['penetration_m'] <= 0]
            
            # 침투 장애물
            for _, obs in penetrations.iterrows():
                folium.CircleMarker(
                    location=[obs.geometry.y, obs.geometry.x],
                    radius=8,
                    popup=f"<b>{obs['obj_id']}</b><br>침투량: {obs['penetration_m']:.1f}m",
                    color='red',
                    fill=True,
                    fillColor='red',
                    fillOpacity=0.7
                ).add_to(m)
            
            # 정상 장애물
            for _, obs in normal.iterrows():
                folium.CircleMarker(
                    location=[obs.geometry.y, obs.geometry.x],
                    radius=3,
                    popup=f"<b>{obs['obj_id']}</b><br>정상",
                    color='green',
                    fill=True,
                    fillColor='green',
                    fillOpacity=0.5
                ).add_to(m)
            
            # Streamlit에 지도 표시
            folium_static(m, width=1200, height=600)
        
        with tab2:
            st.subheader("침투 분석 차트")
            
            # 침투율 도넛차트
            col1, col2 = st.columns(2)
            
            with col1:
                fig_pie = go.Figure(data=[go.Pie(
                    labels=['침투', '정상'],
                    values=[summary['total_penetrations'], 
                           summary['total_obstacles'] - summary['total_penetrations']],
                    hole=0.3,
                    marker_colors=['#dc3545', '#28a745']
                )])
                fig_pie.update_layout(title='침투율 현황')
                st.plotly_chart(fig_pie, use_container_width=True)
            
            with col2:
                # 표면별 침투 분포
                surface_data = summary.get('by_surface', {})
                if surface_data:
                    surfaces = list(surface_data.keys())
                    counts = [surface_data[s]['count'] for s in surfaces]
                    
                    fig_bar = go.Figure(data=[go.Bar(x=surfaces, y=counts)])
                    fig_bar.update_layout(title='표면별 침투 분포')
                    st.plotly_chart(fig_bar, use_container_width=True)
            
            # 침투량 히스토그램
            penetrating_df = pd.DataFrame([{
                'obj_id': r.obj_id,
                'penetration_m': r.penetration_m
            } for r in results if r.is_penetration])
            
            if not penetrating_df.empty:
                fig_hist = px.histogram(
                    penetrating_df, 
                    x='penetration_m',
                    title='침투량 분포',
                    labels={'penetration_m': '침투량 (m)', 'count': '개수'}
                )
                st.plotly_chart(fig_hist, use_container_width=True)
            
            # 3D 시각화 (선택적)
            if show_3d:
                st.subheader("3D 시각화")
                
                fig_3d = go.Figure()
                
                # 침투 장애물
                if not penetrations.empty:
                    fig_3d.add_trace(go.Scatter3d(
                        x=penetrations['x'],
                        y=penetrations['y'],
                        z=penetrations['top_elev_m'],
                        mode='markers',
                        marker=dict(
                            size=8,
                            color=penetrations['penetration_m'],
                            colorscale='Reds',
                            showscale=True
                        ),
                        text=penetrations['obj_id'],
                        name='침투 장애물'
                    ))
                
                fig_3d.update_layout(
                    title='OLS 침투 분석 3D 뷰',
                    scene=dict(
                        xaxis_title='X (m)',
                        yaxis_title='Y (m)',
                        zaxis_title='높이 (m)'
                    )
                )
                st.plotly_chart(fig_3d, use_container_width=True)
        
        with tab3:
            st.subheader("침투 분석 데이터")
            
            # 필터링 옵션
            col1, col2 = st.columns(2)
            with col1:
                show_only_penetrations = st.checkbox("침투 장애물만 표시", value=False)
            with col2:
                min_penetration = st.slider("최소 침투량 (m)", 0.0, 50.0, 0.0)
            
            # 데이터 필터링
            display_df = pd.DataFrame([{
                'obj_id': r.obj_id,
                'rwy_id': r.rwy_id,
                'penetration_m': r.penetration_m,
                'top_elev_m': r.top_elev_m,
                'z_allow_m': r.z_allow_m,
                'surface': r.controlling_surface,
                'status': '침투' if r.is_penetration else '정상'
            } for r in results])
            
            if show_only_penetrations:
                display_df = display_df[display_df['penetration_m'] > 0]
            
            if min_penetration > 0:
                display_df = display_df[display_df['penetration_m'] >= min_penetration]
            
            # 데이터 표시
            st.dataframe(
                display_df,
                use_container_width=True,
                column_config={
                    "penetration_m": st.column_config.NumberColumn(
                        "침투량 (m)",
                        help="양수는 침투, 0 이하는 정상",
                        format="%.2f"
                    ),
                    "status": st.column_config.TextColumn(
                        "상태",
                        help="침투 여부"
                    )
                }
            )
            
            # CSV 다운로드
            csv = display_df.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                label="CSV 다운로드",
                data=csv,
                file_name="ols_penetration_results.csv",
                mime="text/csv"
            )
        
        with tab4:
            st.subheader("침투 분석 보고서")
            
            # 요약 통계 테이블
            summary_data = {
                '항목': [
                    '전체 장애물 수',
                    '침투 장애물 수', 
                    '침투율',
                    '최대 침투량',
                    '평균 침투량'
                ],
                '값': [
                    f"{summary['total_obstacles']:,}개",
                    f"{summary['total_penetrations']}개",
                    f"{summary['penetration_rate']:.1%}",
                    f"{summary['max_penetration_m']:.1f}m",
                    f"{summary['avg_penetration_m']:.1f}m"
                ]
            }
            
            st.table(pd.DataFrame(summary_data))
            
            # 표면별 상세 통계
            st.subheader("표면별 침투 현황")
            surface_stats = []
            for surface, stats in summary.get('by_surface', {}).items():
                surface_stats.append({
                    '표면': surface,
                    '침투 개수': stats['count'],
                    '최대 침투량 (m)': f"{stats['max_penetration_m']:.1f}",
                    '평균 침투량 (m)': f"{stats['avg_penetration_m']:.1f}"
                })
            
            if surface_stats:
                st.table(pd.DataFrame(surface_stats))
            
            # 활주로별 상세 통계
            st.subheader("활주로별 침투 현황")
            runway_stats = []
            for runway, stats in summary.get('by_runway', {}).items():
                runway_stats.append({
                    '활주로': runway,
                    '침투 개수': stats['count'],
                    '최대 침투량 (m)': f"{stats['max_penetration_m']:.1f}",
                    '평균 침투량 (m)': f"{stats['avg_penetration_m']:.1f}"
                })
            
            if runway_stats:
                st.table(pd.DataFrame(runway_stats))
    
    except Exception as e:
        st.error(f"분석 중 오류 발생: {str(e)}")
        st.exception(e)

else:
    # 시작 화면
    st.info("👆 사이드바에서 GeoPackage 파일과 설정 JSON 파일을 업로드하세요.")
    
    # 사용법 안내
    st.markdown("""
    ## 📖 사용법
    
    ### 1. 입력 파일 준비
    
    **GeoPackage (.gpkg) 파일:**
    - `obstacles` 레이어: 장애물 위치 (필수 컬럼: obj_id, top_elev_m)
    - `runway_axes` 레이어: 활주로 중심선 (선택적)
    
    **설정 JSON 파일:**
    ```json
    {
      "crs_epsg": 5186,
      "arp_elev_m": 7.5,
      "runways": [
        {
          "rwy_id": "RWY-ID",
          "thr_x": 198345.12,
          "thr_y": 531234.88,
          "thr_elev_m": 7.3,
          "bearing_deg": 340.1,
          "annex14": { ... }
        }
      ]
    }
    ```
    
    ### 2. 분석 옵션 설정
    - 검증 격자 생성 여부
    - 격자 간격 조정
    - 시각화 옵션 선택
    
    ### 3. 결과 확인
    - **지도**: 대화형 침투 분석 지도
    - **차트**: 다양한 통계 차트
    - **데이터**: 상세 결과 테이블
    - **보고서**: 요약 통계 보고서
    
    ### 4. 결과 다운로드
    - CSV 형태로 결과 다운로드 가능
    """)
    
    # 샘플 데이터 다운로드
    st.markdown("### 📁 샘플 데이터")
    st.info("샘플 데이터를 사용하여 기능을 테스트해보세요.")
