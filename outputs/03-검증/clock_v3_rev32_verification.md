# `Mirror_therapy_clock_v3.py` 코드 검증 (rev 3.2, 2026-09-29)

검증 대상: `capstone/호진파일/Mirror_therapy_clock_v3.py`
- 식별: **rev 3.2**, 3,283행, sha256 `61af8c8860b67288e551167475cd665ec65abd4283a96f73e1a23f51d1dc0f20`
- 이전 내 검토본은 rev 3.1(3,183행) → 사용자가 **K2·원시 depth 저장을 추가**한 rev 3.2가 OneDrive에 반영됨.
- 재현: `scratch/verify/verify_clock_v32.py` → `scratch/verify/clock_v32_result.txt`

---

## 0. 판정 요약

**코드 자체는 정상 동작한다.** 컴파일·import OK, 정적 검사 clean, 신규 함수 오라클 ALL PASS, rev 3.1 기능 회귀 없음.
**다만 "L1에 연결된다"는 아직 아니다** — 그리고 **운영상 큰 부담**이 하나 새로 생겼다.

| # | 항목 | 결과 |
|---|---|---|
| 1 | 컴파일 / import | ✅ |
| 2 | 정적 검사(중복정의·bare except·미정의 이름) | ✅ clean |
| 3 | `wrist_k2()` 오라클 6종 | ✅ ALL PASS |
| 4 | `save_depth_packet()` 왕복 | ✅ ALL PASS |
| 5 | trials_summary CSV 정합 | ✅ **78 == 78** |
| 6 | rev 3.1 기능 회귀(SPARC 참조·per-cycle·_mono) | ✅ 이상 없음 |
| 7 | **L1 연결(입력 포맷)** | 🔴 **불일치 — 어댑터 필요** |
| 8 | **디스크/IO 부담** | 🟠 **프레임당 5.42 MB · 91.6 MB/s** |
| 9 | **K2가 L1과 동일 정의인가** | 🟠 **아니다(3항목 상이)** |
| 10 | 정렬 depth intrinsics | 🟡 SDK 의존 — 실측 확인 필요 |

---

## 1. 실행 검증 결과 (실제 출력)

**`wrist_k2()` 오라클** — 합성 레코드:

| 케이스 | 기대 | 결과 |
|---|---|---|
| 정상 60쌍(0.001 m/프레임 @60fps) | P95 ≈ 60 mm/s, pairs 60 | **60.0000**, valid 60, rejected 0 ✅ |
| dt > 상한(0.5 s) 삽입 | 제외 | rejected **2** ✅ |
| frame_id 건너뜀 | 제외 | rejected **2** ✅ |
| 손 바뀜 | 제외 | rejected **2** ✅ |
| 19쌍(min_pairs=50 미달) | value=None | `None`, status `insufficient_valid_pairs` ✅ |
| 정지(같은 점) | 0 | **0.0** ✅ |

**`save_depth_packet()` 왕복**: 파일 `000000007.npz`, 키 `color_bgr·depth_aligned_u16·depth_native_u16·metadata_json`, native dtype `uint16`, 값·메타 **왕복 일치** ✅

**trials_summary CSV**: 헤더 **78** == 데이터 **78**, K2 열 존재(`K2_Wrist_Speed_P95_mm_s`·`K2_Candidate_P95_mm_s`·`K2_Valid_Pairs`·`K2_Rejected_Pairs`·`K2_Status`) ✅ (rev 3.1의 73 + 5)

**정적 검사**: module-level 중복 정의 **0**, bare `except` **0**, 미정의 이름 **0**(`__file__` 1건은 오탐)

**rev 3.1 회귀**: SPARC가 원저자 참조구현과 여전히 일치(gaussian/벨 exact), `sparc_per_cycle` 정상, `_mono` 중복 시각 거부 유지 ✅

---

## 2. 🔴 L1 연결 격차 — rev 3.2에서도 여전히 불일치

새 원시 depth 저장은 **`.npz`**, L1은 **16-bit `.png`** 를 읽는다.

| 항목 | L1 (`k1k2_from_files.py`) 요구 | rev 3.2 앱 출력 | 상태 |
|---|---|---|---|
| 원시 depth 경로/형식 | `L0_raw/<trial>_depth/*.png` (16-bit, `cv2.imdecode`) | `raw_rgbd/{frame_id:09d}.npz`(`np.savez`) | 🔴 **불일치** |
| 메타 | `meta.json` **최상위** `fx,fy,cx,cy,depth_scale` | `<pre>_metadata.json` + npz 내 `metadata_json`(중첩) | 🔴 변환 필요 |
| 랜드마크 | `L1_track/<trial_id>_landmarks.csv` **가로형** | `*_landmarks.csv` **세로형(21관절)** | 🔴 변환기 필요 |
| `occlusion_state` | visible/partially_occluded/not_assessable | 앱이 안 만듦(**사람 주석** 필드) | 🔴 주석 경로 필요 |
| 시행 키 | `H01_T1_t01` | `Session_..._Task1_..._Trial_1` | 🔴 매핑 필요 |

