# 실행계획 대조 검증 (2026-09-29)

대상: 사용자가 정리한 "수정·정리 5가지" + "실제 테스트 7단계" + "당장 중요한 3가지".
방법: 워크스페이스 코드·프로토콜·파일럿 산출물 직접 대조. (추측 없이 파일에서 확인한 것만 기재)

---

## 0. 총평

**방향은 맞다. 순서(수집→원시저장→L1→VLM)도 맞다.** 다만 **①(프로그램 역할 확정)이 "정리" 수준이 아니라 "인터페이스 계약 확정 + 어댑터 작성"** 이라는 점이 빠져 있다. **지금 `clock_v3`는 그대로는 L1이 읽을 수 없다** — 원시 depth뿐 아니라 **파일 스키마·시행 이름·메타 형식**이 전부 다르다. 이게 단계 2·6이 막히는 실제 이유다.

| 단계 | 사용자 계획 | 레포 실태 | 판정 |
|---|---|---|---|
| ① 프로그램 확정 | clock_v3=수집, L1도구=계산 | **출력 계약이 서로 다름** (§1) | 🟠 **보완 필요** |
| ② 원시 depth 저장 | 저장돼야 함 | **없음**(D-16), 작업본엔 추가됨 | ✅ 맞음 |
| ③ K1·K2 연결 | 앱 파일을 L1이 읽나 | **현재 못 읽음** (§2) | 🟠 **더 구체화 필요** |
| ④ 문서 통일 | 구슬·시행·채점·모델·A4/A0 | 구슬은 09-29 정정, **모델 D-18 미확정** | ✅ 맞음 |
| ⑤ 잘못된 설명 정정 | 검증완료/SPARC탈락/면역 | 정확 | ✅ 맞음 |
| 테스트 1~7 | 작동 확인 순서 | 프로토콜 §6·§9와 부합 | ✅ 타당 |

---

## 1. ①의 실제 장벽 — `clock_v3` 출력 ≠ L1 입력 (파일에서 확인)

**L1(`experiments/l1_pipeline/k1k2_from_files.py`)이 요구하는 것** (docstring·코드 직접 확인):
```
<세션>/
  meta.json                              # 최상위 fx,fy,cx,cy,depth_scale,fps,camera_model
  L1_track/<trial_id>_landmarks.csv      # 헤더: frame,t_s,thumb_u,thumb_v,index_u,index_v,wrist_u,wrist_v,occlusion_state,edge_mixing_suspect
  L0_raw/<trial_id>_depth/*.png          # 16-bit, 값 = depth(mm)
→ 출력: L2_metric/<trial_id>.json        # K1·K2·Q·T
```

**`clock_v3`가 실제로 내놓는 것** (파일럿 세션에서 확인):
```
<세션>/
  original.avi, mediapipe.avi, video_timestamps.csv
  Session_..._continuous_raw.csv
  Session_..._landmarks.csv      # 헤더: Frame_ID,time_s,Hand,Landmark_ID,Landmark,Pixel_U,Pixel_V,MP_X_m..RS_Status  ← 긴 형식(21관절)
  Session_..._trials_summary.csv, _frame_quality.csv, _distance_comparison.csv
  Session_..._metadata.json      # camera_info.color_intrinsics(...) 안에 fx/fy/ppx/ppy
  split/Task1_.../Trial_1/...
  (L0_raw/, L1_track/, L2_metric/ 없음 · depth PNG 0장)
```

**→ 4가지 불일치:**

| 항목 | L1 기대 | clock_v3 현재 | 필요한 조치 |
|---|---|---|---|
| 파일명/폴더 | `L1_track/<trial_id>_landmarks.csv` | `Session_..._landmarks.csv`(평면) | 매핑/변환 |
| 랜드마크 스키마 | **가로형**(thumb/index/wrist의 u,v) | **세로형**(21관절 × Pixel/MP/RS) | **변환기 필요** |
| 랜드마크 없음 표기 | 빈 칸 | `RS_Status` 코드(ok/depth_hole/…) | 의미 매핑 |
| **`occlusion_state`** | `visible/partially_occluded/not_assessable` | **앱이 만들지 않음** — 이는 **사람 주석** 필드 | 주석 파이프라인 필요 |
| 메타 | `meta.json` 최상위 `fx,fy,cx,cy,depth_scale` | `_metadata.json → camera_info`(중첩) | **추출기 필요**(값 자체는 있음) |
| 원시 depth | `L0_raw/<trial>_depth/*.png` | **없음** | 수집기 수정 |

**핵심:** intrinsics **값은 이미 저장되고 있다**(`camera_info.color_intrinsics`, `depth_intrinsics`, `depth_scale_m`). 즉 "카메라 정보가 없다"가 문제가 아니라, **L1이 읽는 형식이 아니다.** 마찬가지로 `occlusion_state`/`edge_mixing_suspect`는 앱 출력이 아니라 **관측 주석**(계획서 §9.2)에서 온다.

