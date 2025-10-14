#!/usr/bin/env python3
"""
Run OLS penetration analysis for Jeju Airport Runway 31
"""

import sys
import os
from pathlib import Path
import json

# Add src directory to Python path
webapp_dir = Path(__file__).parent.parent
src_dir = webapp_dir / 'src'
sys.path.insert(0, str(src_dir))

try:
    from ols_engine import OLSEngine
    from ols_engine.core.data_loader import DataLoader
    from ols_engine.core.config_loader import ConfigLoader
    print("✓ Successfully imported OLS engine modules")
except ImportError as e:
    print(f"❌ Failed to import OLS engine modules: {e}")
    print("Available modules in src:")
    if src_dir.exists():
        for item in src_dir.iterdir():
            print(f"  - {item.name}")
    sys.exit(1)

def load_jeju_obstacles():
    """Load Jeju Airport obstacle data"""
    obstacles_file = Path('/home/user/webapp/jeju_airport/data/jeju_obstacles.json')
    
    with open(obstacles_file, 'r', encoding='utf-8') as f:
        obstacles = json.load(f)
    
    print(f"✓ Loaded {len(obstacles)} obstacles from {obstacles_file}")
    return obstacles

def run_jeju_analysis():
    """Run OLS penetration analysis for Jeju Airport"""
    
    config_file = Path('/home/user/webapp/jeju_airport/config/jeju_ols_config.json')
    output_dir = Path('/home/user/webapp/jeju_airport/outputs')
    
    print("="*60)
    print("JEJU AIRPORT RUNWAY 31 - OLS PENETRATION ANALYSIS")
    print("="*60)
    
    try:
        # Load configuration
        print(f"Loading configuration from: {config_file}")
        config_loader = ConfigLoader()
        config = config_loader.load_config(str(config_file))
        print(f"✓ Configuration loaded successfully")
        print(f"  - CRS: EPSG:{config['crs_epsg']}")
        print(f"  - ARP Elevation: {config['arp_elev_m']}m")
        print(f"  - Runways: {len(config['runways'])}")
        
        # Load obstacles
        obstacles = load_jeju_obstacles()
        
        # Initialize OLS engine
        print("\nInitializing OLS engine...")
        engine = OLSEngine(config)
        
        # Add obstacles to engine
        print("Adding obstacles to analysis...")
        for obstacle in obstacles:
            engine.add_obstacle(
                obs_id=obstacle['id'],
                x=obstacle['x_coord'],
                y=obstacle['y_coord'],
                height=obstacle['height_m'],
                ground_elev=obstacle.get('ground_elevation_m', 0)
            )
        
        print(f"✓ Added {len(obstacles)} obstacles to analysis")
        
        # Run penetration analysis
        print("\nRunning OLS penetration analysis...")
        results = engine.run_analysis()
        
        # Create output directory
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save results
        results_file = output_dir / 'jeju_penetration_results.json'
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"✓ Analysis complete! Results saved to: {results_file}")
        
        # Display summary
        penetrations = results.get('penetrations', [])
        print("\n" + "="*60)
        print("ANALYSIS RESULTS SUMMARY")
        print("="*60)
        print(f"Total obstacles analyzed: {len(obstacles)}")
        print(f"Total penetrations found: {len(penetrations)}")
        print(f"Penetration rate: {len(penetrations)/len(obstacles)*100:.1f}%")
        
        if penetrations:
            print(f"\nPenetration details:")
            surface_counts = {}
            for pen in penetrations:
                surface = pen.get('surface_type', 'unknown')
                surface_counts[surface] = surface_counts.get(surface, 0) + 1
            
            for surface, count in surface_counts.items():
                print(f"  - {surface}: {count} penetrations")
            
            # Show worst penetrations
            sorted_penetrations = sorted(penetrations, key=lambda x: x.get('penetration_height', 0), reverse=True)
            print(f"\nWorst penetrations (top 5):")
            for i, pen in enumerate(sorted_penetrations[:5]):
                obs_id = pen.get('obstacle_id', 'unknown')
                surface = pen.get('surface_type', 'unknown')
                pen_height = pen.get('penetration_height', 0)
                print(f"  {i+1}. {obs_id} - {surface} surface: {pen_height:.2f}m")
        
        print("="*60)
        
        return results
        
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        import traceback
        traceback.print_exc()
        raise

def main():
    """Main function"""
    try:
        results = run_jeju_analysis()
        print("\n🎉 Jeju Airport OLS analysis completed successfully!")
        return results
    except Exception as e:
        print(f"\n💥 Analysis failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    results = main()