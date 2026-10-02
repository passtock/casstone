# Research Proposal

## Development of a Pneumatic Glove-Based Master-Slave Mirror Therapy System and an RGB-D / Feature-Grounded Vision-Language Model for Upper-Limb Functional Assessment

- **Institution**: Handong Global University, School of Mechanical and Control Engineering / Human Robotics Lab  
- **Author**: Undergraduate Researcher Lee Jeayong  
- **Date**: September 4, 2026 (Final Methodologically Verified Edition)  

---

## 0. Revision Summary

This proposal incorporates formal academic feedback and rigorous literature cross-examination, establishing six verified methodological updates to ensure clinical and engineering integrity.

| Category | Original Draft | Final Verified Framework | Scientific Rationale |
| :--- | :--- | :--- | :--- |
| **Sensor Roles** | Camera role was described as potentially contributing to closed-loop actuation. | Actuation control from master to slave is dedicated strictly to flex sensors; the camera system is fully decoupled as an independent diagnostic assessor. | Eliminates visual processing latency and prevents self-occlusion artifacts caused by glove materials. |
| **Patient Trial Design** | Head-to-head equivalence design comparing the pneumatic glove directly against standard rehabilitation. | Add-on feasibility design: Group A (standard rehabilitation alone) vs. Group B (standard rehabilitation plus glove intervention add-on). | Ensures ethical patient safety and targets preliminary non-parametric effect size estimation. |
| **Assessment Timing** | Clinical scores measured only once at baseline. | Dual measurement protocol: baseline and 4-week post-intervention completion. | Captures longitudinal motor recovery trajectories. |
| **Objective 1 Core Metric** | Attempted direct metric quantification of fine finger individuation. | Fine individuation excluded due to signal-to-noise ratio collapse; redefined around robust coarse kinematics and a Feature-Grounded Vision-Language Model pipeline. | Overcomes camera noise floors by tracking macroscopic physical signals. |
| **Objective 1 Validation** | Standalone camera classification model. | Three-Arm comparative validation (Pure Video Baseline, Kinematic JSON Ablation, Proposed Multimodal Grounding) against recent literature benchmarks. | Directly addresses documented score flatlining in vision-language models (arXiv:2511.17727). |
| **Statistical Analysis** | Core claims relied on binary classification accuracy and area under the curve. | Shifted to non-parametric statistics, Spearman rank correlations, and rank-biserial effect sizes tailored for small-sample pilot validation. | Mitigates small-sample overfitting and avoids asymptotic p-value misinterpretations. |

> [!NOTE]
> **Note on Task Selection**: The exploratory individual finger extension task present in earlier iterations has been intentionally excluded. This deliberate omission maintains strict experimental focus on the prehension boundary defining Brunnstrom Stages 4 and 5 (lateral, cylindrical, spherical) while avoiding kinematic noise traps associated with Stage 6 isolated joint movements.

---

## 1. Research Background & Significance

### 1.1 Limitations of Conventional Mirror Therapy and Necessity of Physical Actuation
Traditional mirror therapy projects the visual reflection of the unaffected limb onto the affected side to stimulate the mirror neuron system and promote motor recovery. However, because the affected limb remains passively motionless, this approach induces a sensory mismatch between visual feedback and proprioceptive input while failing to provide objective, quantitative feedback regarding active range of motion recovery. 

The proposed master-slave pneumatic glove system addresses this limitation by physically replicating the real-time kinematics of the unaffected hand onto the paretic hand. This synchronizes visual and somatosensory inputs through multi-sensory feedback. The system operates across 5 coupled finger channels with 1 degree of freedom flexion and extension assistance, utilizing 5 embedded flex sensors on the master unit to achieve low-latency tracking on the slave unit.

### 1.2 Documented Limitations of Standard Clinical Assessment Scales
The rationale for establishing a separate, vision-based digital assessment pipeline does not stem from an inherent lack of reliability in existing clinical metrics, but rather from structural constraints documented across neurorehabilitation literature:

