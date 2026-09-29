# D-15 상태 검증: 조건 생성기 ↔ 계획서 정합 (verifier report)

작성일: 2026-09-29 · 대상: `experiments/vlm_conditions/make_conditions_v6.py`, `outputs/protocol-v6-frozen.md`, `outputs/research-plan-v6.md` §15.2 D-15
검증 도구: 코드 직접 대조 + 생성기 오라클 실행(`--selftest`) + 외부 1차 자료(ARAT 표준 채점지)

---

## 0. 결론

**D-15의 코드 정합 결함 5건은 후속 생성기 `make_conditions_v6.py`에서 모두 해소되어 있음을 확인했다(오라클 43 PASS / 0 FAIL).**
다만 **한 건의 잔존 결함(구슬 규격)을 새로 발견·정정**했고, **실제 세션 end-to-end 실행은 D-16에 막혀** 있어 D-15는 "코드 정합 완료 / 실데이터 실행 미완"의 **부분 해소** 상태다.

| 항목 | 판정 |
|---|---|
| D-15 ① 지표 불일치(4개 → K1·K2) | ✅ 해소 |
| D-15 ② PV=peak(V-1 파손 지표) | ✅ 해소 (K2 = 속도 P95) |
| D-15 ③ 과제 불일치(free/cylinder → ARAT 3/12) | ✅ 해소 (규격 잔존 결함도 정정) |
| D-15 ④ A0/A0-time 조건 없음 | ✅ 해소 (설계상 별도 파일 — 결함 아님) |
| D-15 ⑤ 주입 불일치(burst_implausible → burst_3u) | ✅ 해소 |
| **신규 발견: VLM 프롬프트의 구슬 ⌀1.6 cm (정본 1.5 cm)** | 🔧 **정정 완료** |
| 실제 세션 end-to-end 실행 | ⛔ **D-16(원시 depth 부재)에 막힘** |

---

## 1. D-15가 무엇이었나 (계획서 §15.2 원문)

`make_conditions.py`(파일럿용)가 계획서와 다음이 다르다:
① 지표 4개(`MGA_mm_3D_cal`·`PV_mm_s`·`SPARC`·`TAM_total_deg`) vs 계획서 K1·K2 2개
② `PV_mm_s` = peak velocity (V-1이 깨졌다고 규명한 지표)
③ 과제 `free`·`cylinder` vs ARAT 3·12번
④ A0·A0-time 없음
⑤ 주입 `burst_implausible` vs `burst 3u`
→ **"그 전에는 데이터 수집을 시작하면 안 된다."**

---

## 2. 검증 방법과 근거

### 2.1 코드 직접 대조 (`make_conditions_v6.py`, 523행)

| D-15 항목 | 코드 근거 | 판정 |
|---|---|---|
| ① 2지표 | `KPI = {"k1":"thumb_index_surface_p95_mm", "k2":"wrist_surface_speed_p95_mm_s"}`; 주석 "지표 2개(K1·K2) — MGA/PV/SPARC/TAM 아님" | ✅ |
| ② K2 = 속도 P95 | `K2` 키가 `wrist_surface_speed_p95_mm_s` (peak 아님) | ✅ |
| ③ 과제 | `TASKS = {"T1":{"arat":"3",...}, "T2":{"arat":"12",...}}`; 프롬프트 `task_label`이 ARAT 번호 사용 | ✅ (규격 결함 §3에서 정정) |
| ④ A0 | `CONDITIONS=["A1","A2","A3","A4","R"]` + 주석 "A0/A0-time은 로지스틱 회귀라 VLM 출력이 아니다 → `experiments/analysis/baseline_models.py`" | ✅ (결함 아님) |
| ⑤ 주입 | `INJECTIONS=["none","bias_1u","bias_3u","burst_3u"]`; `inject()`가 burst를 **지정 시행 하나만 +3u** 로 구현 | ✅ |

### 2.2 오라클 실행 (재현 명령)

```bash
PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python experiments/vlm_conditions/make_conditions_v6.py --selftest
```
- 결과: **43 PASS / 0 FAIL** (`experiments/results/conditions_v6_oracle.txt` 갱신)
- 검사 범위: [C1] 상수·지표·과제 · [C2] 프롬프트 §7.1 일치 · [C3] A2/A3 값 선택 · [C4] 주입 · [C5] R 배정 · [C6] 행 구조 · [C7] 컴퓨트 산식(1,608 / 3,216회)
- ⚠️ **주의(환경):** 기본 콘솔(cp949)에서 em-dash `—` 때문에 `UnicodeEncodeError`로 크래시한다. **`PYTHONIOENCODING=utf-8` 없이 실행하면 오라클이 실패한 것처럼 보인다.** 코드 결함이 아니라 콘솔 인코딩 문제다(별도 수정 권장 사항).

---

## 3. 신규 발견 결함: VLM 프롬프트에 구슬 ⌀1.6 cm (정본은 ⌀1.5 cm)

### 3.1 결함

`make_conditions_v6.py`의 `TASKS["T2"]["object"] = "구슬 지름 1.6 cm 5.4 g"` → `task_label("T2")` → **실제 프롬프트에 그대로 삽입**됨을 실행으로 확인:

