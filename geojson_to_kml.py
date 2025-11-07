#!/usr/bin/env python3
"""
GeoJSON을 KML로 변환하는 스크립트
청라시티타워 인근 반경 5km 건물 정보 변환
"""

import json
import glob
import os
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom

def calculate_centroid(coordinates):
    """폴리곤의 중심점 계산"""
    if not coordinates or not coordinates[0]:
        return None, None
    
    # MultiPolygon의 첫 번째 폴리곤의 외부 링 사용
    ring = coordinates[0][0] if len(coordinates[0]) > 0 else []
    
    if not ring:
        return None, None
    
    lon_sum = sum(coord[0] for coord in ring)
    lat_sum = sum(coord[1] for coord in ring)
    count = len(ring)
    
    return lon_sum / count, lat_sum / count

def convert_polygon_to_kml_coords(coordinates):
    """
    GeoJSON 좌표를 KML 좌표 형식으로 변환
    GeoJSON: [longitude, latitude]
    KML: longitude,latitude,altitude
    """
    if not coordinates or not coordinates[0]:
        return ""
    
    # MultiPolygon의 첫 번째 폴리곤의 외부 링 사용
    ring = coordinates[0][0] if len(coordinates[0]) > 0 else []
    
    kml_coords = []
    for coord in ring:
        lon, lat = coord[0], coord[1]
        kml_coords.append(f"{lon},{lat},0")
    
    return "\n              ".join(kml_coords)