- **Fugl-Meyer Assessment for Upper Extremity (FMA-UE)**: Demonstrates excellent inter- and intra-rater reliability, but standard clinical administration requires 30 to 45 minutes of dedicated evaluation by trained clinicians (Gladstone et al., 2002), severely restricting routine longitudinal monitoring. Its 3-point ordinal scale (0, 1, 2) is too coarse to capture small but functionally meaningful joint improvements and exhibits ceiling effects among moderate-to-mild cases.
- **Brunnstrom Recovery Stages (BRS)**: Lacks rigorous psychometric validation as an interval scale and is frequently misapplied by treating ordinal stages as continuous data. Classification between adjacent stages is qualitative, operator-dependent, and prone to boundary ambiguities.
- **Action Research Arm Test (ARAT)**: Although reliable, it exhibits a documented ceiling effect in patients with mild finger impairments (Hsieh et al., 1998; Chen et al., 2009), often scoring compensatory grasping strategies with top-tier marks as long as the functional object is transferred within the target time.
- **Box and Block Test (BBT)**: Exhibits severe floor effects among moderate-to-severe hemiparetic patients who cannot execute isolated gross grasp-and-release actions.

### 1.3 Rationale for Targeting Brunnstrom Stage 4 to 5 Patients
In stroke motor recovery, Stages 4 and 5 represent the definitive transitional boundary where pathological mass synergy patterns break down and isolated joint individuation emerges:

- **Stage 4 Definition**: Spasticity begins to decline; patients achieve the ability to execute lateral prehension (key pinch) and initiate thumb-driven release.
- **Stage 5 Definition**: Relative independence from synergy patterns emerges, enabling palmar prehension, cylindrical grasping, and spherical grasping.

Existing standard metrics systematically fail at this exact juncture: FMA and ARAT reach early ceiling limits for gross grasp accomplishments, while BRS classification remains ambiguous and qualitative. By deliberately targeting the Stage 4 to 5 boundary, this study addresses the exact clinical population where standard scales display their greatest psychometric vulnerability.

### 1.4 Prior Literature Deficits and Methodological Novelty
A recent benchmark study (Li et al., arXiv:2511.17727, 2025) evaluated whether modern vision-language models could estimate FMA motor impairment directly from clinical video clips paired with textual scoring rubrics. That study reported a complete structural failure: the zero-shot vision-language model exhibited **score flatlining**, predicting virtually identical, average impairment scores regardless of patient severity. When pose estimation was incorporated in their secondary dose-quantification task, keypoints were used strictly for 2D spatial bounding-box cropping, achieving a high relative coefficient error of roughly 40%.

The failure of prior attempts stems from demanding implicit 3D physical geometry derivation directly from 2D pixel matrices. Vision-language models are semantic inference engines, not spatial physics engines. This study resolves that gap by deploying an RGB-D sensor to directly measure physical kinematics (joint angles, range of motion, grip apertures, and population-standardized deviations) and injecting these structured numerical values directly into the model prompt via JSON. This grounds the language model on explicit geometric facts, restoring score rank discrimination and enabling clinically actionable narrative reporting.

---

## 2. Research Objectives & Hypotheses

### 2.1 Research Objectives
- **Objective 1 (Primary Contribution - Precision Assessment)**:  
  Establish an autonomous assessment pipeline combining an Intel RealSense D455 RGB-D sensor, MediaPipe pose tracking, and a Kinematic Feature-Grounded Vision-Language Model. Demonstrate that injecting structured 3D kinematic summaries resolves the score-flatlining defect of pure-video vision-language models, yielding significantly higher rank correlation with clinician-evaluated FMA scores.