→ **결론: rev 3.2로 "원시 depth가 저장된다"는 참이 됐지만, "L1이 그 파일을 읽는다"는 아직 거짓이다.** `.npz → 16-bit PNG + meta.json + L1_track 변환 어댑터`가 필요하다.

**참고(좋은 점):** `save_depth_packet`은 `open(tmp,'wb')` + `np.savez` + `os.replace`를 써서 **cv2의 비ASCII 경로 실패(작업 폴더가 `바탕 화면`)** 를 피했다. 이건 L1의 `_imwrite16` 주석이 지적한 바로 그 함정을 회피한 올바른 선택이다.

---

## 3. 🟠 K2가 L1 정식 K2와 같은가 → 아니다

| 항목 | L1 | 앱 `wrist_k2` | 영향 |
|---|---|---|---|
| dt 하한 | **median(dt)/2** (자동; 16.9fps면 ≈0.028 s) | **고정 0.005 s** | 같은 세션에서도 다른 쌍이 걸러짐 → **값이 달라짐** |
| dt 상한 | 0.1 s | 0.1 s | 동일 |
| 인접 조건 | 연속 레코드(프레임 건너뜀 허용) | **`frame_id+1` 필수** | 드롭아웃 시 앱이 더 많이 제외 |
| 손 | 파일 단위 | **hand 동일 요구** | 동일(중복 조건) |
| 최소 쌍 | 없음(Q가 보고) | **`min_pairs=50`** | 짧은 시행에서 앱은 `None` |
| 시간축 | `t_s` | **`mono`**(perf_counter) | 앱이 더 견고(V-1 회피) |

→ 사용자가 말한 **"L1의 정식 K2와 일치 확인 전까지 보조 확인용으로 구분"** 이 정확하다. **같은 시행에서 두 값이 다르게 나온다.**

---

## 4. 🟠 저장량 — 동기화는 무관, "쓰기 시간"만 확인 (2026-09-29 정정)

`save_depth_packet`은 매 기록 프레임마다 **color + aligned depth + native depth**를 **무압축(`np.savez`)** 으로 저장한다.

| 저장 항목 | 크기/프레임 |
|---|---|
| color_bgr 1280×720×3 | 2.76 MB |
| aligned depth 1280×720×2 | 1.84 MB |
| native depth 848×480×2 | 0.81 MB |
| **합계** | **5.42 MB** |

| 규모 | 용량 |
|---|---|
| @16.9 fps | 91.6 MB/s (@24.6 fps → 133 MB/s) |
| 8초 trial 1개 | ≈0.73 GB |
| 예정 본평가(120 trial) | ≈**88 GB** |

**⚠️ 1차 검토 정정:** "OneDrive 동기 폴더 밖에 저장하라"는 권고는 **이 환경에서 불필요**하다. 실측:
- **OneDrive 프로세스 미실행** — 동기화 비활성.
- 경로는 **로컬 C: 드라이브** — 여유 **442 GB / 700 GB**.
→ **네트워크 업로드 부담 없음**, **본평가 88 GB도 여유 범위**.

**남는 것(동기화와 무관):** 원시 저장이 **녹화 루프 안에서 동기 write**이므로, 실측에서 **fps가 떨어졌는지**만 확인하면 된다(떨어지면 dt가 커져 K2·SPARC에 영향).

**완화 후보(선택):** ① `np.savez_compressed`, ② color를 npz에서 제거(AVI 재사용), ③ native depth만 저장, ④ 저장을 캡처와 분리(큐/워커). **단 "무손실 원본 전체 저장" 원칙과 충돌 여부는 정책 결정.**

---

## 5. 🟡 정렬 depth intrinsics — 실측 확인 필요

- 앱은 `self.depth_intr = df.profile.as_video_stream_profile().get_intrinsics()`로 역투영하고, npz에 `aligned_depth_intrinsics=frame_calibration(df)`를 저장한다.
- depth를 color에 정렬(align)한 뒤에는 **color 기준 intrinsics**를 써야 한다. `align.process` 후 `get_intrinsics()`가 color를 돌려주는지는 **SDK 버전 의존**이다.
- `camera_info`에 `color_intrinsics`·`depth_intrinsics`가 함께 저장되므로 소비자가 선택할 수 있다.
- → **카메라 연결 후 실측 확인(치구 거리 검증)에서 반드시 점검.** 확정 버그라고 단정하지 않는다.

---

## 6. 잘 된 점 / 개선 권고

**잘 된 점**
- 정적 상태 clean, 신규 두 함수 오라클 통과, 기존 기능 무회귀.
- `save_depth_packet`이 **atomic(`os.replace`)·no-pickle·비ASCII 경로 안전**.
- depth 저장 실패가 **캡처를 죽이지 않음** — `try/except` + `raw_depth_errors.jsonl` 기록 + 카운터 + UI 경고.
- native/aligned depth를 **구분 저장**(무손실, 재현성).
- K2·per-cycle SPARC가 trials_summary에 **QC 상태와 함께** 기록됨(`K2_Status`, `SPARC_Status`).