def create_kml_from_geojsons(input_pattern, output_file, center_lat=37.533053, center_lon=126.633973):
    """
    여러 GeoJSON 파일을 읽어서 하나의 KML 파일로 변환
    """
    # KML 루트 요소 생성
    kml = Element('kml')
    kml.set('xmlns', 'http://www.opengis.net/kml/2.2')
    
    document = SubElement(kml, 'Document')
    name = SubElement(document, 'name')
    name.text = 'Cheongna Buildings (5km radius)'
    
    # LookAt 설정 (청라시티타워 기준)
    lookat = SubElement(document, 'LookAt')
    heading = SubElement(lookat, 'heading')
    heading.text = '327.04412726540033'
    tilt = SubElement(lookat, 'tilt')
    tilt.text = '83.29890837595849'
    latitude = SubElement(lookat, 'latitude')
    latitude.text = str(center_lat)
    longitude = SubElement(lookat, 'longitude')
    longitude.text = str(center_lon)
    range_elem = SubElement(lookat, 'range')
    range_elem.text = '5000'
    altitude = SubElement(lookat, 'altitude')
    altitude.text = '0'
    
    # 건물 스타일 정의 (높이에 따른 색상)
    # 낮은 건물: 파란색, 중간 건물: 노란색, 높은 건물: 빨간색
    style_low = SubElement(document, 'Style')
    style_low.set('id', 'buildingLow')
    line_style_low = SubElement(style_low, 'LineStyle')
    color_low_line = SubElement(line_style_low, 'color')
    color_low_line.text = 'ff0000ff'  # 빨간색 외곽선
    width_low = SubElement(line_style_low, 'width')
    width_low.text = '1.0'
    poly_style_low = SubElement(style_low, 'PolyStyle')
    color_low = SubElement(poly_style_low, 'color')
    color_low.text = '7fff0000'  # 반투명 파란색
    fill_low = SubElement(poly_style_low, 'fill')
    fill_low.text = '1'
    outline_low = SubElement(poly_style_low, 'outline')
    outline_low.text = '1'
    
    style_mid = SubElement(document, 'Style')
    style_mid.set('id', 'buildingMid')
    line_style_mid = SubElement(style_mid, 'LineStyle')
    color_mid_line = SubElement(line_style_mid, 'color')
    color_mid_line.text = 'ff0000ff'  # 빨간색 외곽선
    width_mid = SubElement(line_style_mid, 'width')
    width_mid.text = '1.0'
    poly_style_mid = SubElement(style_mid, 'PolyStyle')
    color_mid = SubElement(poly_style_mid, 'color')
    color_mid.text = '7f00ffff'  # 반투명 노란색
    fill_mid = SubElement(poly_style_mid, 'fill')
    fill_mid.text = '1'
    outline_mid = SubElement(poly_style_mid, 'outline')
    outline_mid.text = '1'
    
    style_high = SubElement(document, 'Style')
    style_high.set('id', 'buildingHigh')
    line_style_high = SubElement(style_high, 'LineStyle')
    color_high_line = SubElement(line_style_high, 'color')
    color_high_line.text = 'ff0000ff'  # 빨간색 외곽선
    width_high = SubElement(line_style_high, 'width')
    width_high.text = '1.5'
    poly_style_high = SubElement(style_high, 'PolyStyle')
    color_high = SubElement(poly_style_high, 'color')
    color_high.text = '7f0000ff'  # 반투명 빨간색
    fill_high = SubElement(poly_style_high, 'fill')
    fill_high.text = '1'
    outline_high = SubElement(poly_style_high, 'outline')
    outline_high.text = '1'
    
    # GeoJSON 파일들 읽기
    geojson_files = glob.glob(input_pattern)
    print(f"총 {len(geojson_files)}개의 GeoJSON 파일을 처리합니다...")
    
    building_count = 0
    height_stats = {'low': 0, 'mid': 0, 'high': 0, 'unknown': 0}
    
    for idx, geojson_file in enumerate(geojson_files):
        if idx % 1000 == 0:
            print(f"진행 중... {idx}/{len(geojson_files)}")
        
        try:
            with open(geojson_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 건물 높이 추출
            height_str = data.get('properties', {}).get('height', '0')
            try:
                height = float(height_str) if height_str else 0
            except (ValueError, TypeError):
                height = 0
            
            # 건물 이름
            building_name = data.get('properties', {}).get('bld_nm', '')
            
            # 좌표 추출
            geometry = data.get('geometry', {})
            if geometry.get('type') != 'MultiPolygon':
                continue
            
            coordinates = geometry.get('coordinates', [])
            if not coordinates:
                continue
            
            # 높이에 따른 스타일 선택
            if height < 20:
                style_url = '#buildingLow'
                height_stats['low'] += 1
            elif height < 50:
                style_url = '#buildingMid'
                height_stats['mid'] += 1
            elif height > 0:
                style_url = '#buildingHigh'
                height_stats['high'] += 1
            else:
                style_url = '#buildingLow'
                height_stats['unknown'] += 1
            
            # Placemark 생성
            placemark = SubElement(document, 'Placemark')
            
            # 이름 설정
            name_elem = SubElement(placemark, 'name')
            if building_name:
                name_elem.text = f"{building_name} ({height}m)"
            else:
                name_elem.text = f"Building {building_count + 1} ({height}m)"
            
            # 설명 추가
            description = SubElement(placemark, 'description')
            description.text = f"높이: {height}m"
            
            # 스타일 참조
            style_url_elem = SubElement(placemark, 'styleUrl')
            style_url_elem.text = style_url
            
            # Polygon 생성
            polygon = SubElement(placemark, 'Polygon')
            extrude = SubElement(polygon, 'extrude')
            extrude.text = '1'
            altitude_mode = SubElement(polygon, 'altitudeMode')
            altitude_mode.text = 'relativeToGround'
            
            outer_boundary = SubElement(polygon, 'outerBoundaryIs')
            linear_ring = SubElement(outer_boundary, 'LinearRing')
            coords = SubElement(linear_ring, 'coordinates')
            
            # 좌표 변환 (높이 포함)
            if coordinates and coordinates[0] and coordinates[0][0]:
                ring = coordinates[0][0]
                kml_coords = []
                for coord in ring:
                    lon, lat = coord[0], coord[1]
                    kml_coords.append(f"{lon},{lat},{height}")
                coords.text = "\n              " + "\n              ".join(kml_coords)
            
            building_count += 1
            
        except Exception as e:
            print(f"파일 처리 오류 {geojson_file}: {e}")
            continue
    
    print(f"\n총 {building_count}개의 건물을 변환했습니다.")
    print(f"높이 통계:")
    print(f"  - 낮은 건물 (< 20m): {height_stats['low']}개")
    print(f"  - 중간 건물 (20-50m): {height_stats['mid']}개")
    print(f"  - 높은 건물 (> 50m): {height_stats['high']}개")
    print(f"  - 높이 미상: {height_stats['unknown']}개")
    
    # XML을 문자열로 변환하고 포맷팅
    xml_string = tostring(kml, encoding='utf-8')
    dom = minidom.parseString(xml_string)
    pretty_xml = dom.toprettyxml(indent='  ', encoding='utf-8')
    
    # XML 선언 중복 제거
    pretty_xml = b'\n'.join([line for line in pretty_xml.split(b'\n') if line.strip()])
    
    # 파일 저장
    with open(output_file, 'wb') as f:
        f.write(pretty_xml)
    
    print(f"\nKML 파일이 생성되었습니다: {output_file}")
    print(f"파일 크기: {os.path.getsize(output_file) / (1024*1024):.2f} MB")

if __name__ == '__main__':
    input_pattern = 'bld_*.geojson'
    output_file = 'cheongna_buildings_5km.kml'
    
    print("청라시티타워 인근 건물 GeoJSON → KML 변환 시작")
    print("=" * 60)
    
    create_kml_from_geojsons(input_pattern, output_file)
    
    print("=" * 60)
    print("변환 완료!")