- **Objective 2 (Secondary Contribution - Exploratory Intervention)**:  
  Conduct a 4-week pilot clinical trial on Brunnstrom Stage 4 to 5 stroke patients utilizing an add-on design (standard therapy vs. standard therapy plus master-slave glove) to establish clinical protocol feasibility and compute preliminary non-parametric effect sizes.

### 2.2 Research Hypotheses
- **Hypothesis 1 (Cohort Discrimination)**: Healthy controls and stroke patients exhibit statistically significant differences in bilateral 3D joint range of motion, maximum grip aperture, and time-to-maximum grip aperture during synchronized prehension tasks.
- **Hypothesis 2 (Immediate Session Effect)**: A single session of master-slave pneumatic mirror therapy yields an immediate, statistically significant reduction in active tracking angular error on the paretic side.
- **Hypothesis 3 (Exploratory / Proposed Engineering Hypothesis - Subject to Advisor Sign-off)**: A normative multivariate covariance baseline (Mahalanobis distance model) constructed from healthy controls exhibits significant discriminative validity in classifying patient impairment levels.
- **Hypothesis 4 (Grounded Vision-Language Model Superiority)**: The Kinematic Feature-Grounded Vision-Language Model (Arm 3) achieves a significantly higher Spearman rank correlation with gold-standard FMA scores than the pure-video baseline (Arm 1), resolving the flatlining distribution artifact.
- **Hypothesis 5 (Add-On Intervention Efficacy)**: Over a 4-week intervention, the add-on rehabilitation group (Group B) demonstrates a larger positive effect size in FMA score changes compared to standard rehabilitation alone (Group A).

---

## 3. System Architecture: Decoupling Control and Assessment

To prevent sensor latency conflicts and occlusion artifacts, the physical actuation loop and the digital assessment loop are completely decoupled.

```text
┌────────────────────────────────────────────────────────────────────────┐
│ [Actuation Control Loop] Real-Time Gross Physical Mirroring            │
│  Unaffected Hand (5 Flex Sensors) ──[Low-Latency MCU]──> Paretic Glove │
│  (Operates while wearing gloves; 1-DOF assistive flexion/extension)    │
└────────────────────────────────────────────────────────────────────────┘
                                 ≠ Fully Decoupled (No Shared Loop)
┌────────────────────────────────────────────────────────────────────────┐
│ [Diagnostic Assessment Loop] 3D Vision & Feature-Grounded VLM          │
│  Bare-Hand Prehension ──> Intel D455 RGB-D ──> MediaPipe + Depth Map   │
│                             │                          │               │
│                             ▼                          ▼               │
│                     [Video Keyframes]          [3D Kinematic JSON]     │
│                             │                          │               │
│                             └───────────┬──────────────┘               │
│                                         ▼                              │
│                         [Multimodal VLM Inference]                     │
│                                         ▼                              │
│                      [Rank Score & Clinical Narrative Report]          │
└────────────────────────────────────────────────────────────────────────┘
```

### 3.1 Actuation System (Master-Slave Pneumatic Glove)
- **Mechanical & Pneumatic Hardware**: Soft pneumatic elastomer glove linking 5 finger segments to execute coordinated gross flexion and extension in 1 degree of freedom.
- **Sensory Tracking**: Five bi-directional resistive flex bend sensors embedded along the dorsal aspect of the master glove monitor active finger flexion.
- **Embedded Control**: A microcontroller samples flex sensor voltages at high frequency, driving proportional pneumatic solenoid valves and miniature air pumps to achieve an end-to-end master-to-slave tracking latency below 100 milliseconds.
- **Safety Redundancy**: An adjustable mechanical pressure-relief valve hard-caps pneumatic line pressure, paired with a software emergency cutoff and a hardware stop switch.

### 3.2 Diagnostic Vision System (Intel RealSense D455 RGB-D Setup)
All visual functional evaluations occur with bare hands to prevent sensor occlusion.

