#!/usr/bin/env python3
"""
Convert Jeju Airport obstacle JSON data to GeoPackage format for OLS engine
"""

import json
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point
from pathlib import Path

def create_obstacles_geopackage():
    """Convert JSON obstacles to GeoPackage format"""
    
    # Load obstacle data
    obstacles_file = Path('/home/user/webapp/jeju_airport/data/jeju_obstacles.json')
    with open(obstacles_file, 'r', encoding='utf-8') as f:
        obstacles = json.load(f)
    
    print(f"Loading {len(obstacles)} obstacles from JSON...")
    
    # Create obstacles layer with proper column names expected by OLS engine
    obstacles_data = []
    for obs in obstacles:
        obstacles_data.append({
            'obj_id': obs['id'],  # Required by OLS engine
            'obs_type': obs['type'],
            'top_elev_m': obs['height_m'] + obs.get('ground_elevation_m', 0),  # Total elevation
            'height_m': obs['height_m'],  # Object height
            'ground_elev_m': obs.get('ground_elevation_m', 0),
            'description': obs['description'],
            'geometry': Point(obs['x_coord'], obs['y_coord'])
        })
    
    # Create GeoDataFrame
    obstacles_gdf = gpd.GeoDataFrame(obstacles_data, crs='EPSG:5186')
    
    print(f"✓ Created obstacles GeoDataFrame with {len(obstacles_gdf)} features")
    print(f"  - CRS: {obstacles_gdf.crs}")
    print(f"  - Columns: {list(obstacles_gdf.columns)}")
    
    # Create runway axes layer
    runway_axes_data = [{
        'rwy_id': 'RKPC-31',
        'thr_x': 333019.74,
        'thr_y': 1263014.45,
        'thr_elev_m': 36.0,
        'bearing_deg': 310.0,
        'geometry': Point(333019.74, 1263014.45)
    }]
    
    runway_axes_gdf = gpd.GeoDataFrame(runway_axes_data, crs='EPSG:5186')
    
    print(f"✓ Created runway_axes GeoDataFrame with {len(runway_axes_gdf)} features")
    
    # Save to GeoPackage
    output_file = Path('/home/user/webapp/jeju_airport/data/jeju_project.gpkg')
    
    obstacles_gdf.to_file(output_file, layer='obstacles', driver='GPKG')
    runway_axes_gdf.to_file(output_file, layer='runway_axes', driver='GPKG', mode='a')
    
    print(f"✓ Saved GeoPackage to: {output_file}")
    
    # Verify the file
    print("\nVerifying GeoPackage layers:")
    try:
        import fiona
        layers = fiona.listlayers(str(output_file))
        print(f"  Available layers: {layers}")
        
        for layer in layers:
            with fiona.open(str(output_file), layer=layer) as src:
                print(f"  - {layer}: {len(src)} features, CRS: {src.crs}")
    except Exception as e:
        print(f"  ⚠️ Could not verify with fiona: {e}")
    
    return output_file

def main():
    """Create GeoPackage for Jeju Airport analysis"""
    
    print("="*60)
    print("CREATING JEJU AIRPORT GEOPACKAGE FOR OLS ANALYSIS")
    print("="*60)
    
    try:
        geopackage_file = create_obstacles_geopackage()
        print(f"\n🎉 GeoPackage created successfully!")
        print(f"📁 File location: {geopackage_file}")
        print("\nReady for OLS analysis with:")
        print(f"  --input {geopackage_file}")
        print(f"  --config /home/user/webapp/jeju_airport/config/jeju_ols_config.json")
        
        return geopackage_file
        
    except Exception as e:
        print(f"\n💥 Failed to create GeoPackage: {e}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == '__main__':
    geopackage_file = main()