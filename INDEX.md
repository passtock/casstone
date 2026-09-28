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
| 실증 데이터 | 🟡 비장애인 2명 (사용자 파이프라인). 장애인 0명 |
| 동결 절차 | ❌ 해시·사전등록 미이행 |

---

## 7. 다음 우선순위

| # | 할 일 | 이유 |
|---|---|---|
| **1** | 🔴 **D-18 보조 모델 확정·다운로드** | HF 캐시에 **`Qwen2.5-VL-72B`도 `InternVL`도 없다.** `timm` 미설치, `run_vlm.py`에 보조 백엔드 없음. **동결 전 필수** |
| **2** | 🔴 **D-16 원시 depth 부재 결정** | 재촬영(§4.5 규약) vs 변환 어댑터. 어댑터면 **K1 정의가 바뀜** |
| **3** | 🟠 **D-17 A1+ 교란통제 조건 결정** | PR-1을 주 결과로 올렸으므로 **교란이 직접 문제**. 추가 +240회 |
| **4** | **컴퓨트 서빙 경로 확정** (GPU 호스트·API 키) | **1모델 1,608 · 2모델 3,216회**를 돌릴 곳이 없다 |
| **5** | **qwen 백엔드 1회 시범 실행** | 실측 토큰·지연 확인 |
| **6** | **모집 확대 반영** — 장애인 20명 · 비장애인 16명 | 표본 재계산 결과. **10주면 빠듯 → 12주 권장** |
| 7 | `capstone/` 보고서 5곳 본문 수치 재작성 | 가짜 인용이 숫자까지 오염 |
| 8 | 대체 문헌 5건(부분 지지) 문장 범위 축소 | Hesse(모집단)·Cheng(보행)·Scataglini(지침 아님) |
| 9 | 계획서 동결 해시 | D-16·D-18을 닫은 뒤 |

### 🧰 실행 코드 현황 (2026-09-28, **오라클 7종 183 PASS / 0 FAIL**)

| 파일 | 역할 | 상태 |
|---|---|---|
| `experiments/l1_pipeline/k1k2_from_files.py` | **L1** K1·K2·Q + **dt 하한** | ✅ 19 PASS |
| `experiments/vlm_conditions/make_conditions_v6.py` | **조건 정본 생성기** (§6·§7) | ✅ **40 PASS** (v6.2·v6.3 회계 모두 검증) |
| `experiments/analysis/baseline_models.py` | **A0 · A0-time** | ✅ 13 PASS |
| `experiments/vlm/run_vlm.py` | VLM 실행 하네스 | ✅ 49 PASS (실제 실행 0회) |
| `experiments/analysis/analysis_harness.py` | **PR-1·PR-2·PR-3**·bootstrap·Holm(k=3) | ✅ **29 PASS** |
| `experiments/vlm_conditions/make_conditions.py` | ~~파일럿 생성기~~ | ⚠️ **폐기 표시 (D-15)** |

> 🔵 **v6.3 (2026-09-28) 설계 변경:** PR-1 = 수치 주입 효과(`MAE(A2)−MAE(A1)`) 승격 · 장애인 23명·비장애인 22명 · 모델 2개.

### 📘 용어 (2026-09-25 동결)

본 프로젝트 문서는 **`비장애인`(대조군) / `장애인`(연구 참여자)** 을 쓴다.
`장애인`은 **뇌졸중 후 상지 기능장애를 가진 참여자**를 뜻하며 **행정적 장애 등록 여부와 무관**하다.
적용: **Feynman 생성 24개 + 사용자 파일 56개 = 80개**.
**보호된 데이터 식별자 5곳**(폴더명 템플릿 `_환자_` 4 + 메타데이터 `else '환자'` 1)은 의도적으로 원형 유지 — 코드가 만드는 실제 폴더명과 어긋나면 데이터셋이 갈라진다.
**제외 2개**: `참고논문_추출텍스트.txt`(타 저자 인용문), `pptx_extracted_text.txt`(원본 pptx와 어긋남 방지).
백업: `outputs/03-검증/provenance/_backup_terminology_20260925/`

### 🔴 새로 생긴 경고 (2026-09-25)

- **`capstone/` 5개 분석보고서를 외부에 제출하지 말 것.** 가짜 인용이 **본문 수치**까지 오염시킨 곳이 5군데 있다(`1-b` §2.1 실패모드 표, `1-b` §3 각속도, `3-b` §2 비교표, `3-a` §2).
- **프롬프트 문구 변경됨** — `null은 … 기능 저하나 0값을 뜻하지 않습니다`. 옛 문구로 생성된 조건 파일이 있으면 재생성 필요.
- 상세와 파일 목록은 `outputs/03-검증/provenance/citation-verification-report.md` 참조.