- **Global Shutter Advantage**: The D455 incorporates global shutter sensors across both RGB (1280×720) and infrared stereo channels, eliminating rolling-shutter distortion during rapid reach trajectories or tremor.
- **Geometric Spatial Alignment (Nominal Target Parameters)**:
  - **Stand-off Distance**: Nominally set to 70 to 75 centimeters from the lens face to the hand home pad. This is derived from the D455 inter-sensor baseline (95 mm) requiring a minimum depth distance ($Z_{\min} \approx 52\text{ cm}$) to avoid stereo depth dropout (Intel RealSense D400 Series Datasheet).
  - **Camera Elevation and Angle**: Suspended nominally 45 to 50 centimeters above the tabletop via an independent floor-standing boom arm tripod, oriented at an oblique top-down angle of 35° to 40°. This configuration avoids dorsal occlusions while capturing joint flexion without planar foreshortening.
  - **Environmental Controls**: A matte dark-gray felt pad covers the desk surface to minimize specular reflections, accompanied by ambient diffused illumination exceeding 500 lux to attenuate infrared projection patterns on the color stream.
- **Parameter Status**: These geometric coordinates represent nominal target parameters to be empirically calibrated and confirmed during Phase 0 engineering verification.

---

## 4. Clinical Assessment Protocol & Task Design

Tasks are aligned with standardized sub-domains of the Action Research Arm Test and Brunnstrom stage definitions.

```text
[Top-Down Spatial Layout: Prehension Alignment]

                  [Intel RealSense D455 (Elevated, 40° Downward)]
                                       │
            ┌──────────────────────────┴──────────────────────────┐
            │                                                     │
     [Unaffected Block]                                    [Paretic Block]
     (Sagittal / Vertical)                                 (Sagittal / Vertical)
       Index (Lateral)                                       Index (Lateral)
        │  │                                                  │  │
        │  │ <--- Pinch Block (1.5 cm thick)                  │  │ <--- Pinch Block (1.5 cm thick)
        │  │                                                  │  │
       Thumb (Medial)                                        Thumb (Medial)
            │                                                     │
     [Unaffected Home Pad]                                 [Paretic Home Pad]
            └──────────────────────────┬──────────────────────────┘
                                       │
                                [Seated Patient]
```

### 4.1 Standard Prehension Task Definitions
- **Calibration Baseline**:  
  The patient places both hands flat on target home pads: rest posture $\rightarrow$ full active finger extension $\rightarrow$ full closed fist (3 cycles) to establish joint baselines and calibrate coordinate offsets.
- **Cylindrical Grasp Task**:
  - **Object**: Matte wooden cylinder (diameter 5 centimeters, height 10 centimeters).
  - **Protocol**: Bilateral synchronized reach $\rightarrow$ full gross cylindrical grasp $\rightarrow$ 5-centimeter vertical lift $\rightarrow$ 2-second hold $\rightarrow$ table return (8 repetitions). Corresponds to Brunnstrom Stage 5 achievement.
- **Spherical Grasp Task**:
  - **Object**: Matte wooden sphere (diameter 7 centimeters).
  - **Protocol**: Bilateral synchronized reach $\rightarrow$ spherical finger wrap $\rightarrow$ 5-centimeter vertical lift $\rightarrow$ 2-second hold $\rightarrow$ table return (8 repetitions). Corresponds to Brunnstrom Stage 5 achievement.
- **Lateral Prehension Task**:
  - **Object**: Self-standing rectangular matte wooden pinch block (thickness 1.5 centimeters, width 4 centimeters, height 7 centimeters).
  - **Alignment**: Oriented along the sagittal plane (anterior-posterior axis), perpendicular to the patient's chest.
  - **Protocol**: Reach $\rightarrow$ lateral key pinch between the thumb pad and the lateral radial aspect of the index middle phalanx $\rightarrow$ vertical lift $\rightarrow$ return (8 repetitions).
  - **Geometric Rationale**: Placing the block along the sagittal axis forces the thumb medially and the index finger laterally, fully exposing the thumb-index aperture directly toward the 40° elevated camera without self-occlusion. Serves as the critical discriminator for Brunnstrom Stage 4.

