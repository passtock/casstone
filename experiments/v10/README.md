# experiments/v10 — v10 계획서 실행 코드

**대응 계획서:** `capstone/실험계획서_v10_최종본.md`
**작성:** 2026-10-01 · **오라클:** 63 checks / 0 FAIL

| 모듈 | 대응 절 | 역할 |
|---|---|---|
| `l2_metrics_v10.py` | §7, §8.2 | M1(MGA)·M2(추정 TAM_total)·M4(SPARC)·M5(TD) + Q 규칙 |
| `conditions_v10.py` | §9, §10, §11.3 | 비환자 참고 분포 + A1·A2·A3·R·A4·A1n·A2-noRef·A3-hand 프롬프트 생성 |
| `analysis_v10.py` | §12 | 환자 통합 MAE · 고정순서 검정(PR-2→PR-3→PR-1) · 환자단위 부트스트랩 · Holm 민감도 |

## 실행

```bash
# 오라클 (외부 데이터 불필요)
PYTHONIOENCODING=utf-8 python experiments/v10/l2_metrics_v10.py --selftest
PYTHONIOENCODING=utf-8 python experiments/v10/conditions_v10.py --selftest
PYTHONIOENCODING=utf-8 python experiments/v10/analysis_v10.py --selftest

# 실데이터
python experiments/v10/l2_metrics_v10.py --landmarks <trial>_landmarks.csv --hand Right \
    --pose <trial>_pose_landmarks.csv --anterior-axis 1,0,0 --out l2.json
python experiments/v10/conditions_v10.py --trials trials.json --ref-rows ref_rows.json --out conditions.jsonl
python experiments/v10/analysis_v10.py --preds preds.csv --refs refs.csv --out report.json
```

> ⚠️ Windows에서 `PYTHONIOENCODING=utf-8` 없이 실행하면 cp949 em-dash 오류로 크래시한다(기존 `experiments/`와 동일).

## 계획서 명시 사항만 구현한 것 (임의 확장 금지)

- **M1**: Hands world landmark 4–8 거리 **최댓값**. **150 mm 상한 절단 없음**, 초과 프레임 수를 계수로 보고(§7.1). P95는 보조 저장.
- **M2**: 14개 굴곡각(엄지 2 + 네 손가락 × 3) 합의 **P95**. 각 = 180 − 내각(§7.1).
- **M4**: 손목 3D 속력의 SPARC. **손목 경로를 Hands와 분리**(§7.2). 소스는 Pose 손목 우선, 없으면 Hands wrist(0)이며 `source` 태그로 구분.
  `sparc_ref.sparc`(참조구현 일치 검증)를 그대로 재사용, `fc=min(10, fs/2)`.
- **M5**: 어깨 중점의 **탁자 전방 변위**. 전방축은 **외부 입력 필수**(ArUco 탁자 좌표, §6.2). 없으면 `value=null, reason=no_anterior_axis`.
- **Q**(§8.2): 값 산출과 품질 판정 분리. 하드 결측 ≠ 품질 미달.
- **A2 vs A3**: 같은 시행·같은 영상·같은 라벨, **수치 집합만** 다름.
- **R**: A3가 보류하지 않은 시행으로 후보를 제한하지 않고, **원래 유한값이 있는 전체 P**에서 지표별로 A3 추가 보류 수만큼 비복원 무작위(§10). seed 20261001/2/3.
- **A3-hand**: T1·T2만, 손 지표만. **T3에는 만들지 않음**(§10).

## 알려진 제약 (Blocked / Unverified)

| 항목 | 상태 | 설명 |
|---|---|---|
| Pose 입력 | **Blocked** | 촬영 앱(`Mirror_therapy_clock_v3.py`)에 MediaPipe Pose가 **없다**. Pose 파일을 주지 않으면 M4는 Hands wrist 폴백, M5는 `no_pose` null. |
| 절대 정확도 | **Unverified** | 독립 모션캡처 비교 없음(§7.5). |
| 카메라 시야 | **Unverified** | 체간·머리 위가 프레임에 들어오는지 치구/팬텀 실측 필요. |
| 프레임레이트 | **⚠️ 확인됨** | 파일럿 실측 13.4–24.6 fps. §8.2 손목 Q 임계(초 단위)가 이 fps에서 100% 탈락을 만든다 → `experiments/results/v10_wrist_q_audit_pilot.json` |

## 산출 근거 파일

- `experiments/results/v10_l2_metrics_v10_oracle.txt` (20 PASS)
- `experiments/results/v10_conditions_v10_oracle.txt` (24 PASS)
- `experiments/results/v10_analysis_v10_oracle.txt` (19 PASS)
- `experiments/results/v10_pilot_l2_demo.json` (파일럿 16레코드 실측)
- `experiments/results/v10_wrist_q_audit_pilot.json` (손목 Q 탈락률 감사)