→ **①을 이렇게 바꾸는 것을 권함:** "프로그램 역할 정리"가 아니라 **"인터페이스 계약 확정: (a) 수집기는 `L0_raw/<trial>_depth/*.png`(16-bit mm)를 쓰고, (b) `meta.json`(최상위 fx/fy/cx/cy/depth_scale)을 쓰고, (c) `L1_track/<trial>_landmarks.csv`(가로형)를 쓴다. 또는 그 셋을 만드는 어댑터를 만든다."**

---

## 2. ③의 실제 답 — "연결되나?" → **현재는 안 된다**

- `k1k2_from_files.py --selftest`는 **합성 세션**을 스스로 만들어 통과한다. **실제 파일럿 폴더를 넣으면** `meta.json`·`L1_track/`·`L0_raw/`가 없어 **동작하지 않는다.**
- 그래서 ③은 "확인"이 아니라 **"변환기/수집기 작성"** 작업이다. 작업량 순서: **①메타 추출 → ②랜드마크 변환 → ③원시 depth 저장 → ④시행 이름 매핑.**
- 사용자가 강조한 **"PIP 각속도 ≠ K2 손목 속도"** 는 정확하다. `clock_v3`의 `flex_speed/ext_speed`는 **PIP 각속도**이고, K2는 **손목 표면점의 3D 카테시안 속도 P95**다. 서로 대체 불가.

---

## 3. 테스트 7단계 — 타당함 (프로토콜과 부합)

| 단계 | 판정 | 근거/보완 |
|---|---|---|
| 1 짧게 촬영 | ✅ | 프로토콜 §0 주1–2 |
| 2 저장 파일 재열기(**원시 depth 존재?**) | ✅ | **D-16의 핵심** |
| 3 거리 확인(치구) | ✅ | §6.1 — 단 **정적으로 동적 가림까지 검증되지 않음**을 함께 기록 |
| 4 K2 정지 잡음·이동 속도 | ✅ | §6.1 동적 기준(슬라이더/모캡) |
| 5 일부러 추적 끊기 | ✅ | §6.2 가림 주석 — **결측과 이유 기록**(값 창작 금지) |
| 6 L1 실행 | ✅ | 단 §1·§2의 계약이 먼저 맞아야 실행됨 |
| 7 VLM A1·A2·A3·R(+A4·A0) | ✅ | §7. **조건 생성기=`make_conditions_v6.py` 확정** 필요(D-15) |

**빠진 점검 2개(추가 권장):**
- **시행 이름 매핑 확인**: L1은 `H01_T1_t01` 형식을 키로 쓴다. `clock_v3`의 `Trial_1`·`Task1`과 **사람 단위·과제 단위가 어긋나지 않는지** 반드시 확인(참가자 독립성).
- **컴퓨트 확인**: 7단계는 1건이면 되지만, 본평가는 **2모델 3,216회**다. 테스트 단계에서 **토큰·지연·저장**을 실측해두면 뒤가 안 막힌다.

---

## 4. "당장 중요한 3가지" — 맞다, 단 1번의 정의를 정확히

사용자: ① 원시 깊이 저장 확인 → ② 그 파일로 L1 K1·K2 계산 → ③ VLM 입력 전달.

- 방향은 **정확**하다.
- **1번을 "원시 depth 저장"으로만 좁히면 부족**하다. 원시 depth를 저장해도 **메타 형식·랜드마크 스키마·시행 이름**이 안 맞으면 2번에서 막힌다.
- 따라서 1번은 **"수집기 출력 계약(원시 depth + meta.json + L1_track 스키마) 동시 확정"**, 2번은 **"그 계약대로 L1이 실제 파일럿 폴더를 읽는 것"**으로 정의하는 것이 정확하다.

---

## 5. ⑤(잘못된 설명 정정) — 정확

| 정정 대상 표현 | 판정 | 근거 |
|---|---|---|
| "학술 검증 완료" | ✅ 틀림 | 계획서 §15.3 "실증 검증 0건" |
| "기존 SPARC는 확정 탈락" | ✅ 틀림 | 102%는 **구 파일럿**(`Time_Base` 없음) + Wagner 98.9% 오용. **보류(pending)로 두어야 함** |
| "같은 라벨이라 오류에 면역" | ✅ 과함 | 라벨 잡음 영향은 남음 |
| SPARC는 탐색용 | ✅ | §5.3·§0 |

---

## 6. 결론 — 계획에 추가할 3줄