### 4.2 Scientific Justification for an 8-Repetition Protocol
- **Statistical Variance & Reliability**: Stroke kinematics present high trial-to-trial variability and sporadic computer vision landmark jitter. Trimming initial warm-up trials and potential tracking dropouts requires a minimum pool of 5 stable repetitions to guarantee an intraclass correlation coefficient exceeding 0.85 ($\text{ICC} > 0.85$).
- **Neuromuscular Fatigue Mitigation**: Patients at Brunnstrom Stages 4 to 5 experience rapid neuromuscular fatigue when exceeding 10 to 12 consecutive maximal prehension efforts. Fatigue induces abnormal hypertonic synergy spillover, spasticity increases, and compensatory trunk flexion, distorting baseline motor capacity. Eight repetitions per task (24 total functional repetitions) balances test-retest reliability against the physiological fatigue threshold, bounding evaluation time to under 15 minutes.

---

## 5. Data Processing & Feature-Grounded VLM Pipeline

Coarse, robust kinematic parameters are extracted where the physical signal magnitude (40 to 80 millimeters, greater than 100 degrees) vastly exceeds the camera's spatial depth noise floor.

### 5.1 3D Coordinate Extraction and Kinematic Feature Derivation
1. **Hardware Alignment**: RealSense SDK executes hardware-synchronized mapping of depth pixels to RGB sensor coordinates.
2. **2D Landmark Extraction**: MediaPipe Hands extracts 2D keypoint coordinates $(u, v)$ for 21 anatomical landmarks per hand.
3. **Depth Filtering**: A $5\times5$ spatial window centered on $(u, v)$ extracts the median depth value ($Z_{\text{med}}$), rejecting boundary flying-pixel artifacts.
4. **3D Deprojection**: Camera intrinsic matrices map 2D coordinates and filtered depth into real-world Cartesian metric coordinates $(X, Y, Z)$ in millimeters:
   $$X = \frac{(u - c_x) \cdot Z_{\text{med}}}{f_x}, \quad Y = \frac{(v - c_y) \cdot Z_{\text{med}}}{f_y}, \quad Z = Z_{\text{med}}$$

**Extracted Coarse Kinematic Parameters**:
- **Total Active Range of Motion (TAROM)**: Aggregate sum of active angular excursions across MCP, PIP, and DIP joints during grasp.
- **Maximum Grip Aperture (MGA)**: Peak 3D Euclidean distance between thumb tip and index fingertip measured during in-flight reach.
- **Time-to-Maximum Grip Aperture (TMGA)**: Percentage of total reach duration elapsed when peak aperture occurs.
- **Movement Duration**: Total elapsed time from movement onset to object lift stabilization.

### 5.2 Phase 1: Construction of the Statistical Normative Model
To avoid overfitting risks on small cohorts, the healthy control dataset ($n=20\text{ to }30$) establishes a formal statistical normative reference rather than a black-box neural network:

- **Standardized Z-Scores**: Computed for all kinematic metrics against healthy parametric distributions ($\mu_{\text{norm}}, \sigma_{\text{norm}}$):
  $$Z = \frac{X_{\text{patient}} - \mu_{\text{norm}}}{\sigma_{\text{norm}}}$$
- **Normative Corridor**: Re-interpolates reach-to-pinch trajectories across 0% to 100% normalized movement time using cubic splines, defining a 95% confidence corridor ($\text{Mean} \pm 1.96\text{ Standard Deviations}$) to quantify continuous trajectory departure.
- **Mahalanobis Distance**: Measures multi-joint coordination breakdown across covariant hand features:
  $$D_M(\boldsymbol{x}) = \sqrt{(\boldsymbol{x} - \boldsymbol{\mu})^T \boldsymbol{\Sigma}^{-1} (\boldsymbol{x} - \boldsymbol{\mu})}$$

