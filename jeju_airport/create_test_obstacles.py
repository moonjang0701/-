#!/usr/bin/env python3
"""
Create test obstacle data for Jeju Airport OLS analysis
"""

import json
import random
import math
from pathlib import Path

def create_test_obstacles():
    """Create sample obstacles around Jeju Airport runway 31"""
    
    # Runway center coordinates (approximate)
    runway_center_x = 333044.0
    runway_center_y = 1262934.0
    
    obstacles = []
    obstacle_types = ['Building', 'Tower', 'Tree', 'Antenna', 'Structure']
    
    # Create obstacles in different zones around the airport
    for i in range(150):
        # Generate random position within 10km of runway
        angle = random.uniform(0, 2 * math.pi)
        distance = random.uniform(500, 10000)  # 500m to 10km from runway
        
        x = runway_center_x + distance * math.cos(angle)
        y = runway_center_y + distance * math.sin(angle)
        
        # Generate realistic heights based on distance from runway
        if distance < 2000:
            # Closer to runway - lower heights
            height = random.uniform(5, 50)
        elif distance < 5000:
            # Medium distance - medium heights
            height = random.uniform(10, 80)
        else:
            # Further away - can be taller
            height = random.uniform(15, 120)
        
        obstacle = {
            'id': f'JEJU_OBS_{i+1:03d}',
            'type': random.choice(obstacle_types),
            'x_coord': round(x, 2),
            'y_coord': round(y, 2),
            'height_m': round(height, 1),
            'ground_elevation_m': random.uniform(0, 50),  # Jeju terrain elevation
            'description': f'Test obstacle {i+1} for Jeju Airport'
        }
        
        obstacles.append(obstacle)
    
    return obstacles

def save_obstacles_json(obstacles, output_file):
    """Save obstacles as JSON file"""
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(obstacles, f, indent=2, ensure_ascii=False)
    
def save_obstacles_csv(obstacles, output_file):
    """Save obstacles as CSV file"""
    import csv
    
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['id', 'type', 'x_coord', 'y_coord', 'height_m', 'ground_elevation_m', 'description']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(obstacles)

def main():
    """Generate test obstacle data for Jeju Airport"""
    
    data_dir = Path('/home/user/webapp/jeju_airport/data')
    
    print("Generating test obstacles for Jeju Airport...")
    
    # Create test obstacles
    obstacles = create_test_obstacles()
    print(f"✓ Generated {len(obstacles)} test obstacles")
    
    # Save in both formats
    json_file = data_dir / 'jeju_obstacles.json'
    csv_file = data_dir / 'jeju_obstacles.csv'
    
    save_obstacles_json(obstacles, json_file)
    save_obstacles_csv(obstacles, csv_file)
    
    print(f"✓ Saved obstacles to: {json_file}")
    print(f"✓ Saved obstacles to: {csv_file}")
    
    # Display summary
    print("\n" + "="*50)
    print("JEJU AIRPORT TEST OBSTACLES SUMMARY")
    print("="*50)
    print(f"Total obstacles: {len(obstacles)}")
    
    # Statistics
    heights = [obs['height_m'] for obs in obstacles]
    distances = []
    
    runway_x, runway_y = 333044.0, 1262934.0
    for obs in obstacles:
        dist = math.sqrt((obs['x_coord'] - runway_x)**2 + (obs['y_coord'] - runway_y)**2)
        distances.append(dist)
    
    print(f"Height range: {min(heights):.1f}m - {max(heights):.1f}m")
    print(f"Distance range: {min(distances):.0f}m - {max(distances):.0f}m")
    print(f"Average height: {sum(heights)/len(heights):.1f}m")
    print(f"Average distance: {sum(distances)/len(distances):.0f}m")
    print("="*50)
    
    return obstacles

if __name__ == '__main__':
    obstacles = main()