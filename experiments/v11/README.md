# experiments/v11 — v10의 두 블로커(P1·P2) 해결 코드

**대응 계획서:** `capstone/실험계획서_v10_최종본.md`
**작성:** 2026-10-01 · **오라클:** 52 checks / 0 FAIL (19 + 13 + 20)
**원칙:** `experiments/v10/` **기존 코드는 수정하지 않는다.** 필요한 부분만 import 해서 재사용하고, 막힌 두 지점을 새 모듈로 구현한다.

| 모듈 | 해결 | 대응 |
|---|---|---|
| `pose_offline.py` | **P1** — 촬영 앱에 Pose가 없어 M4·M5를 못 만들던 문제 | 저장된 `original.avi`를 **사후 처리**해 Pose 롱포맷 CSV 생성 |
| `qrobust.py` | **P2** — §8.2 손목 Q가 파일럿 fps에서 100% 탈락시키던 문제 | 임계를 **dt 배수 + 결측률**로 재정의 |
| `l2_metrics_v11.py` | 위 둘을 v10 지표 정의에 연결 | v10의 M1·M2·M4 계산을 **import 재사용**, M5는 두 정의로 구현 |
| `run_session_v11.py` | 세션 순회 러너 | 시행 폴더 순회 → L2 + 구/신 Q 감사 |

## 1. P1 해결 — 오프라인 Pose

```bash
python experiments/v11/pose_offline.py \
    --video "<session>/original.avi" \
    --timestamps "<session>/video_timestamps.csv" \
    --out "<session>/pose_landmarks.csv"
# 원시 depth까지 있으면 카메라 좌표도 함께:
python experiments/v11/pose_offline.py --video v.avi --timestamps ts.csv \
    --depth-dir "<session>/raw_rgbd" --intrinsics fx,fy,cx,cy --out pose.csv
```

- 출력 CSV는 v10 `load_pose_csv`가 그대로 읽는다(오라클에서 호환 검증).
- `MP_*` = world landmark(**원점 = 골반 중점**). `RS_*` = 카메라 좌표(depth+내부파라미터 있을 때만, 없으면 `no_depth`).
- 부산물: `*.meta.json` — 출처·모델 복잡도·프레임 수 + **FOV 보고**(부위별 visibility 비율).

**실측(파일럿 20260915, 1,825프레임, 36.8초 소요):**

| 부위 | vis≥0.5 프레임 비율 | 중앙 visibility |
|---|---|---|
| nose | 100.0% | 1.000 |
| L/R shoulder | **100.0%** | 1.000 |
| L/R wrist | 100.0% / 95.9% | 0.988 / 0.987 |
| L/R hip | 99.5% / 100.0% | 0.933 / 0.936 |

→ **체간이 실제로 화면에 들어온다.** 이전 세션의 "손 중심 배치라 체간이 프레임 밖일 것"이라는 우려는 이 세션에서 **반증**됐다. (T3의 "머리 위 도달"은 이 영상이 자유 과제라 검증되지 않음 — 미확인 유지.)

## 2. P2 해결 — dt 상대 Q

| 새 규칙 | 정의 | 구(v10 §8.2) |
|---|---|---|
| `max_gap_ratio` | `max(dt)/median(dt)` | `max_gap ≤ 0.10 s` (절대) |
| `missing_frac` | 기대 격자 대비 결측 표본 비율 | `interp_frac ≤ 0.10` |
| `motion_noise_ratio` | 이동 구간 P99 속력 / 정지 구간 P95 속력 | (없음) |

- `motion_unresolved`는 **임상 실패와 분리**해 `flags`로 따로 노출한다(v10 §7.2 요구).
- `calibrate()`는 **추적 통계만** 받는다. `score`·`mae`·`arat`·`vlm` 등 결과 필드가 들어오면 **예외를 던진다**(v10 §8.2 "점수·정답률로 최적화 금지" 강제).

**통제 실험(결측 0, 내용 동일, fps만 다름):**

| 조건 | 구(v10 절대초) | 신규칙 |
|---|---|---|
| 13.4 fps | ❌ 탈락 (`max_dt` 0.117 s) | ✅ **통과** |
| 30.0 fps | ✅ 통과 | ✅ 통과 |

→ 구규칙의 탈락은 **데이터 문제가 아니라 임계의 프레임레이트 의존성**이었음이 분리 증명됐다.

