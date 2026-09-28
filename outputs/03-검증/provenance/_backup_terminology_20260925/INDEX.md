# 워크스페이스 인덱스

**작성일:** 2026-09-23
**목적:** 이 워크스페이스에 무엇이 어디 있는지 한 눈에 보이게 한다.

---

## 1. 지금 당장 봐야 할 문서 (우선순위 순)

| 순위 | 파일 | 무엇 | 용도 |
|---|---|---|---|
| **1** | `outputs/03-검증/provenance/citation-verification-report.md` | **인용 무결성 감사** — 깨진 DOI 25건, **오류귀속 8건·가짜 인용 10건** 발견 | 🔴 **먼저 읽기 (2026-09-25 신규)** |
| **2** | `outputs/03-검증/systematic-search-novelty-audit.md` | **신규성 감사** — 우리 연구가 정말 새로운지 검증. 이전 주장 3개가 반박됨 | 🔴 읽기 |
| **3** | `outputs/research-plan-v6.md` | **연구계획서 정본** (v6.2, 18절) | 설계·근거 |
| **4** | `outputs/research-plan-v6-easy.md` | 쉬운 해설 (비유 중심, v6.2) | 비전문가·면담 |
| **5** | `outputs/protocol-v6-frozen.md` | 현장 실행 체크리스트 (세션 대본·채점 시트) | 치료사·촬영 |
| **6** | `outputs/01-조사문헌/arat-fma-ue-evidence-map.md` | 증거맵 (논문 40편 + 쉬운설명) | 문헌 근거 |
| **7** | `outputs/01-조사문헌/rgbd-grasp-vlm-protocol-analysis.md` | 아틀라스 (논문 43편 정밀 프로토콜) | 상세 근거 |

> **✅ 감사 결과 요약:** 위 6·7번(증거맵·아틀라스)과 3번(계획서)은 **깨진 인용 0건**이었다.
> 문제는 **`capstone/` 분석보고서 5개**에 집중되어 있었고, 2026-09-25에 **교정 16건 · 철회 15건 · 보완 2건**을 처리했다.

---

## 2. outputs/ 구조 (정리 후)

```
outputs/
├── research-plan-v6.md              🔵 정본 연구계획서
├── research-plan-v6-easy.md         🟢 쉬운 해설
├── protocol-v6-frozen.md            🟠 현장 실행 체크리스트
│
├── 01-조사문헌/                     ← 문헌 조사 (읽기용)
│   ├── arat-fma-ue-evidence-map.md          (156KB, 논문 40편)
│   ├── arat-fma-ue-evidence-map-ko.md       (24KB, 한국어판)
│   ├── arat-fma-ue-evidence-map.provenance.md (12KB, 출처·검증 이력)
│   └── rgbd-grasp-vlm-protocol-analysis.md  (184KB, 논문 43편 정밀 분석)
│
├── 02-설계이력/                     ← 왜 이렇게 설계했나 (이력)
│   └── experiment-plan-v6-naive.md          (100KB, 결정 근거 전체)
│
├── 03-검증/                         ← 검증 기록
│   ├── systematic-search-novelty-audit.md   🔴 신규성 감사
│   └── experiment-plan-v6-verification.md   (내부 불일치 6건·위험 12개)
│
├── open-science-seeds/              (12MB, Feynman 제공 예시 — 그대로)
│
├── .plans/                          (작업 계획 초안)
└── .drafts/                         (중간 초안 5개)
```

---

## 3. experiments/ 구조 (실행 코드)

```
experiments/
├── vlm_conditions/make_conditions.py     🔴 주입 생성기 + A0~R 하네스 (오라클 ALL PASS)
│   └── _example_20260915/                (실제 데이터로 돌린 결과: 조건 208건)
├── vlm/run_vlm.py                        🔴 VLM 실행 하네스 (오라클 V1~V9 ALL PASS)
├── analysis/analysis_harness.py          🔴 PR-1·PR-2·bootstrap·Holm·가중κ
├── l1_pipeline/                          (L1 계산 — 참고용, capstone이 더 정교)
│   ├── k1k2_reference.py                 (오라클 참조 구현 T1~T6)
│   └── k1k2_from_files.py                (실데이터 파일 입력판, 오라클 S1~S5)
├── gauge_validation/                     (치구 135기록 빈 템플릿 시트 + 분석기)
│   ├── gauge_sheet_template.csv
│   ├── make_gauge_sheet.py
│   └── analyze_gauge_validation.py
├── session_tools/make_session.py         (세션 폴더 + 채점 시트 생성)
└── results/                              (오라클 테스트 로그 5개 — 코드 무결성 검증 증거)
```

**실행 방법:** 각 스크립트 상단 docstring 참조. 주요 명령:
```bash
python experiments/vlm_conditions/make_conditions.py --selftest
python experiments/vlm_conditions/make_conditions.py --session-dir "<세션경로>" --out <출력>
python experiments/analysis/analysis_harness.py --selftest
python experiments/l1_pipeline/k1k2_from_files.py --selftest
```

---

## 4. 사용자의 기존 자산 (내가 건드리지 않음)

