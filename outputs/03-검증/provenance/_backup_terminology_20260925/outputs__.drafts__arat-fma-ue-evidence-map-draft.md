# ARAT 및 FMA-UE 상지기능 자동화를 위한 8대 선행연구 증거 맵 — Draft

## Executive summary

핵심 결론은 다음과 같다.

1. FMA-UE와 ARAT는 신뢰도와 타당도가 높은 임상척도이지만, ordinal score, 평가자·프로토콜 의존성, 바닥/천장 효과, 이동의 질과 보상전략 압축이라는 구조적 한계를 가진다.
2. 운동학은 임상척도를 대체하기보다는 보완한다. 가장 일관된 후보는 운동시간, 속도, smoothness(SPARC/NMU), 체간 변위, 어깨·팔꿈치 운동과 peak aperture 관련 지표이다.
3. 자동평가 연구는 Kinect/RGB-D, IMU, RGB 비디오 순으로 발전했고 높은 상관·정확도를 보고하지만, 작은 표본, 항목 부분자동화, 단일 평가자, 환자 단위 외부검증 부족, 데이터 누수 위험이 흔하다.
4. 범용 VLM 단독 FMA 채점은 현재 불충분하다. Qwen2.5-VL-72B의 FMA 예측이 중증도 범위 전반에서 거의 일정해지는 직접 근거가 있다. 다만 `flatlining`과 `kinematic blindness`는 본 보고서가 사용하는 현상명이지 표준 임상용어는 아니다.
5. 비장애인 대비 뇌졸중 환자는 대체로 더 느리고, 덜 매끄럽고, 체간 변위가 크며, 어깨-팔꿈치 협응과 파지 개구가 달라진다. 고기능 환자에서는 end-point가 정상화되어도 proximal coordination과 보상은 남을 수 있다.
6. 정상 파지는 단일 평균이 아니다. 대규모 건강인 자료는 공통 시너지와 함께 강한 개인차를 보여준다. 그러나 6차원 GMM 하위유형 및 정상 매니폴드 이탈 백분위는 아직 검증된 표준이 아니라 합리적인 연구가설이다.
7. 무마커 RGB/RGB-D는 단순 ROM, movement time, 체간 변위에는 유용할 수 있지만 회전, 가림, 순간 속도, NVP/SPARC 같은 미분 기반 지표에는 오차가 커질 수 있다.
8. 가장 설득력 있는 설계는 VLM 단독이 아니라 `영상 + 명시적 운동학 JSON + 정상 하위유형/매니폴드 거리 + 규칙/확률 계층 + 임상가 확인`의 2단계 지식증강 구조다.

## 8-theme evidence map

| Theme | Strongest evidence | N | Key quantitative result | Main limitation | Directness |
|---|---|---:|---|---|---|
| 1 Clinical limits | Hsueh 2009; Kristersson 2019 | 53; 117 | ARAT early floor 38–42%; later ceiling ~21–23%; ICC generally high | floor/ceiling vary by stage | Direct |
| 2 Kinematic correlates | Alt Murphy 2012; Bayle 2024; Qiu 2022 | 30; 31; 8 | ARAT: NMU r=.81, time r=.68, trunk r=.63; SPARC–ARAT r=.68 | task and severity dependence | Direct |
| 3 Automated scoring | Wang 2024; BIONICS 2023; Li 2022 | 95; 45; 20 | total coefficient .960; item accuracy 78.1–82.7%; r=.981 | limited external validation | Direct |
| 4 VLM limitations | Li et al. 2025 preprint | 29 controls+51 stroke; FMA subset 899 videos/28 people | FMA prediction essentially constant and like score-1 baseline | preprint; one VLM family | Direct but preliminary |
| 5 Stroke vs healthy | Collins 2018 meta-analysis; Murphy 2011 | 460+324; 19+19 | peak velocity SMD −1.48; trunk SMD 1.55; trunk 77.2 vs 26.7 mm | study heterogeneity | Direct |
| 6 Healthy diversity | Jarque-Bou 2019; subject-pattern study 2020 | 77; 31 | 12 synergies >80%; person-ID 95.48% | not an ARAT cohort; GMM not established | Indirect |
| 7 Markerless validity | Faity 2022; Jo 2023; review 2025 | 26; 6; 14 studies | trunk ICC=.93 vs rotation .38; upper-limb error ~10–12° | mostly healthy/simple movements | Direct/indirect |
| 8 Knowledge augmentation | Ahmed 2024; Tang 2025; BiomechGPT | 478 videos; 10+10; 750 | HBM resolved 95%/98 disagreements; feature+LLM F1 .79/.73; motion-language r .88–.96 | limited direct ARAT/FMA validation | Direct + transfer |

