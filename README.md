# 🦾 Capstone (캡스톤): VLM 및 RGB-D 기반 뇌졸중 상지 재활 평가 자동화 시스템

[![Capstone Project](https://img.shields.io/badge/프로젝트-캡스톤_디자인-blue.svg)](./INDEX.md)
[![Latest Plan](https://img.shields.io/badge/연구계획서-v13.2_최종본-brightgreen.svg)](./capstone/실험계획서_v13.2_최종본.md)
[![Clinical Standard](https://img.shields.io/badge/임상_표준-ARAT_&_FMA--UE-purple.svg)](./outputs/채점자_룰북_ARAT_기준.md)
[![Repository](https://img.shields.io/badge/GitHub-passtock/casstone-darkblue.svg)](https://github.com/passtock/casstone)

인텔 리얼센스(Intel RealSense D455) RGB-D 카메라와 시각-언어 모델(Vision-Language Model, VLM), 그리고 MediaPipe 3D 핸드 트래킹을 융합하여 **뇌졸중 환자의 상지 운동 기능 평가(ARAT / FMA-UE)를 무구속·비침습적으로 자동 채점 및 정량화**하는 캡스톤 디자인 연구 프로젝트 저장소입니다.

---

## 🧭 빠른 바로가기 (Quick Links)

> 💡 **"지금 어디를 봐야 할지 모를 때"**: 전체 문서의 상세 지도가 담긴 [`INDEX.md`](./INDEX.md)를 먼저 확인하세요.

| 목적 | 핵심 문서 바로가기 | 설명 |
|:---:|:---|:---|
| 📋 **최신 연구계획서** | [`capstone/실험계획서_v13.2_최종본.md`](./capstone/실험계획서_v13.2_최종본.md) | **현재 연구의 최종 정본 (v13.2)** |
| 💡 **계획서 요약본** | [`outputs/실험계획서_최종본_쉬운버전.md`](./outputs/실험계획서_최종본_쉬운버전.md) | 교수님 면담 및 브리핑용 쉬운 해설본 |
| 🧑‍⚕️ **임상 채점 룰북** | [`outputs/채점자_룰북_ARAT_기준.md`](./outputs/채점자_룰북_ARAT_기준.md) | ARAT 표준 임상 평가 룰북 (등받이 이탈 감점 포함) |
| 📸 **촬영 가이드** | [`capstone/사진_촬영_가이드.md`](./capstone/사진_촬영_가이드.md) | 카메라 설치 구도 및 환자 2초 정지 기준선 매뉴얼 |
| 💻 **최신 검사 코드** | [`experiments/v13/qv13.py`](./experiments/v13/qv13.py) | v13 규칙 1:1 파이썬 구현체 (오라클 25 PASS) |

---

## 🔬 프로젝트 핵심 개요

1. **임상적 배경**:
   - 뇌졸중 환자의 상지 재활 평가 척도인 ARAT(Action Research Arm Test)와 FMA-UE는 치료사의 수기 평가에 의존하여 평가자 간 편차가 발생하고 시간이 많이 소요됩니다.
2. **기술적 해결책**:
   - **RGB-D 깊이 카메라 (Intel RealSense D455)**: 환자의 3차원 공간 움직임, 어깨 보상 운동(등받이 이탈), 파지 궤적 정밀 계측.
   - **VLM (Vision-Language Model)**: 동작의 질적 특성(부드러움, 떨림, 파지 실패 패턴)을 임상 지침에 맞추어 추론 및 피드백 생성.
   - **3D 프린팅 ARAT 키트**: 임상 표준 규격(37cm 선반, 블록 등)을 정밀 재현하여 표준화된 실험 환경 제공.

---

## 📂 폴더 구조 및 구성 (Directory Architecture)

```
c:/Users/passp/Desktop/univercity/4-2/캡스톤/
│
├── 🧭 INDEX.md                                # 워크스페이스 마스터 인덱스 (전체 길라잡이)
├── 📖 README.md                               # 본 저장소 메인 소개 문서
├── 📝 CHANGELOG.md                            # 버전별 연구계획 변경 이력
│
├── 📁 capstone/                               # 메인 연구 문서 및 실시간 파이프라인
│   ├── 📄 실험계획서_v13.2_최종본.md           # 현재 연구의 최종 확정 계획서
│   ├── 📄 사진_촬영_가이드.md                 # 카메라 설치 구도 매뉴얼
│   ├── 📁 00_발표자료_모음/                   # PPTX 발표 슬라이드 아카이브
│   ├── 📁 01_분석보고서_6종/                  # 1-a ~ 3-b 기술 분석 보고서
│   ├── 📁 05_웹캠_핸드트래킹_테스트/           # D455 + MediaPipe 트래킹 파이프라인
│   └── 📁 06_VLM_재활평가_테스트/             # VLM 평가 스크립트 및 14프레임 추출기
│
├── 📁 outputs/                                # 학술 보고서 및 임상 검증 자료
│   ├── 📄 실험계획서_최종본_쉬운버전.md         # 교수님 면담용 요약본
│   ├── 📄 채점자_룰북_ARAT_기준.md            # ARAT 표준 임상 평가 룰북
│   ├── 📁 01-조사문헌/                        # 논문 48편 정밀 분석 보고서 및 증거맵
│   └── 📁 03-검증/                            # 계획서 엄중 검토 및 변경 대조표
│
├── 📁 experiments/                            # 알고리즘 및 실험 파이썬 코드
│   ├── 📁 v13/                                # 최신 품질 판정기 (qv13.py)
│   ├── 📁 analysis/                           # 부트스트랩 통계 분석 하네스
│   └── 📁 vlm/                                # VLM 프롬프트 생성 및 실행기
│
├── 📁 arat_3d_kit/                            # 3D 프린터용 ARAT 37cm 선반 STL 모델
└── 📁 00_발표_및_랩미팅자료/                   # 대외 발표 PPTX 및 랩미팅 보고서
```

---

<div align="center">
  <b>🦾 Capstone: Vision-Language Models & RGB-D Kinematics for Stroke Rehabilitation Assessment</b><br>
  Designed for Precision Clinical Evaluation & Automated Functional Scoring.
</div>
