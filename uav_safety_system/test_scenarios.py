"""
다양한 시나리오 테스트

시나리오:
1. 시간당 10대 (저밀도)
2. 시간당 20대 (중밀도) - 기본
3. 시간당 30대 (고밀도)
4. 안전 거리 변경 (30m, 50m, 100m)
"""

import numpy as np
from monte_carlo_simulator import MonteCarloSimulator

def test_density_scenarios():
    """밀도별 시나리오 테스트"""
    
    print("=" * 80)
    print("시나리오 테스트: UAV 밀도 변화")
    print("=" * 80)
    print()
    
    scenarios = [
        {'uavs_per_hour': 10, 'name': '저밀도 (시간당 10대)'},
        {'uavs_per_hour': 20, 'name': '중밀도 (시간당 20대)'},
        {'uavs_per_hour': 30, 'name': '고밀도 (시간당 30대)'},
    ]
    
    simulator = MonteCarloSimulator(
        airspace_size=(1.5, 0.9, 0.15),
        safe_distance=0.05,  # 50m
        gps_noise_std=0.005
    )
    
    results_table = []
    
    for scenario in scenarios:
        print(f"테스트 중: {scenario['name']}...")
        
        results = simulator.run_monte_carlo(
            n_trials=500,  # 500번으로 빠르게
            total_hours=8,
            uavs_per_hour=scenario['uavs_per_hour'],
            verbose=False
        )
        
        results_table.append({
            'name': scenario['name'],
            'uavs_per_hour': scenario['uavs_per_hour'],
            'total_uavs': results['total_uavs'],
            'collision_prob': results['collision_probability'] * 100,
            'avg_active': results['avg_max_active_uavs']
        })
        
        print(f"  충돌 확률: {results['collision_probability']*100:.2f}%")
        print(f"  평균 동시 비행: {results['avg_max_active_uavs']:.1f}대")
        print()
    
    # 결과 테이블 출력
    print("=" * 80)
    print("결과 요약")
    print("=" * 80)
    print(f"{'시나리오':<20} {'시간당':<8} {'총 UAV':<10} {'충돌확률':<12} {'평균동시':<10}")
    print("-" * 80)
    for r in results_table:
        print(f"{r['name']:<20} {r['uavs_per_hour']:<8} {r['total_uavs']:<10} "
              f"{r['collision_prob']:>6.2f}%      {r['avg_active']:>4.1f}대")
    print("=" * 80)
    print()


def test_safe_distance_scenarios():
    """안전 거리별 시나리오 테스트"""
    
    print("=" * 80)
    print("시나리오 테스트: 안전 거리 변화")
    print("=" * 80)
    print()
    
    scenarios = [
        {'safe_distance': 0.03, 'name': '30m 안전 거리'},
        {'safe_distance': 0.05, 'name': '50m 안전 거리'},
        {'safe_distance': 0.10, 'name': '100m 안전 거리'},
    ]
    
    results_table = []
    
    for scenario in scenarios:
        print(f"테스트 중: {scenario['name']}...")
        
        simulator = MonteCarloSimulator(
            airspace_size=(1.5, 0.9, 0.15),
            safe_distance=scenario['safe_distance'],
            gps_noise_std=0.005
        )
        
        results = simulator.run_monte_carlo(
            n_trials=500,
            total_hours=8,
            uavs_per_hour=20,  # 고정
            verbose=False
        )
        
        results_table.append({
            'name': scenario['name'],
            'safe_distance': scenario['safe_distance'] * 1000,
            'collision_prob': results['collision_probability'] * 100,
            'avg_active': results['avg_max_active_uavs']
        })
        
        print(f"  충돌 확률: {results['collision_probability']*100:.2f}%")
        print()
    
    # 결과 테이블 출력
    print("=" * 80)
    print("결과 요약 (시간당 20대 고정)")
    print("=" * 80)
    print(f"{'시나리오':<20} {'안전거리':<12} {'충돌확률':<12} {'평균동시':<10}")
    print("-" * 80)
    for r in results_table:
        print(f"{r['name']:<20} {r['safe_distance']:>6.0f}m       "
              f"{r['collision_prob']:>6.2f}%      {r['avg_active']:>4.1f}대")
    print("=" * 80)
    print()


def test_realistic_scenario():
    """현실적인 안전 시나리오 찾기"""
    
    print("=" * 80)
    print("안전한 운영 시나리오 탐색 (목표: 충돌 확률 < 10%)")
    print("=" * 80)
    print()
    
    # 다양한 조합 테스트
    test_cases = [
        {'uavs': 5, 'safe_dist': 0.05, 'name': '시간당 5대, 50m'},
        {'uavs': 10, 'safe_dist': 0.05, 'name': '시간당 10대, 50m'},
        {'uavs': 10, 'safe_dist': 0.10, 'name': '시간당 10대, 100m'},
        {'uavs': 15, 'safe_dist': 0.10, 'name': '시간당 15대, 100m'},
    ]
    
    results_table = []
    
    for case in test_cases:
        print(f"테스트 중: {case['name']}...")
        
        simulator = MonteCarloSimulator(
            airspace_size=(1.5, 0.9, 0.15),
            safe_distance=case['safe_dist'],
            gps_noise_std=0.005
        )
        
        results = simulator.run_monte_carlo(
            n_trials=500,
            total_hours=8,
            uavs_per_hour=case['uavs'],
            verbose=False
        )
        
        collision_prob = results['collision_probability'] * 100
        is_safe = collision_prob < 10
        
        results_table.append({
            'name': case['name'],
            'collision_prob': collision_prob,
            'is_safe': is_safe,
            'avg_active': results['avg_max_active_uavs']
        })
        
        status = "✅ 안전" if is_safe else "⚠️  위험"
        print(f"  충돌 확률: {collision_prob:.2f}% {status}")
        print()
    
    # 결과 테이블 출력
    print("=" * 80)
    print("결과 요약 (안전 기준: 충돌 확률 < 10%)")
    print("=" * 80)
    print(f"{'시나리오':<25} {'충돌확률':<12} {'평균동시':<12} {'안전성'}")
    print("-" * 80)
    for r in results_table:
        status = "✅ 안전" if r['is_safe'] else "⚠️  위험"
        print(f"{r['name']:<25} {r['collision_prob']:>6.2f}%      "
              f"{r['avg_active']:>4.1f}대       {status}")
    print("=" * 80)
    print()


if __name__ == "__main__":
    # 1. 밀도별 테스트
    test_density_scenarios()
    
    # 2. 안전 거리별 테스트
    test_safe_distance_scenarios()
    
    # 3. 안전한 시나리오 찾기
    test_realistic_scenario()
    
    print("=" * 80)
    print("모든 시나리오 테스트 완료!")
    print("=" * 80)
