#!/usr/bin/env python3
"""
Parse Jeju Airport CSV data into OLS configuration format
Based on user-provided data structure with EPSG:5186 coordinate system
"""

import csv
import json
import os
from pathlib import Path

def parse_reference_points(csv_file):
    """Parse 기준점.csv to extract runway and ARP coordinates"""
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        row = next(reader)
        
        # Parse runway start point
        runway_start = row['활주로 시점'].strip().split()
        runway_start = [float(runway_start[0]), float(runway_start[1])]
        
        # Parse runway end point
        runway_end = row['활주로 종점'].strip().split()
        runway_end = [float(runway_end[0]), float(runway_end[1])]
        
        # Parse ARP coordinates
        arp_coords = row['ARP 좌표'].strip().split()
        arp_coords = [float(arp_coords[0]), float(arp_coords[1])]
        
    return {
        'runway_start': runway_start,
        'runway_end': runway_end,
        'arp_coordinates': arp_coords
    }

def parse_surface_properties(csv_file):
    """Parse 표면속성표.csv to extract OLS surface parameters"""
    surfaces = {}
    
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            surface_type = row['표면유형'].strip()
            
            # Parse parameters based on surface type
            surface_data = {}
            
            # Common parameters
            if row['기준표고']:
                surface_data['anchor_elevation'] = float(row['기준표고'])
            
            if row['축방위각']:
                surface_data['axis_azimuth'] = float(row['축방위각'])
            
            if row['경사율']:
                surface_data['slope'] = float(row['경사율'])
            
            if row['길이']:
                surface_data['length'] = float(row['길이'])
            
            if row['폭']:
                surface_data['width'] = float(row['폭'])
            
            if row['확산율']:
                surface_data['divergence'] = float(row['확산율'])
            
            if row['높이제한']:
                surface_data['height_limit'] = float(row['높이제한'])
            
            # Map Korean surface types to English
            surface_mapping = {
                '접근표면': 'approach',
                '이륙표면': 'takeoff', 
                '전이표면': 'transitional',
                '내수평표면': 'inner_horizontal',
                '원추표면': 'conical'
            }
            
            english_type = surface_mapping.get(surface_type, surface_type.lower())
            surfaces[english_type] = surface_data
    
    return surfaces

def create_runway_config(reference_points, surface_properties):
    """Create runway configuration in OLS engine format"""
    
    # Calculate runway length and bearing from start/end points
    import math
    
    start_x, start_y = reference_points['runway_start']
    end_x, end_y = reference_points['runway_end']
    
    # Calculate runway length
    runway_length = math.sqrt((end_x - start_x)**2 + (end_y - start_y)**2)
    
    # Calculate runway bearing (azimuth from start to end)
    bearing = math.degrees(math.atan2(end_x - start_x, end_y - start_y))
    if bearing < 0:
        bearing += 360
    
    # Create runway configuration
    runway_config = {
        'runway_id': 'RKPC_RWY31',
        'airport_code': 'RKPC',
        'runway_name': 'Runway 31',
        'coordinates': {
            'start_point': reference_points['runway_start'],
            'end_point': reference_points['runway_end'],
            'arp': reference_points['arp_coordinates']
        },
        'runway_properties': {
            'length': round(runway_length, 2),
            'bearing': round(bearing, 1),
            'elevation': surface_properties.get('approach', {}).get('anchor_elevation', 36)
        },
        'coordinate_system': 'EPSG:5186',
        'surfaces': {}
    }
    
    # Add surface configurations
    for surface_type, properties in surface_properties.items():
        if surface_type in ['approach', 'takeoff', 'transitional', 'inner_horizontal', 'conical']:
            runway_config['surfaces'][surface_type] = properties
    
    return runway_config

def main():
    """Main parsing function"""
    data_dir = Path('/home/user/webapp/jeju_airport/data')
    config_dir = Path('/home/user/webapp/jeju_airport/config')
    
    # Parse CSV files
    reference_file = data_dir / '기준점.csv'
    surface_file = data_dir / '표면속성표.csv'
    
    print("Parsing Jeju Airport CSV data...")
    
    try:
        # Parse reference points
        reference_points = parse_reference_points(reference_file)
        print(f"✓ Parsed reference points: {reference_points}")
        
        # Parse surface properties
        surface_properties = parse_surface_properties(surface_file)
        print(f"✓ Parsed surface properties: {surface_properties}")
        
        # Create runway configuration
        runway_config = create_runway_config(reference_points, surface_properties)
        print(f"✓ Created runway configuration for {runway_config['runway_id']}")
        
        # Save configuration
        config_file = config_dir / 'jeju_runway31_config.json'
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(runway_config, f, indent=2, ensure_ascii=False)
        
        print(f"✓ Saved configuration to: {config_file}")
        
        # Display summary
        print("\n" + "="*60)
        print("JEJU AIRPORT RUNWAY 31 CONFIGURATION SUMMARY")
        print("="*60)
        print(f"Airport Code: {runway_config['airport_code']}")
        print(f"Runway ID: {runway_config['runway_id']}")
        print(f"Coordinate System: {runway_config['coordinate_system']}")
        print(f"Runway Length: {runway_config['runway_properties']['length']:.2f}m")
        print(f"Runway Bearing: {runway_config['runway_properties']['bearing']:.1f}°")
        print(f"Runway Elevation: {runway_config['runway_properties']['elevation']}m")
        print(f"ARP Coordinates: {runway_config['coordinates']['arp']}")
        print(f"Surface Types: {', '.join(runway_config['surfaces'].keys())}")
        print("="*60)
        
        return runway_config
        
    except Exception as e:
        print(f"❌ Error parsing CSV data: {e}")
        raise

if __name__ == '__main__':
    config = main()