## 1. Clinical limits of FMA-UE and ARAT

The strongest evidence does not support describing the scales as unreliable. Rather, the problem is loss of information despite high reliability. Hsueh et al. found interrater ICC ≥.92 and test-retest ICC ≥.97, yet ARAT showed a 41.5% floor at day 14 and ceiling above 20% at later assessments. Kristersson et al. similarly found ARAT floor effects of 38.4%, 30.2%, and 24.1% at 3 days, 10 days, and 4 weeks.

The scales are also observational ordinal summaries. ARAT score 2 can combine slow execution and compensation. Consequently, the same score does not identify why performance was abnormal. Recent cross-stage work found strong agreement between FMA-UE and ARAT categories but concluded that the scales alone could not distinguish restitution from compensation.

Clinical time burden should be presented carefully: typical reported administration is approximately 10 minutes for ARAT and approximately 20 minutes for FMA motor assessment, but setup, training, equipment, and severe impairment can add burden. The evidence supports saying `workflow burden and trained-rater dependence`, not that every ARAT is intrinsically long.

## 2. Kinematic correlates

### Metric definitions

- SPARC: negative arc length of the normalized Fourier magnitude spectrum of velocity; less negative values indicate smoother motion.
- PAp: maximum thumb-index aperture during reaching.
- TPAp: reach onset to peak aperture.
- TAPV: wrist peak velocity to onset of the subsequent transport phase.
- Trunk displacement: maximum thorax/sternum translation from the initial position; task-specific definitions vary.

Alt Murphy et al. provide a clinically interpretable anchor: in 30 people after stroke, ARAT correlated with smoothness/NMU (r=.81), total movement time (r=.68), and trunk displacement (r=.63); smoothness plus trunk displacement explained 67% of ARAT variance. Bayle et al. found baseline SPARC correlations of .48 with UE-FMA and .68 with ARAT, together with excellent reliability (ICC=.912).

Qiu et al. directly examined the requested grasp metrics in eight early-subacute patients. PAp, trajectory smoothness, reach duration and TAPV changed significantly; TPAp+PAp and TAPV+TPAp models explained adjusted 59.8% and 61.9% of UEFMA variation. Exact individual r values were not verifiable from accessible official text and should not be invented.

The principal inference is that no single metric is sufficient. SPARC captures temporal smoothness; PAp/TPAp capture grasp preshaping; TAPV captures late adjustment; trunk displacement captures compensation. Their complementarity justifies structured multimodal injection.

## 3. ML/DL automatic scoring

Early Kinect work on 41 patients scored 13 FMA items with 65–87% item accuracy. A 2022 RealSense/Leap/force system covering 30 voluntary FMA items reported r=.981 and average item accuracy 80.83% in 20 patients. Smartphone video in 45 acute patients scored 16/33 FMA items at 78.1–82.7% accuracy. A larger 2024 clinical validation in 95 inpatients reported a total-score coefficient of .960.