### 5.3 Feature-Grounded Prompting Architecture
- **Base Engine**: Multimodal VLM (e.g., GPT-4o or Gemini 1.5 Pro) accessed via zero-shot and few-shot in-context evaluation without model fine-tuning.
- **Multimodal Input Payload**:
  1. Four synchronized video keyframes: movement initiation $\rightarrow$ peak in-flight aperture $\rightarrow$ object contact $\rightarrow$ lift maintenance.
  2. Standard clinical rubric text defining Fugl-Meyer Assessment prehension scoring criteria.
  3. A structured kinematic grounding JSON payload containing physical measurements and population Z-scores.

#### Listing 1: Representative Synthetic JSON Schema
*(Illustrative Prototype for Pipeline Demonstration - Not Actual Clinical Data)*

```json
{
  "clinical_metadata": {
    "task": "Lateral Prehension (Key Pinch Block)",
    "target_cohort": "Brunnstrom Stage 4-5 Boundary",
    "trials_averaged": 8
  },
  "kinematic_grounding_features": {
    "MGA_mm": {
      "measured_value": 41.2,
      "normative_mean": 68.5,
      "normative_sd": 4.8,
      "z_score": -5.69,
      "descriptor": "Severely constricted pre-contact grip aperture"
    },
    "TAROM_degrees": {
      "measured_value": 128.5,
      "normative_mean": 210.0,
      "normative_sd": 15.2,
      "z_score": -5.36
    },
    "movement_duration_sec": {
      "measured_value": 4.8,
      "normative_mean": 1.4,
      "normative_sd": 0.25,
      "z_score": 13.6
    },
    "multivariate_coordination": {
      "mahalanobis_distance": 12.4,
      "normative_threshold_p95": 5.99,
      "pathological_synergy_flag": true
    }
  },
  "prompt_directives": {
    "task_1": "Estimate FMA score rank (0, 1, or 2) grounded on the provided kinematic Z-scores.",
    "task_2": "Inspect visual keyframes to detect trunk lean, shoulder abduction, or wrist drop compensation.",
    "task_3": "Generate a concise, clinically interpretable narrative progress report."
  }
}
```

---

## 6. Experimental Protocols & Study Design

### 6.1 Phase 0: System Engineering & Dual-Condition Optical Verification (2 Weeks)
- **Scope**: Conducted over two weeks without human clinical subjects to evaluate hardware reliability and calibrate optical parameters.
- **Latency Benchmark**: Oscilloscope verification of end-to-end master-to-slave tracking latency below 100 milliseconds.
- **Dual-Condition Optical Calibration (Static vs. Dynamic Regimes)**:  
  Rather than relying on unverified literature assumptions, Phase 0 directly establishes the empirical error bounds of the camera tracking pipeline against a precision digital goniometer:
  - **Static Posture Benchmark (Fixed Joint Angles)**: Targeted threshold of mean absolute error ($\text{MAE} < 7^\circ$) and intraclass correlation coefficient ($\text{ICC} > 0.85$).
  - **Dynamic Motion Benchmark (Reach and Grasp Trajectories)**: Targeted threshold of $\text{MAE} < 15^\circ$ across dynamic functional excursions, with trajectory correlation (Pearson $r > 0.80$).
  - **Signal-to-Noise Ratio (SNR) Criteria**: Explicitly verifies that the chosen macroscopic assessment features (MGA range: 40 to 80 mm; TAROM: $> 100^\circ$) maintain an $\text{SNR} > 3.0$ under dynamic noise regimes, ensuring that assessment validity is decoupled from fine-scale landmark jitter.
- **Mechanical Safety**: Confirmation of automatic venting via mechanical pressure-relief valves at target line pressures (>120 kPa).

