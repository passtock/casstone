# Direct Research Notes — ARAT·FMA-UE 자동평가 증거 맵

- **Date:** 2026-09-22
- **Mode:** Lead-owned degraded direct mode (Workbench delegation disabled)
- **PDF policy:** PDF 직접 파싱 미수행. PubMed/arXiv 메타데이터, 초록, HTML 전문/검색 스니펫, 공식 저널 페이지를 사용.

## Exact search terms used

1. `FMA-UE ARAT clinical limitations ceiling floor effect administration time interrater reliability stroke DOI sample size`
2. `ARAT Fugl-Meyer upper extremity compensation trunk movement not distinguished impairment activity limitation review`
3. `FMA-UE ARAT psychometric properties ceiling effect floor effect stroke systematic review`
4. `SPARC PAp TPAp TAPV stroke upper limb kinematics clinical score correlation`
5. `"PAp" "TPAp" "TAPV" upper limb stroke`
6. `spectral arc length SPARC Fugl-Meyer ARAT correlation stroke reaching sample size`
7. `automatic Fugl Meyer upper extremity assessment IMU machine learning stroke accuracy DOI sample size`
8. `ST-GCN automatic Fugl-Meyer upper extremity assessment stroke skeleton video`
9. `three-view video automated upper limb rehabilitation assessment FMA ARAT deep learning`
10. `vision language model rehabilitation exercise assessment scoring video LLM VLM`
11. `multimodal large language model physical rehabilitation movement assessment kinematics sensor`
12. `Qwen2.5-VL rehabilitation motion assessment clinical scoring flatlining kinematic blindness`
13. `stroke versus healthy reach-to-grasp kinematics peak aperture time to peak aperture trunk displacement sample size DOI`
14. `healthy controls stroke patients upper limb kinematics reaching drinking trunk displacement FMA ARAT`
15. `stroke reach-to-grasp PAp peak aperture TPAp TAPV kinematics definitions`
16. `healthy grasp kinematic variability Gaussian mixture model grasp trajectories hand size kinematic subtypes`
17. `GMM clustering reach-to-grasp kinematics healthy participants grasp strategy`
18. `hand grasp synergy manifold healthy subjects PCA kinematic synergies sample size DOI`
19. `Intel RealSense upper limb kinematics validation Vicon ICC error stroke rehabilitation`
20. `MediaPipe upper limb joint angle validity Vicon ICC healthy subjects`
21. `markerless RGB-D upper limb motion capture reliability validity Vicon RealSense D435 error`
22. `"Automated ARAT Scoring" participant stroke sample size Ahmed 2024 hierarchical Bayesian`
23. `Ahmed 2024 ARAT multi-view video stroke hierarchical Bayesian movement quality`
24. `three camera ARAT stroke video dataset Ahmed hierarchical Bayesian model`
25. `"UEFMA" "TAPV" "peak aperture" stroke`
26. `"Rehabilitation Exercise Quality Assessment" GPT-4o accuracy UI-PRMD REHAB24-6`

## Database searches

- PubMed: `(Fugl-Meyer OR ARAT) AND (ceiling effect OR floor effect OR reliability OR validity) AND stroke`
- PubMed: `(SPARC OR spectral arc length OR trunk displacement OR peak aperture) AND stroke AND upper limb kinematics`
- PubMed: `(automatic OR machine learning OR deep learning) AND (Fugl-Meyer OR Action Research Arm Test) AND stroke AND upper limb`
- PubMed: `(RealSense OR MediaPipe OR RGB-D OR markerless) AND (Vicon OR validity OR reliability OR ICC) AND upper limb kinematics`
- arXiv metadata: `2511.17727`, `2505.18412`, `2505.01680`
- PubMed metadata: PMID 38693881, 39186425, 30776997, 36086392

## Evidence notes by theme

### 1. Clinical limitations

- Hsueh et al., 2009, *Psychometric Comparisons of 4 Measures...*, N=53 at day 14, N=35 completed day 180. ARAT floor/ceiling: 41.5/9.4% (day 14), 17.0/20.8% (day 30), 11.3/20.8% (day 90), 11.3/22.6% (day 180). Pairwise scale correlations ≥.81; interrater ICC ≥.92; test-retest ICC ≥.97. ARAT around 10 min but requires dedicated apparatus. DOI 10.2522/ptj.20080285.
- Kristersson et al., 2019, N=117. ARAT floor 38.4%, 30.2%, 24.1% at days 3, 10, week 4; ceiling 21.3% at week 4. DOI 10.2340/16501977-2534.
- Hernández et al., 2019, N=60. FMA-UE ceiling 21.7% in early stroke despite high agreement. DOI 10.2340/16501977-2590.
- Kim et al./Frontiers 2024: acute/subacute/chronic samples N=133/113/92; weighted κ=.76/.83/.81 between FMA-UE and ARAT categories, but scales cannot distinguish restitution from compensation. DOI 10.3389/fneur.2024.1429929.