IMU studies offer good signal fidelity but require placement and calibration. A 2025 three-reaching-motion estimator in 11 stroke participants achieved 7% normalized RMSE under leave-one-subject-out validation. A separate 120-patient GRU study reported 92.66% item accuracy, R²=.9838 and RMSE=2.40, but dataset/session independence and transportability still require scrutiny.

ST-GCN is well suited to skeleton sequences, but much of the literature evaluates healthy or mixed rehabilitation datasets rather than item-level FMA/ARAT in representative stroke cohorts. The 2025 three-view ARAT preprint reported 89% validation accuracy in 500 segments from 50 patients, but reduced scores 2 vs 3 to a binary task and used a random segment split. Without an explicit patient-disjoint split, leakage cannot be ruled out.

## 4. VLM/LLM status and defects

The most direct study evaluated 29 controls and 51 stroke survivors. For FMA impairment, Qwen2.5-VL-72B was tested on 899 videos from 28 people. Predictions were essentially constant across severity and resembled a visual-blind baseline returning 1. This is direct evidence for score flatlining.

The same work states that VLMs failed to capture subtle kinematic detail, and dose estimation was comparable to a nonvisual Markov baseline except in structured mild/control cases after substantial prompting and post-processing. This supports describing a fine-grained motion-perception deficit, but `kinematic blindness` should be labeled an interpretive shorthand.

VLM-only failure is mechanistically plausible: sparse frame sampling removes velocity and smoothness detail; 2D appearance is ambiguous under occlusion; language priors can overwhelm visual evidence; ordinal prompts encourage central responses. A 14-frame protocol may aggravate temporal aliasing unless paired with explicit sensor-derived statistics.

## 5. Healthy versus stroke kinematics

A reach-to-grasp meta-analysis pooling 460 stroke and 324 controls found lower peak velocity (SMD −1.48) and greater trunk displacement (SMD 1.55). In a standardized drinking task, stroke participants had longer total time (11.4 vs 6.49 s), lower peak velocity (431 vs 616 mm/s), and greater trunk displacement (77.2 vs 26.7 mm).

These differences are not universal. In well-recovered patients, distal movement time and time-to-peak velocity may approximate controls while proximal elbow-shoulder timing remains altered. Therefore, normalizing only end-point performance can misclassify compensation as recovery.

## 6. Normal grasp variability, GMM and synergy manifold

The premise that normal grasp is heterogeneous is supported. In 31 healthy participants performing 1083 grasps, person-specific patterns based on joint angle and force could be classified with 95.48% accuracy; hand size alone did not explain the clusters. In 77 people performing 20 grasps six times, 12 synergies explained >80% of variation, while only the first three were common in more than half the participants and finer thumb/index patterns varied.

However, the literature located does not validate a specific six-dimensional GMM as a clinical normative reference for ARAT. GPLVM+GMM/GMR work on five people and 31 grasps provides a modeling precedent but not sufficient clinical evidence. Thus, GMM kinematic subtyping and percentile-based manifold distance should be framed as the proposed contribution and evaluated against simpler baselines: global z-score, sex/hand-size stratification, PCA Mahalanobis distance, and one-class models.

## 7. Markerless RGB-D validity

Markerless methods are metric-dependent. Kinect v2 versus Vicon in 26 healthy adults yielded trunk-displacement ICC=.93, but trunk-rotation ICC=.38 and poor reliability for NVP and peak velocity after filtering (ICC=.38 and .21). A six-person comparison found mean upper-limb angular errors of 11.56±3.74° for RealSense D415 and 9.98±3.79° for MediaPipe.

MediaPipe can perform well for simple planar ROM: elbow flexion ICC=.92 versus Qualisys in 22 healthy participants. Yet systematic reviews show heterogeneous results and consistently worse validity for complex rotation and occluded movement. Therefore, RealSense/MediaPipe validity cannot be expressed as one universal error or ICC.

A defensible system should report joint- and metric-specific agreement; use multi-view/depth for hand and trunk; validate PAp, TPAp, TAPV and SPARC directly against Vicon; and quantify missingness, jitter, and failure by impairment severity.