## 3. M5(체간) 두 정의 — 좌표계 문제 회피

world landmark의 원점이 골반이라 **전역 이동은 복원 불가**하다(실측: hips mid ≈ 0,0,0). 그래서 두 값을 모두 낸다.

| 정의 | 축 필요 | 의미 | ARAT 대응 |
|---|---|---|---|
| **`TD_lean`** (기본) | **불필요** | `max_t ‖horizontal(P_sh_mid − P_hip_mid)‖ − 기준선` (mm) | 등받이 접촉 상실 = 상체가 골반 수직축에서 벗어남 |
| `TD_forward` | **필요**(ArUco 탁자축) | 전방축 성분의 구간 최대 (mm) | 전역 전방 이동(의자에서 미끄러짐) |

- ⚠️ 수평면은 **(x, z)** 다. MediaPipe world landmark의 수직축은 **y** (작성 중 이 축을 (x,y)로 잘못 잡아 TD가 0이 되는 버그를 오라클이 검출·수정).
- `td_mode`로 어느 쪽을 쓸지 명시하고, 축이 없으면 `TD_forward`는 `no_anterior_axis` + null.

## 4. 파일럿 실측 요약 (`experiments/results/`)

| 파일 | 내용 |
|---|---|
| `v11_pilot_session_summary.json` | 8시행 × 좌우 = 16레코드. **TD 16/16 산출**(P1 해결), M1 84.4–114.9 mm, SPARC −4.09 ~ −7.18 |
| `v11_pilot_frame_drop_audit.json` | 시행당 **1.8–14.1% 프레임 실제 누락**, 최대 13프레임 연속 드롭 |
| `v11_ab_comparison.json` | 구/신 Q 통제 비교 + 파일럿 탈락 사유 분해 |
| `v11_*_oracle.txt` | 오라클 로그 3종 |

**파일럿 Q 탈락 사유 분해(손목):** 실제 드롭 + 과제 특성의 복합.

| 사유 | 레코드 |
|---|---|
| 실제 드롭 + 손목 이동 없음 | 15 / 16 |
| 손목 이동 없음만 | 1 / 16 |

- `gap_ratio_exceeded` / `missing_frames` = **실제 프레임 드롭 검출**(오탐 아님, `v11_pilot_frame_drop_audit.json`로 확인).
- `motion_unresolved` = 이 파일럿은 **손을 탁자에 대고 여닫는 자유 과제**라 손목이 거의 이동하지 않음 → 정상 동작.
- `unstable_trunk_baseline` 16/16 = 파일럿에 §6.3.1의 **"정지 2초 기준선"이 없음**. 프로토콜 적용 후 재측정 대상.

## 5. 실행

```bash
# 오라클 (외부 데이터 불필요)
PYTHONIOENCODING=utf-8 python experiments/v11/qrobust.py --selftest
PYTHONIOENCODING=utf-8 python experiments/v11/pose_offline.py --selftest
PYTHONIOENCODING=utf-8 python experiments/v11/l2_metrics_v11.py --selftest

# 실데이터
python experiments/v11/pose_offline.py --video <s>/original.avi --timestamps <s>/video_timestamps.csv --out <s>/pose_landmarks.csv
python experiments/v11/run_session_v11.py --session <s> --out summary.json
python experiments/v11/qrobust.py --series series.json --calibrate --out calib.json
```

> ⚠️ Windows에서 `PYTHONIOENCODING=utf-8` 없이 실행하면 cp949 em-dash 오류로 크래시한다(기존 `experiments/`와 동일). MediaPipe는 첫 실행 시 `pose_landmark_lite.tflite`를 내려받는다.

## 6. 남은 것

- TD를 채점에 쓰려면 **§4.4 룰북·§9.2 프롬프트에 "몸통이 등받이에서 완전히 떨어지면 2점"** 명문화가 필요하다(v10 D1). `conditions_v10.py`의 프롬프트에는 이미 포함돼 있으나 **연구자 승인 항목**이다.
- `qrobust`의 기본 임계(2.5 / 0.15)는 **권고 초기값**이다. §8.2대로 **승인된 내부 점검 자료에서 `calibrate()`로 확정**하고 해시로 동결해야 한다.
- T3의 "머리 위 도달" 프레임 포함 여부는 실제 T3 촬영으로만 확인된다.
