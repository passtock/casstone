# 자체점검 문서 검증 — 정정판 (2026-09-29, 2차)

> **정정 이력:** 1차 검토(같은 날)에서 **두 건을 잘못 판정**했다. 사용자의 반증을 받아 **원문 PDF(MDPI, 18p)를 직접 내려받아 재검증**했고, 아래를 정정한다.
> - 🔴 **정정 1:** "Li 2022는 SPARC를 쓰지 않는다" → **틀렸다. Li 2022는 RealSense + SPARC를 실제로 쓴다.**
> - 🔴 **정정 2:** "96 mm·Vicon을 확인 못 했다" → **틀렸다. 원문 §2.3.2에 명시되어 있다.**
> - 🔴 **정정 3:** "SPARC는 C2 탈락(102% vs 98.9%)이 맞다" → **타당하지 않다.** 그 102%는 **시간 오류가 있던 구 파일럿 값**에서 계산됐다.
> 원인: 1차 검토는 **섹션 스니펫에만 의존**했고 전문을 읽지 않은 채 "SPARC 언급 없음"이라고 **과잉 단정**했다. 재현 경로: `scratch/verify/li2022.pdf`(MDPI 원본).

검증 대상: 사용자의 "현재 상태 점검 + 실험 주의사항 + 교수님 예상질문·답변" 문서(2026-09-29).

---

## 0. 정정 후 결론

사용자 문서는 **대체로 정확**하다. 1차 검토에서 내가 제기한 "고칠 것" 중 **Li 2022 관련은 내 오류**였고, **SPARC 탈락 판정 문제는 사용자가 옳다.** 실제로 남는 고칠 것은 **① 도구 귀속**과 **② 비교 조건 표 보완** 정도다.

| 항목 | 1차 판정 | **정정 후** |
|---|---|---|
| `clock_v3` vs v6 파이프라인 혼동(도구 귀속) | 🔴 고칠 것 | 🔴 **유지(타당)** |
| Li 2022가 SPARC 미사용 | 🔴 인용 불일치 | ✅ **내 오류 — 철회. 사용자 주장이 맞다** |
| 96 mm 미확인 | 🟠 | ✅ **내 오류 — 원문 §2.3.2에서 확인** |
| SPARC MDC 102% 탈락이 정당 | ✅ 정확 | ❌ **사용자 지적이 옳다 — 판정 근거 무효** |
| 조건 표 A4·A0 누락 | 🟠 보완 | 🟠 **유지** |
| "라벨 오류 면역" 표현 | 🟡 조정 | 🟡 **사용자 제안 문장이 더 정확** |

---

## 1. 정정 1 — Li 2022는 RealSense + SPARC를 쓴다 (내가 틀렸다)

근거(원문 PDF 직접 검증, `scratch/verify/li2022.pdf`):

- **Table 3** (Feature 매핑): `31 | SPARC | Spectral arc length` 항목이 존재. Table 1에서 **31번 = Tremor**, 센서는 **RS(RealSense)**.
- **Shoulder/Elbow Endpoint** 특징 목록에도 `Spectral arc length`가 명시(Table 3 상단).
- **§2.3.3**: *"For the Coordination/Speed part, the parameter L of the SSA algorithm was slightly adjusted so as to avoid removing motion details and **maintain the tremor information for item 31**."*

→ **"RealSense와 SPARC를 함께 사용한 사례"라는 사용자 인용은 정확하다.** 단 사용자가 붙인 제한 — *"우리 PIP 각속도 SPARC와 같은 구현을 검증한 논문은 아니다"* — 도 정확하다(Li 2022의 SPARC는 **tremor feature**로, keypoint endpoint 기반이다).

**정정 문장:** 1차 검토의 *"이 논문은 SPARC를 쓰지 않는다"* → **철회.** 정확한 서술은 **"Li 2022는 RealSense 키포인트로 tremor 판정에 SPARC를 사용했다. 다만 우리 PIP 각운동 SPARC 구현의 타당도를 대신 검증하지는 않는다."**

## 2. 정정 2 — 96 mm·Vicon은 원문에 있다 (내가 틀렸다)