### `capstone/` (994MB) — 실제 연구 파이프라인
| 경로 | 내용 |
|---|---|
| `05_웹캠_핸드트래킹_테스트/` | **MediaPipe + RealSense 동시 기록**, `kinematics.py`(OneEuro·ApertureFilter·thumb_abduction), `Mirror_therapy.py`(131KB), `sparc_reference.md` |
| `06_VLM_재활평가_테스트/` | `analyze_my_video_14frames.py`, `fma_eval_llavanext.py`, `multi_vlm_evaluator.py`, `benchmark_runner.py`, `sampled_14_frames/` |
| `호진파일/outputs/데이터_저장/` | **실제 데이터**: 비장애인 2명(26세·62세), 8시행/세션. `trials_summary.csv`(58열), `qiu_kinematics_summary.csv`, `landmarks.csv`, `frame_quality.csv`, `split/index.csv` |
| `01~04`, `기타양식`, `이미지` | 참고논문 PDF, 보고서 제출본, 계획서, 다이어그램 |
| `scripts/` | 그림 생성 스크립트 |

### 기타
| 경로 | 내용 |
|---|---|
| `끝/` (5.6MB) | 국립재활원 기술수요조사서 관련 (별개 과제) |
| `feynman-sessions/` (9.8MB) | Feynman 세션 기록 |
| `Research_Proposal_MasterSlave_MirrorTherapy.md` (33KB) | 거울치료 연구제안서 (별개 주제) |
| `ARAT_논문조사_종합보고서.md` (23KB) | 초기 논문조사 보고서 |
| `2026-09-21_랩미팅_연구진행보고_이재용.{md,docx}` | 랩미팅 자료 |
| `CHANGELOG.md` (42KB) | **작업 일지 — 15차 항목까지** |
| `FEYNMAN_SYNC_GUIDE.md` | Feynman 동기화 가이드 |

---

## 5. 정리 제안 (내가 하지 않은 것 — 사용자 판단 필요)

| # | 대상 | 제안 | 이유 |
|---|---|---|---|
| **1** | `preview_frames_llavanext/` (루트, 532KB) | **삭제** | `capstone/06_VLM_재활평가_테스트/preview_frames_llavanext/` 와 **내용 동일(중복)** |
| 2 | `test_r12_syntax.dxf`, `pure_r12_test.dxf` | 보관 또는 삭제 | CAD 문법 테스트 파일. 이 연구와 무관 |
| 3 | `scratch_splits.txt` | 보관 또는 삭제 | PPT 슬라이드 분할 스크래치 |
| 4 | `프레젠테이션1.pptx` (2.3MB), `프레젠테이션1/` | 보관 | 발표자료. 최신 여부 확인 필요 |
| 5 | `video_analysis_result.md`, `fma_result_llavanext_cylindrical.md` | `capstone/06_.../` 로 이동 | VLM 분석 결과 — 06 폴더 소속 |
| 6 | `logo_stamp_original.jpg` (97KB) | 보관 | 로고 |
| 7 | `notes/`, `papers/` | **빈 폴더** | 사용 또는 삭제 |

**⚠️ 나는 사용자 파일을 삭제하지 않았습니다.** 위 7개는 제안이고, 1번(중복)만 확실합니다.

---

## 6. 상태 요약 (2026-09-23)

| 영역 | 상태 |
|---|---|
| 연구계획서·프로토콜 | ✅ 완성 (18절 / 19절 / 10절) |
| 실행 코드 | 🟡 6개 영역, 오라클 전부 PASS. **VLM 실행 하네스 미작성** |
| 설계 결정 | ✅ 27개 중 20개 종결, 7개 외부 의존 |
| **신규성 검증** | 🔴 **이전 주장 3개 반박됨** → 차별점 재설계 필요 |
| 실증 데이터 | 🟡 건강인 2명 (사용자 파이프라인). 환자 0명 |
| 동결 절차 | ❌ 해시·사전등록 미이행 |

---

## 7. 다음 우선순위

| # | 할 일 | 이유 |
|---|---|---|
| **1** | **팀 코드에 dt 하한 규칙 구현** (`capstone/호진파일/compute_qiu_metrics.py`) | 계획서·프로토콜에는 적혔지만 **코드 미반영**. 그 전까지 `PV` 값은 신뢰 불가 |
| **2** | **대체 문헌 13편 초록 확인** | 미검증 인용을 철회하고 붙인 대체 문헌이 **원 주장을 실제로 지지하는지** 미확인 |
| **3** | **컴퓨트 산식 확정 (1,008 vs 864)** | 계획서 §6.1의 이중계산 — 예산을 잡기 전에 필요 |
| 4 | 신규성 감사 읽고 차별점 재설계 | 지금 상태로는 "incremental" 위험 |
| 5 | Scopus / IEEE Xplore에서 추가 검색 | 이번 감사는 PubMed+웹만 했다 |
| 6 | 임상 참조 점수 확보 (치료사) | 없으면 논문 불가 |
| 7 | **계획서 동결 해시** (`sha256sum outputs/research-plan-v6.md`) | v6.2 정정이 끝났으므로 이제 가능. 10분 |
| 8 | `preview_frames_llavanext` 중복 삭제 · `notes/`·`papers/` 빈 폴더 정리 | 즉시 |

### 🔴 새로 생긴 경고 (2026-09-25)

- **`capstone/` 5개 분석보고서를 외부에 제출하지 말 것.** 가짜 인용이 **본문 수치**까지 오염시킨 곳이 5군데 있다(`1-b` §2.1 실패모드 표, `1-b` §3 각속도, `3-b` §2 비교표, `3-a` §2).
- 상세와 파일 목록은 `outputs/03-검증/provenance/citation-verification-report.md` 참조.