1. **①을 "인터페이스 계약 확정 + 어댑터 작성"으로 재정의** (원시 depth만이 아니라 meta.json 형식·L1_track 가로형 스키마·시행 이름 매핑 포함).
2. **`occlusion_state`/`edge_mixing_suspect`는 앱이 아니라 관측 주석**에서 온다 → 주석 경로도 연결 대상에 포함.
3. **조건 생성기(`make_conditions_v6.py`)·보조 모델(D-18)·컴퓨트 경로**를 "테스트 7단계" 앞에 명시.

**사용자 계획 자체는 타당하다.** 유일한 수정은 **1번의 범위를 "저장"에서 "출력 계약 전체"로 넓히는 것**이다.

---

## 7. 다른 요약과의 합의 대조 + 보정 3건 (2026-09-29 2차)

사용자가 정리한 "쟁점별 비교표"는 **대체로 정확**하다. 아래 3건만 보정한다.

### 보정 1 — 단계 3은 "확인"이 아니라 "수정/어댑터" (이미 검증됨)
사용자: *"그 파일을 기존 L1 도구에 넣어 K1·K2·Q를 계산하기."*
→ **검증 결과: 현재 `clock_v3` 출력을 L1에 그대로 넣으면 동작하지 않는다**(§1의 4가지 불일치: `meta.json` 최상위 키·`L1_track` 가로형 스키마·`L0_raw` depth·시행 이름). 따라서 3번은 **"넣어 보기"가 아니라 "출력 계약을 맞춘 뒤(또는 어댑터를 만든 뒤) 넣기"**다. "연결 확인 필요"는 맞지만, **확인 결과가 이미 '안 맞음'**이다.

### 보정 2 — C2 명칭은 "세션 내 반복 변동 지표"가 더 정확 (사용자 제안 채택)
사용자: *"'반복시행 기반 MDC 근사'로 이름만 바꾸는 것으로 끝나지는 않는다 … '세션 내 반복 변동 지표'가 더 명확하다."*
→ **동의한다.** 이유를 보강하면:
- **MDC(test-retest)** 는 **다른 시점(세션 간)** 재측정으로 **측정오차**를 분리한다.
- 그런데 `metric_portfolio_check_v2.py:76`은 **같은 세션 내 반복시행 SD**로 계산한다. 여기에는 **측정오차 + 실제 수행 변동**이 섞인다.
- 따라서 "MDC95"라는 이름은 **과대**이고, 정확한 명칭은 **"세션 내 반복 변동(within-session repetition variability)"**이다. 세션 간 test-retest를 확보하기 전에는 **MDC로 승격하지 않는다.**

### 보정 3 — "정본 §5.3만 고치면 된다"는 내 요약이 너무 좁았다 (사용자 지적 타당)
내 직전 문장 *"유일하게 손봐야 할 곳은 정본 §5.3"*는 **내 자신의 분석과 어긋났다.** 함께 인정한 수정 대상은:
- §1.3 "라벨 오류에 면역" 표현
- A4·A0·D-15·D-18을 비교표·사전 조건에 포함
- 원시 depth 저장(수집기)
- L1 실데이터 실행
- §5.3 SPARC·C2 표현
→ "§5.3만"이 아니라 **">= 5곳"**이다. **정정한다.**

### 확인 (그대로 맞음)
- Li 2022 SPARC 사용: 일치
- 기존 SPARC 탈락 판정 보류: 일치
- 코드 있음 / 자체시험 통과 / 실험준비 완료의 **3단계 구분**: 정확
- "연구 방향은 정리됐고, 본실험 준비는 아직": 정확
- 추가 K2는 **L1의 정식 K2와 일치 확인 전까지 보조용으로 구분**: 타당 (작업본 K2는 미검토)

---

## Sources
- `experiments/l1_pipeline/k1k2_from_files.py` (입력 계약: docstring, `load_meta`, `read_landmarks`, `backproject`)
- `experiments/session_tools/make_session.py` (meta.json 템플릿: fx/fy/cx/cy/depth_scale)
- `capstone/호진파일/Mirror_therapy_clock_v3.py` (`_save_landmarks`/`_save_metadata`/`_intrinsics_dict`), 파일럿 `*_landmarks.csv`·`*_metadata.json`
- `outputs/research-plan-v6.md` §6.1·§6.2·§7·§9.2·§15.2·§15.3
- `outputs/protocol-v6-frozen.md` §0·§3
- `outputs/03-검증/self-review-check-20260929.md`(정정판), `outputs/03-검증/d15-status-verification.md`

## Blocked / Unverified
- 사용자가 "작업 폴더에 추가했다"고 한 **K2·원시 depth 저장 코드는 OneDrive에 반영 전**이라 **검토하지 못했다**(파일 미확인).
- 위 인터페이스 불일치는 **현재 OneDrive의 `clock_v3`(rev 3.1) 기준**이다. 작업본이 반영되면 재확인 필요.