## 8. Multimodal knowledge augmentation

Ahmed et al. provide the closest direct precedent: in 478 stroke videos, a hierarchical Bayesian model linked computational kinematics to clinician-rated movement components, segments, and tasks; it resolved 95% of 98 rater-disagreement cases and aligned kinematics to task-segment combinations in >90%.

Tang et al. provide a direct LLM precedent for feature injection. With explicit exercise-specific joint features, GPT-4o certainty prompting achieved accuracy/F1 .76/.79 on UI-PRMD and .70/.73 on REHAB24-6. It still underperformed ST-GCN on UI-PRMD (.94 accuracy), was tested on healthy-only datasets, and generated feedback without quantitative ground truth.

BiomechGPT shows that tokenized motion can give language models clinically meaningful numerical competence at scale, with 750 participants and correlations .88–.96 for mobility regression tasks. This is transfer evidence, not direct ARAT evidence.

## Recommended architecture and evaluation

### Two-stage architecture

1. RGB-D/multi-view layer: pose, hand landmarks, object trajectory, event segmentation.
2. Deterministic metric layer: SPARC, PAp, TPAp, TAPV, trunk displacement, joint ROM, confidence/missingness.
3. Normal-reference layer: covariate-aware subtypes and manifold distance; report uncertainty.
4. Knowledge packet: 14 frames plus structured JSON containing raw values, percentiles, metric definitions, measurement confidence, and rule flags.
5. VLM reasoning layer: score explanation and candidate FMA/ARAT item score.
6. Safety layer: constrained output schema, calibration, defer-to-clinician threshold, evidence trace.

### Minimum evaluation

- Patient-disjoint nested cross-validation plus external-site holdout.
- Baselines: ordinal mean, demographics-only, video-only VLM, kinematics-only model, RGB-only model, and fused model.
- Outcomes: item weighted κ, total ICC, MAE/RMSE, calibration, Bland–Altman, ceiling/floor sensitivity, and compensation F1.
- Ablations: frames, depth, each metric family, subtype percentile, JSON, and clinical rules.
- Error strata: severity, paretic side, skin tone, hand size, occlusion, camera view, assistive support.
- Leakage audit at patient/session/trial level.

## Evidence-backed caveats and disagreements

- High scale reliability does not imply sensitivity to movement quality.
- High model-score correlation can coexist with poor item agreement or central-score bias.
- Healthy-data exercise benchmarks can exaggerate clinical generalization.
- SPARC is strongly supported for smoothness, but its value depends on segmentation and velocity quality.
- Markerless positional/angle validity does not automatically validate derivatives such as SPARC or TAPV.
- GMM subtype count must be selected by stability and external predictive utility, not visual cluster neatness.
- The direct VLM limitation evidence is currently a preprint and should be independently reproduced.

## Open questions

1. Does structured JSON eliminate FMA prediction flatlining in patient-disjoint testing?
2. Do subtype percentiles add information beyond hand size, object size and conventional z-scores?
3. Can markerless SPARC/TPAp/TAPV error remain below clinically meaningful change thresholds?
4. Does the model distinguish task success through compensation from restoration of joint coordination?
5. Are explanations faithful to metrics or merely plausible text?
6. What defer threshold achieves safe clinician-in-the-loop deployment?

## Recommended reading/reproduction priority

1. Reproduce the VLM flatlining result and add metric JSON.
2. Reproduce markerless-vs-Vicon validity for the exact proposed camera geometry and metrics.
3. Reproduce SPARC/PAp/TPAp/TAPV relations under patient-disjoint longitudinal evaluation.
4. Build normative subtypes only after covariate and stability checks.
5. Compare video-only, kinematics-only, and fused systems on compensation-sensitive labels.

## Sources

TODO: inline URLs and complete source list in cited version.