### 6.2 Phase 1: Healthy Normative Cohort Characterization (3 to 4 Weeks)
- **Participants**: 20 to 30 healthy adult volunteers without upper-extremity neurological or orthopedic impairments.
- **Protocol**: Execution of calibration baseline, cylindrical grasp (8 trials), spherical grasp (8 trials), and lateral prehension (8 trials) on both limbs.
- **Deliverables**: Baseline distributions for range of motion, maximum grip aperture, time-to-aperture, duration, and covariance matrices to benchmark stroke deficits.

### 6.3 Phase 2: Stroke Patient Pilot Clinical Trial (4 Weeks)
- **Participants**: 10 to 15 subacute and chronic post-stroke hemiparetic patients presenting with upper-limb motor deficits at Brunnstrom Stages 4 to 5 and Mini-Mental State Examination (MMSE) scores $\ge 24$ (Folstein et al., 1975).

#### Objective 1 Experimental Architecture: Three-Arm Comparative Assessment

| Study Arm | Input Data Configuration | Primary Experimental Purpose |
| :--- | :--- | :--- |
| **Arm 1 (Baseline)** | 4 Keyframe Images + Scoring Rubric Text | Direct replication of literature baseline; testing for score-flatlining artifacts. |
| **Arm 2 (Ablation)** | Kinematic JSON + Scoring Rubric Text | Evaluating model numerical deductive capacity in the absence of spatial visual context. |
| **Arm 3 (Proposed)** | Keyframes + Kinematic JSON (with Z-scores) + Rubric | Validating that explicit physical grounding restores ranking validity and narrative accuracy. |

#### Objective 2 Experimental Architecture: 4-Week Add-on Clinical Efficacy
- **Group A (Control)**: Standard occupational and physical therapy alone (40 minutes per session).
- **Group B (Intervention)**: Standard occupational and physical therapy plus master-slave pneumatic glove mirror therapy add-on (15 minutes per session).
- **Dose & Frequency**: 3 sessions per week over 4 weeks (12 total intervention sessions).
- **Measurement Milestones**: Baseline, per-session monitoring (abbreviated vision metrics), and 4-week completion.

---

## 7. Statistical Analysis & Outcome Metrics

Given the small-sample clinical pilot constraints ($n=10\text{ to }15$), analysis relies on non-parametric evaluations, rank correlation, and effect size estimation.

### 7.1 Objective 1 Statistical Evaluation (Assessment Pipeline)
- **Mitigation of Score Flatlining (H4-1)**: Levene's test of variance homogeneity compares predicted FMA score distributions across Arms 1, 2, and 3 to confirm that Arm 3 recovers inter-subject variance rather than collapsing toward an invariant mean.
- **Rank-Order Correlation (H4-2)**: Spearman rank correlation coefficients compare model predictions against clinician-evaluated FMA scores across all three arms, with Steiger's Z-test evaluating the statistical significance of dependent correlation differences.
- **Blinded Qualitative Narrative Assessment**: Two physiatrists and one occupational therapist evaluate generated clinical reports on a 5-point Likert scale assessing hallucination absence, compensatory pattern recognition, and therapeutic actionability.

### 7.2 Objective 2 Statistical Evaluation (Intervention Efficacy)
- **Between-Group Change Scores (H5)**: The primary endpoint of score change from baseline to 4 weeks ($\Delta\text{FMA-UE} = T_1 - T_0$) is evaluated between Group A and Group B using the Mann-Whitney U test.
- **Non-Parametric Effect Size Reporting**: To prevent over-reliance on p-values in small samples, the rank-biserial correlation ($r$) and its 95% confidence interval serve as the principal reported outcomes:
  $$r = 1 - \frac{2U}{n_1 n_2}$$
- **Within-Session Immediate Effects (H2)**: Immediate pre-to-post session tracking error reductions are evaluated using the Wilcoxon signed-rank test.

---

## 8. Limitations & Methodological Risk Mitigation

