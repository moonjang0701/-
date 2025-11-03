#!/bin/bash
# UAV 안전성 측정 - 다양한 시나리오 실행 스크립트

echo "========================================"
echo "UAV 공역 안전성 측정 시스템"
echo "커스텀 시나리오 자동 실행"
echo "========================================"
echo ""

cd /home/user/webapp/uav_safety_system

# 시나리오 1: 저밀도 (30대)
echo "시나리오 1: 저밀도 (30 UAVs)..."
python3 main.py --scenario custom \
    --config config_custom_150uavs_fast.yaml \
    --num_uavs 30 \
    --parallel

echo ""
echo "시나리오 1 완료!"
echo ""

# 시나리오 2: 중밀도 (75대)
echo "시나리오 2: 중밀도 (75 UAVs)..."
python3 main.py --scenario custom \
    --config config_custom_150uavs_fast.yaml \
    --num_uavs 75 \
    --parallel

echo ""
echo "시나리오 2 완료!"
echo ""

# 시나리오 3: 고밀도 (150대)
echo "시나리오 3: 고밀도 (150 UAVs)..."
python3 main.py --scenario custom \
    --config config_custom_150uavs_fast.yaml \
    --num_uavs 150 \
    --parallel

echo ""
echo "시나리오 3 완료!"
echo ""

echo "========================================"
echo "모든 시나리오 실행 완료!"
echo "결과 위치: results/"
echo "========================================"