**권고**
1. **어댑터 작성**: npz→16-bit PNG + `meta.json`(최상위 fx/fy/cx/cy/depth_scale) + `L1_track` 가로형 변환. (또는 L1이 npz를 읽도록 수정 — 둘 중 하나를 동결)
2. **K2 단일화**: 앱 `wrist_k2`를 L1과 **같은 규칙**(dt 하한 = median/2, 연속 레코드 허용, 최소쌍 정책)으로 맞추거나, 앱 값을 **보조 지표로만** 명시.
3. **저장 정책 결정**(§4) — 본평가 전에 IO·용량 실측.
4. **intrinsics 실측 확인**(§5) — 치구 거리 검증에서.
5. **오라클에 L1 계약 검사 추가**: "npz→PNG 변환 후 L1이 값을 내는가"를 회귀 테스트로 고정.

---

## 7. 재현

```bash
cd "capstone/호진파일"
python -m py_compile Mirror_therapy_clock_v3.py
PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python ../../scratch/verify/verify_clock_v32.py
# 기존 회귀 하네스
cd outputs/_compare && python run_kinematics_ab.py && python run_sparc_parity.py \
  && python run_percycle_validation.py && python run_csv_alignment_check.py
```

## 8. 사용자 반영 확인 (2026-09-29 2차 점검)

사용자가 "원시 깊이 저장을 OneDrive 실행파일에 반영했다"고 보고 → 실제 파일로 확인:

| 사용자 주장 | 확인 |
|---|---|
| 반영된 실행 파일 | ✅ rev 3.2, **sha256 `61af8c88…` (내 1차 검증과 동일 — 미변경)** |
| 기존 파일 백업 | ✅ `Mirror_therapy_clock_v3_backup_20260929_142457.py` — 헤더가 **rev 3.1**, `wrist_k2`/`save_depth_packet` **없음**, `sparc_per_cycle` **있음** → “백업 + per-cycle 보존” 맞음 |
| NPZ에 정렬 전/후 깊이 + 무손실 RGB | ✅ 키 `color_bgr·depth_native_u16·depth_aligned_u16` |
| 프레임번호·시각·깊이단위·카메라보정 | ✅ `frame_id`·`capture_monotonic_s`·`capture_unix_s`·`depth_unit='uint16 * depth_scale_m = metres'`·`camera_info`·`aligned_depth_intrinsics` |
| 화면 성공/오류 개수 | ✅ 상태줄 `"RAW 저장 {saved} / 오류 {errors}"` + 오류 시 toast |
| 저장 오류 별도 기록 | ✅ `raw_depth_errors.jsonl` |
| 보조 K2(L1 정식과 미일치) | ✅ `wrist_k2` 존재, §3처럼 L1과 정의 상이 |
| 계산·출력 검증 23개 통과 | ⚠️ **사용자 테스트 산출물은 레포에서 찾지 못함.** 단 §1의 **내 독립 검증은 ALL PASS**이므로 기능은 뒷받침됨 |
| 실제 RealSense 시험 | ❌ 아직 (사용자도 인정) |

### 🟠 짧은 수집 테스트의 용량·IO (2026-09-29 정정)
프레임당 **5.42 MB**(무압축)이므로 저장량 자체는 큽니다:

| 촬영 길이 | @16.9 fps | @24.6 fps |
|---|---|---|
| 10초 | 0.92 GB | 1.33 GB |
| 20초 | 1.83 GB | 2.67 GB |

**⚠️ 정정:** "OneDrive 동기화 부담" 우려는 **이 환경에 해당 없음**(OneDrive 프로세스 미실행, 경로는 로컬 C: 442 GB 여유). → 동기화 때문에 폴더를 옮길 필요 없고, **본평가 88 GB도 여유 범위**.
**남는 확인:** 원시 저장이 녹화 루프 안 동기 write이므로 **촬영 후 실측 fps**가 스펙 대비 얼마나 떨어졌는지만 보면 된다.

### 어댑터는 여전히 필요 (사용자 인정과 일치)
`raw_rgbd/*.npz` → `L0_raw/<trial>_depth/*.png`(16-bit) + `meta.json`(최상위 fx/fy/cx/cy/depth_scale) + `L1_track`(가로형) 변환·매핑이 남아 있다.

---

## Sources
- `capstone/호진파일/Mirror_therapy_clock_v3.py` (rev 3.2, sha256 `61af8c88…`)
- `experiments/l1_pipeline/k1k2_from_files.py` (입력 계약: `load_meta`·`read_landmarks`·`backproject`·K2 계산부)
- `experiments/session_tools/make_session.py` (meta.json 템플릿)
- `scratch/verify/verify_clock_v32.py`, `scratch/verify/clock_v32_result.txt`
- `outputs/03-검증/execution-plan-vs-repo-20260929.md` §1·§7

## Blocked / Unverified
- **실제 카메라·GUI 미구동** — depth 저장의 실측 fps 영향, intrinsics 값, `.npz` 실제 크기는 **카메라 연결 후** 확인 필요.
- 본 검증은 **rev 3.2 현재 파일** 기준이며, 사용자의 추가 로컬 수정이 있으면 재검증 필요.