근거(원문 §2.3.2, 직접 인용):
> *"…the four motions (I, II, III, V) were **54, 43, 138, 150 mm**, respectively, with a **mean offset of 96mm**, which was acceptable and close to that of Kinect V2 (72 mm) [32]."*
> *"Regarding the data with high confidence collected by **Vicon** as the baseline…"*

→ **사용자 문서의 ③(54/43/138/150, 평균 96 mm, Vicon 기준)은 정확하다.**
→ 그리고 사용자의 단서도 옳다: 이는 **"RealSense 장치 자체의 깊이 오차 = 96 mm"가 아니라**, **SSA 처리·관절 추적을 포함한 손목 위치 비교 결과**다. 원문도 "processed by SSA" 맥락에서 서술한다.
→ 계획서 §2 ②의 *"Li 2022 (N=20, RealSense vs Vicon) 손목 위치 평균 96 mm 오차"*는 **문구를 다듬을 필요**가 있다: "장치 오차"로 읽히면 오해다. **"Vicon 기준 대비, SSA 처리 후 손목 위치 차이 평균 96 mm"**가 정확하다.

---

## 3. 정정 3 — SPARC MDC 102% 판정은 무효 (사용자가 옳다)

사용자 지적: *"102%는 시간 오류가 있던 기존 값에서 계산했으므로 수정 후 지표 판정에 쓸 수 없다. Wagner의 98.9%는 그 연구의 관측치이지 보편 탈락 기준이 아니다."*

**검증 결과 — 지적이 타당하다.**

1. **데이터 출처가 구 파이프라인이다.** `experiments/analysis/metric_portfolio_check_v2.py`:
   ```
   ROOT = "capstone/호진파일/outputs/데이터_저장"      # 구 파일럿
   SPARC = ["SPARC"]
   ```
   이 CSV는 **`Time_Base` 열이 없다**(= V-1 시계 교정 이전 산출물). `SPARC` 열 값은 예: **−11.589**(교정 후 파이프라인은 사이클 평균 ≈ −2.8, CHANGELOG 기록).
   → **102.0%는 시간 오류·구 SPARC 정의로 계산된 값**이다. 교정 후 지표의 편입 판정에 쓸 수 없다.

2. **임계값 사용이 부적절하다.** Wagner 2008(PMID 18326055)은 **MDC 7.4–98.9%의 범위**를 *관측*했고, "peak velocity 등 일부 변수는 >50% 변해야 실제 변화"라고 보고했다. **98.9%는 특정 연구의 최대 관측치**이지, **다른 지표의 보편 탈락 컷오프가 아니다.** 계획서 §5.3의 *"Wagner 최대치 98.9% 초과 = 사실상 측정 불가"*는 **근거를 넘겨 쓴 표현**이다.

→ **정본 §5.3 수정 권고:**
- SPARC(MD 102%) 판정을 **"교정 후 데이터로 재계산 전까지 보류(pending)"**로 강등.
- C2의 "50%"는 **Wagner가 보고한 취약 지표의 실용 기준**으로만 쓰고, **98.9%를 탈락 컷오프로 쓰지 않는다.**
- **"반복 SD 기반 계산을 MDC95로 부르지 않는다"** — `metric_portfolio_check_v2.py:76`은 `1.96·√2·SD`(반복시행 SD)로 계산한다. 이는 **test-retest MDC**의 한 형태지만, **같은 사람·같은 세션 반복**이라 "재측정 신뢰도"로 명명하려면 **세션 간(test-retest) 설계**가 필요하다. 명칭을 **"반복시행 기반 MDC 근사"**로 낮추는 것이 정확하다.

---

## 4. 유지되는 지적 — 도구 귀속 (사용자도 이 부분은 인정)

- `clock_v3`에는 **손목 3D 속도 P95(K2) 계산이 없다**(코드 확인: PIP 각속도 `ang_velocity`·SPARC·TAM/MGA만). 원시 depth PNG 저장도 없다.
- 실제 **K1·K2·Q는 `experiments/l1_pipeline/k1k2_from_files.py:266-307`에 구현**되어 있다.
- **단, "구현돼 있다"와 "실데이터로 검증됐다"는 다르다** → 실제 실행 이력은 **없음**(D-16: 원시 depth 부재).
- 사용자가 "L1 구현 여부를 아직 확인하지 않았다"고 한 것은 정직한 태도다. **확인 결과: 구현은 있다(코드·오라클 `--selftest`), 실데이터 실행은 없다.**

