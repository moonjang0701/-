# 청라시티타워 인근 5km 반경 건물 데이터 변환

청라시티타워 인근 반경 5km 범위의 건물 정보를 GeoJSON 형식에서 KML 형식으로 변환한 프로젝트입니다.

## 📊 데이터 통계

- **총 건물 수**: 31,388개
- **낮은 건물 (< 20m)**: 30,565개
- **중간 건물 (20-50m)**: 517개
- **고층 건물 (> 50m)**: 306개

## 🎯 중심 좌표 (청라시티타워)

- **위도**: 37.533053
- **경도**: 126.633973

## 📁 생성된 파일

### 1. `cheongna_buildings_5km.kml` (25.69 MB)
모든 31,388개 건물을 포함한 전체 KML 파일

**특징:**
- 높이에 따라 3단계 색상 구분
  - 🔵 파란색: 낮은 건물 (< 20m)
  - 🟡 노란색: 중간 건물 (20-50m)
  - 🔴 빨간색: 높은 건물 (> 50m)
- 각 건물의 실제 높이로 3D 표현
- `extrude=1`, `altitudeMode=relativeToGround` 사용

### 2. `cheongna_buildings_above_50m.kml` (0.63 MB)
50m 이상의 고층 건물만 포함 (306개)

**높이 범위:**
- 최소: 50.0m
- 최대: 8149.0m (데이터 오류 가능성 높음)
- 평균: 101.3m

### 3. `cheongna_sample_building.kml` (1.4 KB)
예시 건물 (75m x 75m x 448m 빨간 박스)

## 🛠️ 사용된 스크립트

### `geojson_to_kml.py`
모든 GeoJSON 파일을 읽어서 하나의 KML 파일로 변환

```bash
python3 geojson_to_kml.py
```

**기능:**
- 31,388개의 GeoJSON 파일 일괄 처리
- 높이에 따른 자동 색상 분류
- 3D 건물 표현 (extrude)
- 진행상황 표시 (1000개 단위)

### `filter_buildings_by_height.py`
특정 높이 이상의 건물만 필터링하여 KML 생성

```bash
# 50m 이상 건물만
python3 filter_buildings_by_height.py 50

# 100m 이상 건물만
python3 filter_buildings_by_height.py 100
```

## 📐 좌표 시스템 변환

### GeoJSON 형식
```json
{
  "type": "Feature",
  "properties": {
    "height": "12",
    "bld_nm": "건물명"
  },
  "geometry": {
    "type": "MultiPolygon",
    "coordinates": [[[[경도, 위도], ...]]]
  }
}
```

### KML 형식
```xml
<Polygon>
  <extrude>1</extrude>
  <altitudeMode>relativeToGround</altitudeMode>
  <outerBoundaryIs>
    <LinearRing>
      <coordinates>
        경도,위도,높이
        경도,위도,높이
        ...
      </coordinates>
    </LinearRing>
  </outerBoundaryIs>
</Polygon>
```

**주요 차이점:**
1. GeoJSON: `[경도, 위도]` 배열 형식
2. KML: `경도,위도,높이` 문자열 형식 (쉼표로 구분)
3. KML은 높이 정보를 세 번째 값으로 추가

## 🎨 KML 스타일 설정

### 색상 코드 (KML은 aabbggrr 형식)
- `ff0000ff`: 불투명 빨간색 (외곽선)
- `7fff0000`: 반투명 파란색 (낮은 건물)
- `7f00ffff`: 반투명 노란색 (중간 건물)
- `7f0000ff`: 반투명 빨간색 (높은 건물)

### LookAt 설정
```xml
<LookAt>
  <heading>327.04</heading>     <!-- 방향 -->
  <tilt>83.30</tilt>            <!-- 기울기 -->
  <latitude>37.533053</latitude>
  <longitude>126.633973</longitude>
  <range>5000</range>           <!-- 거리 -->
  <altitude>0</altitude>
</LookAt>
```

## 📦 원본 데이터

- **파일명**: `반경5km.zip` (13.1 MB)
- **압축 해제 크기**: 약 139 MB
- **파일 수**: 31,388개의 `.geojson` 파일
- **명명 규칙**: `bld_000001.geojson` ~ `bld_031388.geojson`

## 🚀 사용 방법

### Google Earth에서 열기
1. Google Earth Pro 실행
2. `File` → `Open` 선택
3. 생성된 `.kml` 파일 선택
4. 3D 건물이 표시됨

### 프로그래밍으로 사용
```python
import xml.etree.ElementTree as ET

tree = ET.parse('cheongna_buildings_5km.kml')
root = tree.getroot()

# 모든 Placemark 찾기
for placemark in root.findall('.//{http://www.opengis.net/kml/2.2}Placemark'):
    name = placemark.find('{http://www.opengis.net/kml/2.2}name').text
    print(name)
```

## ⚠️ 데이터 품질 이슈

1. **높이 이상값**: 일부 건물의 높이가 비정상적으로 높음 (예: 8149m)
2. **건물명 누락**: 대부분의 건물에 이름이 없음 (`bld_nm=""`)
3. **좌표 정밀도**: 소수점 약 14자리까지 표현

## 🔧 향후 개선 사항

- [ ] 높이 이상값 필터링 (예: 500m 이상 제외)
- [ ] 건물명 데이터 보강
- [ ] 건물 용도별 색상 구분
- [ ] 인터랙티브 웹 뷰어 추가
- [ ] 건물 면적 계산 기능

## 📝 라이선스

이 프로젝트는 공개 건물 데이터를 기반으로 하며, 변환 스크립트는 자유롭게 사용 가능합니다.

## 👤 작성자

GenSpark AI Developer

---

**생성 일시**: 2025-11-07