### 2. Kinematic indicators

- Schwarz et al., 2019 systematic review: 225 studies, N=6197, 151 metrics. Only 30 studies examined clinimetrics. DOI 10.1161/STROKEAHA.118.023531.
- Alt Murphy et al., 2012, N=30 stroke: ARAT correlated with NMU smoothness r=.81, movement time r=.68, trunk displacement r=.63; NMU+trunk displacement explained 67% ARAT variance (unique 37% and 11%). DOI 10.1177/1545968312448234.
- Bayle et al., 2024, N=31: baseline SPARC correlations UE-FMA r=.48, proximal UE-FMA r=.56, ARAT r=.68; SPARC ICC=.912; change effect size=.76. DOI 10.1186/s12984-024-01382-1.
- Saes et al., 2021, N=40 stroke + 12 controls: SPARC longitudinal association with FM-UE B=31.73 (95% CI 27.27–36.20), within-subject B=30.85; recovery leveled after week 5. DOI 10.1186/s12984-021-00937-w.
- Qiu et al., 2022, N=8: PAp=largest index-thumb distance; TPAp=reach onset to PAp; TAPV=wrist peak velocity to transport onset. Significant pre/post changes in PAp, trajectory smoothness, reach duration, TAPV; kinematic measures significantly correlated with UEFMA. Exact individual r values not exposed in accessible HTML; two-variable models TPAp+PAp adjusted R²=59.8%, predictive R²=51.9%; TAPV+TPAp adjusted R²=61.9%, predictive R²=52.0%. DOI 10.1109/EMBC48229.2022.9871891.

### 3. Automated scoring

- Kim et al., 2016 Kinect, N=41: 13 FMA items, per-item accuracy 65–87%; summed 13-item score r=.873, total FMA relation r=.799. DOI 10.1371/journal.pone.0158640.
- Li et al., 2022 RealSense+Leap+force, N=20 stroke: all 30 voluntary FMA items; r=.981; item accuracy 80.83%, macro F1 80.97%; mean RealSense joint offset 96 mm vs Vicon. DOI 10.3390/brainsci12101380.
- BIONICS, 2023, N=45 acute stroke: smartphone RGB, 16/33 FMA items; item accuracy 78.1–82.7%, group correlation average .89. DOI 10.1177/15459683231184186.
- Wang et al., 2024, N=95 hemiparetic inpatients: depth+ML total-score coefficient .960; weak force-sensing items. DOI 10.1177/02692155241251434.
- Zhou et al., 2025, N=11 stroke: IMU from three reaches, LOSO normalized RMSE 7%, 70% of FMA items. DOI 10.1109/JBHI.2025.3542037.
- Ahmed & Rikakis, 2025 arXiv 2505.01680: 50 patients, 500 segments; three views; labels 2 vs 3 only; random 80/20 segment split; late fusion accuracy 89%, score agreement 91%. Risks: preprint, binary truncation, likely segment-level patient leakage because split described at segment level.
- Deb et al., 2022 ST-GCN: KIMORE/UI-PRMD generic rehabilitation datasets, not direct ARAT/FMA clinical validation. DOI 10.1109/TNSRE.2022.3150392.

### 4. VLM/LLM

- Li et al., 2025 arXiv 2511.17727: 29 controls + 51 stroke, 3448 trials. FMA experiment: 899 videos/28 subjects, Qwen2.5-VL-72B. Predicted FMA essentially constant; error similar to score-1 visual-blind baseline. Direct evidence for score flatlining. Paper says subtle kinematics not captured; `kinematic blindness` is a useful interpretive label, not its formal term.
- Tang et al., 2025 arXiv 2505.18412 (later book chapter DOI 10.1007/978-981-95-0568-5_5): feature-sequence + GPT-4o. Certainty prompting accuracy/F1 .76/.79 on UI-PRMD, .70/.73 on REHAB24-6. UI-PRMD ST-GCN .94/.96. Healthy-only datasets (10 subjects each); feedback only qualitatively evaluated; LLM overconfidence and uncontrolled randomness.

### 5. Stroke vs controls