---

## 5. 사용자가 추가로 받아들인 항목 (동의)

- **A4**(영상 없이 수치만) → 영상의 추가 가치; **A0**(로지스틱 회귀) → VLM 필요성. 설명용 전체 설계에 포함.
- **D-15**(조건 생성기 정합)·**D-18**(보조 모델 확정) → 본평가 전 확인 항목(2026-09-29 D-15 부분 해소, D-18/D-16 미해결).

## 6. 라벨 잡음 표현 — 사용자 제안 문장 채택 권고

사용자 제안이 더 정확하다. 계획서 §1.3의 *"면역"* 표현은 다음으로 대체 권장:
> "동일한 영상과 참조 라벨을 사용해 조건 간 비교를 맞춘다. 다만 참조 라벨 오류의 영향이 제거되는 것은 아니며, 평가자 간 일치도와 민감도 분석을 함께 확인한다."

---

## 7. 최종 정리

| 사용자 문서 항목 | 판정 |
|---|---|
| ① 도구 귀속 정정 요청 | ✅ **타당** (K1·K2는 L1 도구에 구현, 실데이터 실행은 없음) |
| ② Li 2022가 RealSense+SPARC 사용 | ✅ **맞다** (내 1차 판정이 틀렸음) |
| ③ §2.3.2 96 mm·Vicon | ✅ **맞다** (원문 확인) |
| ④ SPARC MDC 102% 판정 무효 | ✅ **맞다** (구 파일럿 데이터 + Wagner 오용) |
| ⑤ A4·A0·D-15·D-18 보완 | ✅ 타당 |
| ⑥ "면역" 표현 완화 | ✅ 타당 |

**최종 권고:** 사용자 문서는 **그대로 사용 가능**하다. 다만 ④를 반영해 **계획서 §5.3의 SPARC 판정과 C2 임계 표현을 수정**해야 하며, 이 수정은 **교정 후 데이터로 SPARC를 재계산한 뒤** 확정하는 것이 맞다. 내 1차 검토의 **Li 2022·96 mm 관련 지적은 철회**한다.

---

## Sources (직접 검증)
- Li Y, Li C, Shu X, Sheng X, Jia J, Zhu X. *A Novel Automated RGB-D Sensor-Based Measurement of Voluntary Items of the FMA-UE: A Feasibility Study.* Brain Sci. 2022;12(10):1380. PMID **36291314** · doi **10.3390/brainsci12101380** · PMC9599696. **원문 PDF 직접 확인**: Table 3(item 31 SPARC), §2.3.2(54/43/138/150 mm, mean 96 mm, Vicon baseline), §2.3.3(SSA L 조정·tremor 보존). 로컬 사본: `scratch/verify/li2022.pdf`
- Wagner JM, et al. Phys Ther 2008;88(5):652-63. PMID **18326055** · doi **10.2522/ptj.20070255** (MDC 7.4–98.9% **범위**)
- Kwakkel G, et al. SRRR2 consensus. Int J Stroke 2019. doi **10.1177/1747493019873519** · PMID **31660781**
- Yozbatiran N, et al. Neurorehabil Neural Repair 2008;22(1):78-90. doi **10.1177/1545968307305353** · https://escholarship.org/uc/item/9v02m4c7
- Balasubramanian S, et al. J NeuroEng Rehabil 2015;12:112. PMID **26651329** · doi **10.1186/s12984-015-0090-9**
- 워크스페이스: `outputs/research-plan-v6.md` §1.3·§5.3, `experiments/analysis/metric_portfolio_check_v2.py`, `experiments/l1_pipeline/k1k2_from_files.py`, `capstone/호진파일/*`

## Blocked / Unverified
- 본 정정판의 Li 2022 내용은 **원문 PDF로 직접 확인**했다. 1차 검토의 해당 지적은 **철회**한다.
- 계획서 §5.3 SPARC 판정은 **교정 후 데이터로 재계산 전까지 확정 불가**(현재 "보류"로 두는 것이 맞다).
