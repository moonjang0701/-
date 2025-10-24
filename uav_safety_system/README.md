# UAV 공역 안전성 측정 시스템

## 📋 프로젝트 개요

무인항공기(UAV) 운영을 위한 **공역 안전성 측정 및 경로 계획 시스템**입니다. 
UAV의 위치 불확실성을 고려한 안전 봉투(Safety Envelope) 계산, 충돌 확률 분석, 
그리고 안전장(Safety Field) 기반 경로 최적화 기능을 제공합니다.

### 주요 기능

- ✈️ **안전 봉투(Safety Envelope) 계산**: UAV의 기동 능력과 응답 시간을 고려한 보호 공역 산출
- 📊 **충돌 확률 분석**: 가우시안 위치 불확실성 기반 충돌 확률 계산
- 🗺️ **안전장(Safety Field) 생성**: 3D 공역에 대한 안전도 분포 계산
- 🛤️ **경로 최적화**: 안전장 기반 최적 경로 계획
- 📈 **시각화**: 안전 봉투, 안전장, 경로 등의 3D 시각화

### 이론적 배경

본 시스템은 다음 논문의 수학적 모델을 구현합니다:

- **안전 봉투**: UAV의 최대 속도와 응답 시간을 고려한 3D 타원체 모델
- **위치 불확실성**: Along-track 및 Cross-track 방향의 시간 종속적 분산 성장 모델
- **충돌 확률**: 다변량 정규 분포를 이용한 확률적 안전성 평가
- **안전장**: 공역 전체에 대한 안전도 분포 및 경로 최적화

## 🚀 시작하기

### 필요 조건

- Python 3.9 이상
- pip 또는 conda 패키지 관리자

### 설치

1. **저장소 클론 (또는 다운로드)**
```bash
cd /home/user/webapp/uav_safety_system
```

2. **가상 환경 생성 (권장)**
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 또는
venv\Scripts\activate  # Windows
```

3. **의존성 패키지 설치**
```bash
pip install -r requirements.txt
```

## 📖 사용 방법

### 1. 설정 파일 수정

`config.yaml` 파일에서 UAV 성능, 공역 범위, 시뮬레이션 파라미터 등을 설정합니다.

```yaml
uav_performance:
  Vf: 5.0          # 최대 전방 속도 (km/min)
  Vb: 2.0          # 최대 후방 속도 (km/min)
  # ... 기타 파라미터

trajectory:
  start_position: [50, 0, 5]    # 시작 위치 (km)
  end_position: [50, 100, 5]    # 목표 위치 (km)
  # ... 기타 경로 설정
```

### 2. 시스템 실행

```bash
# 기본 실행
python main.py

# 사용자 정의 설정 파일 사용
python main.py --config my_config.yaml

# 결과 디렉토리 지정
python main.py --output-dir my_results/
```

### 3. 결과 확인

실행 후 `results/` 디렉토리에 다음 파일들이 생성됩니다:

- `safety_envelope_*.png`: 안전 봉투 시각화
- `safety_field_*.png`: 안전장 분포 시각화
- `trajectory_*.png`: 계획된 경로 시각화
- `collision_probability.csv`: 충돌 확률 데이터
- `waypoints.csv`: 경로점 좌표 데이터

## 📁 프로젝트 구조

```
uav_safety_system/
├── core/                          # 핵심 알고리즘 모듈
│   ├── __init__.py
│   ├── safety_envelope.py         # 안전 봉투 계산
│   ├── conflict_probability.py    # 충돌 확률 분석
│   ├── safety_field.py            # 안전장 생성
│   └── trajectory_planning.py     # 경로 계획
├── utils/                         # 유틸리티 함수
│   ├── __init__.py
│   └── math_helpers.py            # 수학적 보조 함수
├── visualization/                 # 시각화 모듈
│   ├── __init__.py
│   └── plotting.py                # 플로팅 함수
├── tests/                         # 단위 테스트
│   ├── __init__.py
│   ├── test_safety_envelope.py
│   └── test_conflict_probability.py
├── config.yaml                    # 설정 파일
├── requirements.txt               # 의존성 패키지
├── README.md                      # 프로젝트 문서
└── main.py                        # 메인 실행 파일
```

## 🧪 테스트

단위 테스트 실행:

```bash
# 모든 테스트 실행
pytest

# 커버리지 포함 테스트
pytest --cov=core --cov=utils --cov-report=html

# 특정 테스트 파일만 실행
pytest tests/test_safety_envelope.py
```

## 📊 주요 수식 및 알고리즘

### 안전 봉투 (Safety Envelope)

UAV의 기동 능력과 응답 시간을 고려한 타원체 형태의 보호 공역:

```
SE = {(x, y, z) | (x/Rx)² + (y/Ry)² + (z_pos/Rz_up)² ≤ 1 or (z_neg/Rz_down)² ≤ 1}
```

여기서:
- Rx = Vf × Δt (전방) 또는 Vb × Δt (후방)
- Ry = Vl × Δt (횡방향)
- Rz_up = Va × Δt (상승)
- Rz_down = Vd × Δt (하강)

### 충돌 확률 (Conflict Probability)

가우시안 위치 불확실성 기반:

```
P_conflict = P(UAV ∈ Obstacle | μ, Σ)
```

공분산 행렬:
```
Σ = diag(σ₁², σ₂², σ₃²)
σ₁ = r_A1 × √Δt  (along-track)
σ₂ = r_A2 × √Δt  (cross-track)
σ₃ = r_A3 × √Δt  (vertical)
```

### 안전장 (Safety Field)

공역 내 각 점의 안전도:

```
SF(x, y, z) = min_obstacles(distance(point, obstacle) / safety_envelope_radius)
```

## 🤝 기여

버그 리포트, 기능 제안, 코드 기여를 환영합니다!

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 라이선스

MIT License - 자세한 내용은 LICENSE 파일 참조

## 📧 연락처

프로젝트 관련 문의: [이메일 주소]

## 🙏 참고 문헌

본 시스템은 다음 연구를 기반으로 구현되었습니다:

- [논문 제목 및 저자]
- [UAV 안전성 관련 표준 문서]
- [기타 참고 문헌]

## 📈 로드맵

- [x] 안전 봉투 계산 모듈
- [x] 충돌 확률 분석 모듈
- [x] 안전장 생성 모듈
- [x] 경로 계획 모듈
- [ ] 실시간 장애물 회피
- [ ] 다중 UAV 협조 제어
- [ ] 웹 기반 GUI
- [ ] ROS 통합

---

**Version**: 1.0.0  
**Last Updated**: 2024-10-24