- Collins et al., 2018 reach-to-grasp meta-analysis: 29 studies, 460 stroke + 324 controls; peak velocity SMD −1.48 (95% CI −1.94 to −1.02), trunk displacement SMD 1.55 (0.85–2.25). DOI 10.1016/j.physio.2017.10.002.
- Murphy et al., 2011, N=19+19: total time 11.4 vs 6.49 s; peak velocity 431 vs 616 mm/s; trunk displacement 77.2 vs 26.7 mm. DOI 10.1177/1545968310370748.
- van Kordelaar et al., 2012, N=46 stroke +12 controls: duration 1.93 vs 1.10 s; PCA separated pathological synergy and trunk compensation; DOI 10.1007/s00221-012-3169-6.

### 6. Healthy grasp diversity/subtyping/synergies

- Nisky et al./PLOS One 2020, N=31, 1083 grasps, five objects: subject classification 95.48%; hand size insufficient explanation. DOI 10.1371/journal.pone.0234969. Note: t-SNE+kNN, not GMM.
- Jarque-Bou et al., 2019, N=77, 20 grasps ×6: 12 synergies explain >80%; first 3 >50%; fine synergies subject-variable. DOI 10.1186/s12984-019-0536-6.
- Jarque-Bou et al., 2020, N=24, 24 ADL: 4 subject-specific PCs explain 77.3±1.9%; shared finger flexion cores but variable thumb/index strategies. DOI 10.1038/s41598-020-63092-7.
- Romero et al., 2010, N=5, 31 grasps: 2D GPLVM + GMM/GMR (≤3 Gaussians) models temporal grasp paths. Provides GMM precedent but tiny robotics sample, not a clinical normative subtype validation.
- Conclusion: a fixed six-dimensional GMM/percentile subtype is a defensible proposed method, not an already validated stroke-rehab standard.

### 7. Markerless validation

- Faity et al., 2022, N=26 healthy, Kinect v2 vs Vicon: trunk displacement ICC=.93; trunk rotation ICC=.38; filtered movement time/path ratio/time-to-PV/NVP/peak velocity ICC=.76/.51/.55/.38/.21. DOI 10.3390/s22072735.
- Jo et al., 2023, N=6: Qualisys reference; upper-limb absolute errors RealSense D415 11.56±3.74°, MediaPipe 9.98±3.79°. DOI 10.3390/s23010003.
- Scano et al., 2020, N=15, Kinect v2 vs Vicon: test-retest ICC .73–.82 point-to-point and .62–.84 exploration depending workspace. DOI 10.3390/mti4020014.
- Systematic review Lee et al., 2025: 14 studies; simple flexion/abduction generally more valid than rotations; reliability/validity heterogeneous; two RealSense studies only. DOI 10.3389/fbioe.2025.1570637.
- MediaPipe vs Qualisys, N=22: elbow flexion ROM ICC=.92; DOI 10.1016/j.jbmt.2024.04.033.

### 8. Knowledge augmentation

- Ahmed et al., 2024, 478 videos; HBM maps extracted kinematics→composite features→segments→tasks; 95% of 98 rater disagreements resolved, >90% kinematic/task-segment alignment. DOI 10.1109/TNSRE.2024.3450008.
- Tang et al., 2025: engineered angle/stability features provided to GPT-4o improve/enable natural-language assessment; quantitative classification values above.
- UbiPhysio, arXiv 2308.10526: 104 participants, 25 actions, 9548 instances; clinically designed biomechanical features + retrieval-enhanced GPT-4 feedback. Not stroke/ARAT validated.
- BiomechGPT, arXiv 2505.18465: 71.1 hours, 750 participants, 10 tasks; motion tokens; activity F1=.91, impairment presence F1=.88; cadence/speed/TUG/FSST r=.95/.96/.88/.89. Primarily lower-limb/mobility, not ARAT/FMA.

## Exclusions / downgraded claims

- `Flatlining`: supported descriptively by arXiv 2511.17727 Figure 5, but not established as a standardized clinical term.
- `Kinematic Blindness`: not found as a formal term in the focal literature; use only as a label for failure to perceive fine-grained kinematics.
- Exact Pearson r values for Qiu 2022 PAp/TPAp/TAPV were not accessible from official HTML/metadata; report significance and verified model R² only.
- Direct evidence for GMM on a six-dimensional healthy ARAT/reach-to-grasp subtype and percentile deviation was not found. Mark as a proposed research contribution.
- Three-view ARAT 89% study is an arXiv preprint with binary 2-vs-3 labels and segment-level random split; not clinical SOTA proof.
