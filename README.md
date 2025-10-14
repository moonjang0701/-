# OLS 침투 판정 엔진

ICAO/국내 기준의 장애물제한표면(OLS) 침투 판정을 위한 결정론적 기하 연산 엔진입니다.

## 개요

이 엔진은 CAD/GIS 벡터 데이터를 입력받아 다음을 수행합니다:

1. **CAD→GIS 정규화**: EPSG:5186 좌표계로 통일
2. **OLS 허용고도 함수 계산**: 각 표면별 기하학적 모델링
3. **장애물 침투 판정**: 결정론적 수치 계산
4. **시각화 및 보고서**: 지도/테이블 형태 결과 생성

## 주요 특징

- **결정론적**: 동일 입력 → 동일 결과 보장
- **수학적 정확성**: 이미지/LLM 추론 대신 기하 연산 사용
- **표준 준수**: ICAO Annex 14 및 국내 기준 지원
- **다양한 출력**: GeoPackage, CSV, GeoJSON, QGIS 스타일

## 입력 형식

### project.gpkg (GeoPackage)
- `runway_axes`: 활주로 중심선 (LineString)
- `obstacles`: 장애물 위치 및 높이 (Point/Polygon)

### config.json
```json
{
  "crs_epsg": 5186,
  "geoid": "KGEOID2020",
  "runways": [
    {
      "rwy_id": "RKSI-34",
      "thr_x": 198345.12,
      "thr_y": 531234.88,
      "thr_elev_m": 7.3,
      "bearing_deg": 340.1,
      "annex14": {
        "approach": {"slope": 0.025, "inner_width_m": 300, "divergence": 0.10, "length_m": 15000},
        "takeoff": {"slope": 0.02, "inner_width_m": 180, "divergence": 0.10, "length_m": 15000},
        "transitional": {"slope": 0.143, "height_cap_m": 45},
        "inner_horizontal": {"radius_m": 4000, "height_m": 45},
        "conical": {"slope": 0.05, "height_m": 100}
      }
    }
  ]
}
```

## 출력 결과

### project.gpkg (갱신)
- `penetrations`: 침투 장애물 위치 및 침투량
- `ols_grid`: OLS 허용고도 격자 (검증용)

### 요약 보고서
- `penetration_summary.csv`: 침투 통계 요약
- `run.log`: 처리 과정 상세 로그

### 시각화 (선택)
- QGIS 스타일 파일 (SLD/QML)
- Cesium 시각화용 GeoJSON

## 사용법

```bash
# 의존성 설치
pip install -r requirements.txt

# 엔진 실행
python -m ols_engine.main --input project.gpkg --config config.json --output outputs/

# 또는 패키지 설치 후
pip install -e .
ols-engine --input project.gpkg --config config.json --output outputs/
```

## 좌표계 및 고도 기준

- **좌표계**: EPSG:5186 (중부 TM) 고정
- **고도 기준**: AMSL (지오이드 보정 일관 적용)
- **정밀도**: 결정론적 기하 연산으로 mm 단위 정확도

## 품질 검증

- 무효 좌표/결측 표고 에러 처리
- 샘플 격자점에서 z_allow 검증
- 다활주로 겹침 구역 최솟값 적용 확인

## 라이센스

MIT License - 자세한 내용은 LICENSE 파일 참조