### 8.1 Optical Noise and Self-Occlusion Boundaries
- **Risk**: Contact-phase fingertip distances cannot be resolved below 2 to 3 millimeters using standard depth cameras due to flying-pixel edge noise.
- **Mitigation**: The protocol explicitly excludes fine finger individuation metrics from primary endpoints. It relies on coarse macro-kinematics where physical signals (40 to 80 millimeters, greater than 100 degrees) vastly exceed camera noise. The sagittal orientation of the pinch block ensures that the thumb and index finger remain optically separated.

### 8.2 Vision-Language Model Numerical Reasoning Bias and Hallucination
- **Risk**: Large language models can exhibit inconsistent arithmetic comparisons when evaluating raw floating-point numbers, risking hallucinated score outputs.
- **Mitigation**: Raw values are supplemented with pre-computed Z-scores and clinical categorical descriptors (such as "Severely constricted") within the input JSON payload. Few-shot in-context examples lock the model into deterministic output schemas.

### 8.3 Statistical Power in Pilot Cohorts ($n=10\text{ to }15$)
- **Risk**: Constrained patient recruitment risks Type II error inflation, potentially failing to reach asymptotic significance thresholds.
- **Mitigation**: The clinical trial is explicitly framed as an exploratory feasibility and effect-size estimation pilot. The resultant effect sizes will provide empirical priors to inform formal statistical power calculations for subsequent multi-center randomized controlled trials.

---

## 9. Expected Scientific Contributions

- **Theoretical & Computer Science Contribution**: Provides an empirical solution to the score-flatlining failure of zero-shot vision-language models in motor rehabilitation by establishing a structured, kinematic feature-grounded multimodal framework.
- **Clinical & Translational Contribution**: Delivers an objective, rapid evaluation pipeline tailored to Brunnstrom Stages 4 to 5, addressing the ceiling effects of conventional scales and generating interpretable narrative summaries for therapy planning.
- **Biomedical Engineering Contribution**: Validates a cost-effective telerehabilitation paradigm that combines 1 degree of freedom soft pneumatic actuation with single-camera 3D spatial assessment.

---

## References

1. **Chen, H. M., Chen, C. C., Hsueh, I. P., Huang, S. L., & Hsieh, C. L. (2009)**. Test-retest reproducibility and smallest real difference of 5 hand function tests in patients with stroke. *Neurorehabilitation and Neural Repair*, 23(5), 435–440. [[PMID: 19118132](https://pubmed.ncbi.nlm.nih.gov/19118132/)]
2. **Folstein, M. F., Folstein, S. E., & McHugh, P. R. (1975)**. "Mini-mental state": a practical method for grading the cognitive state of patients for the clinician. *Journal of Psychiatric Research*, 12(3), 189–198. [[PMID: 1202204](https://pubmed.ncbi.nlm.nih.gov/1202204/)]
3. **Gladstone, D. J., Danells, C. J., & Black, S. E. (2002)**. The Fugl-Meyer Assessment of motor recovery after stroke: a critical review of its measurement properties. *Neurorehabilitation and Neural Repair*, 16(3), 232–240. [[PMID: 12234086](https://pubmed.ncbi.nlm.nih.gov/12234086/)]
4. **Hsieh, C. L., Hsueh, I. P., Chiang, F. M., & Lin, P. H. (1998)**. Inter-rater reliability and validity of the Action Research Arm Test in stroke patients. *Age and Ageing*, 27(2), 107–113. [[PMID: 9634306](https://pubmed.ncbi.nlm.nih.gov/9634306/)]
5. **Intel Corporation. (2020)**. *Intel RealSense D400 Series Product Family Datasheet*. (Document Number: 338820-009).
6. **Li, K., et al. (2025)**. Vision-language models for human motion understanding: Lessons from stroke rehabilitation. *arXiv preprint arXiv:2511.17727*. [[arXiv:2511.17727](https://arxiv.org/abs/2511.17727)]
