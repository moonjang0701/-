#!/usr/bin/env python3
"""
높이 필터를 적용하여 특정 높이 이상의 건물만 KML로 변환
"""

import json
import glob
import os
import sys
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom

def create_filtered_kml(input_pattern, output_file, min_height=50, center_lat=37.533053, center_lon=126.633973):
    """
    특정 높이 이상의 건물만 KML로 변환
    """
    # KML 루트 요소 생성
    kml = Element('kml')
    kml.set('xmlns', 'http://www.opengis.net/kml/2.2')
    
    document = SubElement(kml, 'Document')
    name = SubElement(document, 'name')
    name.text = f'Cheongna Buildings (>= {min_height}m)'
    
    # LookAt 설정
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
    range_elem.text = '2000'
    altitude = SubElement(lookat, 'altitude')
    altitude.text = '0'
    
    # 고층 건물 스타일
    style = SubElement(document, 'Style')
    style.set('id', 'highBuilding')
    line_style = SubElement(style, 'LineStyle')
    color_line = SubElement(line_style, 'color')
    color_line.text = 'ff0000ff'  # 빨간색 외곽선
    width = SubElement(line_style, 'width')
    width.text = '2.0'
    poly_style = SubElement(style, 'PolyStyle')
    color = SubElement(poly_style, 'color')
    color.text = '7f0000ff'  # 반투명 빨간색
    fill = SubElement(poly_style, 'fill')
    fill.text = '1'
    outline = SubElement(poly_style, 'outline')
    outline.text = '1'
    
    # GeoJSON 파일들 읽기
    geojson_files = glob.glob(input_pattern)
    print(f"총 {len(geojson_files)}개의 GeoJSON 파일을 검색합니다...")
    
    building_count = 0
    heights = []
    
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
            
            # 최소 높이 필터
            if height < min_height:
                continue
            
            heights.append(height)
            
            # 건물 이름
            building_name = data.get('properties', {}).get('bld_nm', '')
            
            # 좌표 추출
            geometry = data.get('geometry', {})
            if geometry.get('type') != 'MultiPolygon':
                continue
            
            coordinates = geometry.get('coordinates', [])
            if not coordinates:
                continue
            
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
            description.text = f"높이: {height}m\n파일: {os.path.basename(geojson_file)}"
            
            # 스타일 참조
            style_url_elem = SubElement(placemark, 'styleUrl')
            style_url_elem.text = '#highBuilding'
            
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
    
    print(f"\n총 {building_count}개의 건물을 변환했습니다. (>= {min_height}m)")
    if heights:
        print(f"높이 범위: {min(heights):.1f}m ~ {max(heights):.1f}m")
        print(f"평균 높이: {sum(heights)/len(heights):.1f}m")
    
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
    
    # 명령줄 인자로 최소 높이 지정 가능
    min_height = 50 if len(sys.argv) < 2 else float(sys.argv[1])
    output_file = f'cheongna_buildings_above_{int(min_height)}m.kml'
    
    print(f"건물 필터링: {min_height}m 이상")
    print("=" * 60)
    
    create_filtered_kml(input_pattern, output_file, min_height)
    
    print("=" * 60)
    print("변환 완료!")