```
변경 전:  [과제]  ARAT 12번 — 구슬 지름 1.6 cm 5.4 g
```
계획서 v6.4 정본은 **⌀1.5 cm**. `protocol-v6-frozen.md` §2도 ⌀1.6 cm로 어긋나 있었다.
즉 **D-15를 고친 생성기가 자체적으로 정본과 다른 물성을 모델 입력에 넣고 있었고, 오라클은 이 값을 검사하지 않았다.**

### 3.2 정본 1.5 cm의 근거 (외부 1차 자료 확인)

- ARAT 표준 채점지(Yozbatiran/Lyle 계열): **"Pinch 2. Marble, 1.5 cm, index finger and thumb"** — https://faculty.ksu.edu.sa/sites/default/files/action_research_arm_test.pdf
- Yozbatiran et al. 2008 *A Standardized Approach to Performing the ARAT*(물성 Table A2) — https://mahilab.rice.edu/sites/default/files/page-files/Yozbatiran_ARAT_2007.pdf (doi 10.1177/1545968307305353)
- 본 워크스페이스 `outputs/01-조사문헌/`의 증거맵·아틀라스도 이미 **1.5 cm**로 일관.

→ 계획서 v6.4의 "1.6→1.5 cm 확정"은 **외부 표준과 일치**한다. 정본이 맞고, 코드·프로토콜이 stale였다.

### 3.3 정정 내용

| 파일 | 변경 |
|---|---|
| `experiments/vlm_conditions/make_conditions_v6.py` | `TASKS["T2"]["object"]` 1.6→**1.5 cm**; docstring 표 동일 정정; **오라클에 회귀 검사 3건 추가**(T2 물성=1.5 cm, T1 물성=5 cm/55 g, 프롬프트 라벨=1.5 cm) |
| `outputs/protocol-v6-frozen.md` §2 | T2 구슬 **1.6→1.5 cm** |
| `outputs/research-plan-v6.md` | 헤더에 v6.4 후속 정정(2026-09-29) 기록; §15.2 D-15 상태를 "**부분 해소**"로 갱신(원문 설명은 기록으로 보존) |

정정 후 재확인:
```
변경 후:  [과제]  ARAT 12번 — 구슬 지름 1.5 cm 5.4 g
```
오라클 재실행 **43 PASS / 0 FAIL** (신규 3건 포함).

---

## 4. 남은 것 (D-15가 "완전 종결"이 아닌 이유)

- **실제 세션 end-to-end 실행 미완.** 생성기는 `L2_metric/*.json`(`k1k2_from_files.py` 산출)을 입력으로 받는다. 그런데 파일럿 세션에 **원시 depth 프레임이 0장**이라 **D-16**에 막혀 있다(계획서 §15.2 D-16). 즉 **코드 정합은 끝났지만, 실제 데이터로 조건 CSV를 만든 적은 아직 없다.**
- 따라서 "데이터 수집 시작 가능"으로 바꿔 말하려면 **D-16을 먼저 닫아야** 한다(원시 depth 재촬영 또는 변환 어댑터).

---

## 5. 변경 파일과 해시 / 백업

백업 위치: `outputs/03-검증/provenance/_backup_marble_fix_20260929/`

| 파일 | 변경 전 sha256 | 변경 후 sha256 |
|---|---|---|
| `experiments/vlm_conditions/make_conditions_v6.py` | `9d81eb44…ba9712` | `712abd33…7bd701` |
| `outputs/protocol-v6-frozen.md` | `502819eb…69ab64` | `868ff722…575b078` |
| `outputs/research-plan-v6.md` | `43a7566e…4ea4f56a` | `98c00b3a…24708c` |

(`*BEFORE_sha256.txt` / `research-plan-v6.BEFORE.md` 로 원본 보존)

---

## 6. 한계 (정직)

- 이 검증은 **코드 정합** 검증이다. **실제 장애인 데이터로 생성기를 돌린 결과가 아니다**(D-16).
- 오라클은 **합성 레코드**다. 실제 촬영·VLM 성능이 아니다.
- 구슬 규격은 자료원에 따라 1.5 vs 1.6 cm 표기가 혼재한다. 본 검증은 **정본(v6.4)과 ARAT 표준 채점지(1.5 cm)에 근거**해 1.5 cm로 통일했다. 만약 실물 구슬이 1.6 cm라면 **실물 기준으로 다시 고정**해야 한다.
- `make_conditions.py`(파일럿용)와 `experiment-plan-v6-naive.md`·`experiment-plan-v6-verification.md`의 1.6 cm 표기는 **이력 문서**로 남겨 두었다(삭제하지 않음).

## Sources
- 계획서 정본: `outputs/research-plan-v6.md` (§4.2 물성, §6 조건, §7.1 프롬프트, §15.2 D-15/D-16)
- 현장 프로토콜: `outputs/protocol-v6-frozen.md`
- 신규성/정합 감사: `outputs/03-검증/deck-0928-vs-plan-v6-alignment-audit.md` §3-③, §4-5
- ARAT 물성 1차 근거: ARAT 표준 채점지 https://faculty.ksu.edu.sa/sites/default/files/action_research_arm_test.pdf · Yozbatiran et al. 2008 https://mahilab.rice.edu/sites/default/files/page-files/Yozbatiran_ARAT_2007.pdf (doi 10.1177/1545968307305353)
- 증거맵/아틀라스(워크스페이스): `outputs/01-조사문헌/arat-fma-ue-evidence-map.md`, `outputs/01-조사문헌/rgbd-grasp-vlm-protocol-analysis.md`
- 오라클 로그: `experiments/results/conditions_v6_oracle.txt`
