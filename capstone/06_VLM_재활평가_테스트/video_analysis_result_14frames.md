# VLM 재활 영상 분석 결과 보고서 (14-Frame Normalized Sampling)

- **대상 영상**: `C:/Users/passp/OneDrive/바탕 화면/jeayong/capstone/06_VLM_재활평가_테스트/KakaoTalk_20260909_183548574.mp4` (길이: 80.7초)
- **샘플링 기법**: 전체 영상 균등 14프레임 정규화 추출 (0% ~ 100%)
- **분석 모델**: `Qwen/Qwen2.5-VL-3B-Instruct` (로컬 GPU 가속 4-bit 구동)
- **총 소요 시간**: 79.3초
- **분석 일시**: 2026-09-15 18:14:26

---

## 0. 정규화 추출된 14개 프레임 정보
| 프레임 번호 | 타임스탬프 | 영상 진행률 | 파일 저장 경로 |
|:---:|:---:|:---:|:---|
| #1 | 0.0s | 0% | `sampled_14_frames\frame_01_t00.0s.jpg` |
| #2 | 6.2s | 8% | `sampled_14_frames\frame_02_t06.2s.jpg` |
| #3 | 12.4s | 15% | `sampled_14_frames\frame_03_t12.4s.jpg` |
| #4 | 18.6s | 23% | `sampled_14_frames\frame_04_t18.6s.jpg` |
| #5 | 24.8s | 31% | `sampled_14_frames\frame_05_t24.8s.jpg` |
| #6 | 31.0s | 38% | `sampled_14_frames\frame_06_t31.0s.jpg` |
| #7 | 37.2s | 46% | `sampled_14_frames\frame_07_t37.2s.jpg` |
| #8 | 43.4s | 54% | `sampled_14_frames\frame_08_t43.4s.jpg` |
| #9 | 49.6s | 62% | `sampled_14_frames\frame_09_t49.6s.jpg` |
| #10 | 55.8s | 69% | `sampled_14_frames\frame_10_t55.8s.jpg` |
| #11 | 62.0s | 77% | `sampled_14_frames\frame_11_t62.0s.jpg` |
| #12 | 68.2s | 85% | `sampled_14_frames\frame_12_t68.2s.jpg` |
| #13 | 74.5s | 92% | `sampled_14_frames\frame_13_t74.5s.jpg` |
| #14 | 80.7s | 100% | `sampled_14_frames\frame_14_t80.7s.jpg` |

> 프레임 미리보기 이미지는 `sampled_14_frames/` 폴더에 타임스탬프 오버레이와 함께 저장되어 있습니다.

---

## 1. 전체 활동 및 세팅 식별 (Activity & Scene Identification)
The video shows a participant engaged in an upper-limb rehabilitation session, which is sampled uniformly from start (0%) to end (100%). The participant is seated at a table with two round objects placed on it. Throughout the sequence, the participant uses both hands to manipulate these objects.

Here is a detailed description of the sequence:

1. **Frame 1/14**: The participant is sitting at the table with both hands resting on the surface. The first frame indicates that the session has started at 0% completion.
   
2. **Frame 2/14**: The participant's right hand is raised, and they appear to be preparing to grasp one of the round objects. The second frame shows that the session has progressed to 8% completion.

3. **Frame 3/14**: The participant's left hand is raised, and they are about to grasp the other round object. The third frame indicates that the session has reached 15% completion.

4. **Frame 4/14**: The participant's right hand is holding the first round object while their left hand is empty. The fourth frame shows that the session has progressed to 23% completion.

5. **Frame 5/14**: The participant

---

## 2. 기능적 원초 동작 분해 판별 (Motion & Grasp Decomposition - NYU 2026 논문 방식)

### [오른손 (Right Hand)]
- **유의미한 움직임 감지 (Motion)**: O (Yes) (응답 원문: `Yes`)
- **물체 파지/접촉 감지 (Grasp)**: X (No) (응답 원문: `No`)
- **도출된 운동 프리미티브**: **Reach or Reposition (접촉 전 이동 또는 원위치 복귀)**

### [왼손 (Left Hand)]
- **유의미한 움직임 감지 (Motion)**: O (Yes) (응답 원문: `Yes`)
- **물체 파지/접촉 감지 (Grasp)**: X (No) (응답 원문: `No`)
- **도출된 운동 프리미티브**: **Reach or Reposition (접촉 전 이동 또는 원위치 복귀)**

---

## 3. 양손 대칭성 및 운동 협응 분석 (Bimanual Coordination & Symmetry)
The video shows a series of frames capturing the rehabilitation movement of a person's hands. Here is a detailed analysis of the movement coordination between the left and right hands:

### Frames 1 to 13:
- **Frames 1 to 2**: The person is sitting at a table with their hands resting on the table. The left hand is slightly raised, and the right hand is resting on the table.
- **Frames 3 to 13**: The person begins to move their hands towards the two spherical objects on the table. Both hands move in a coordinated manner, with the left hand moving slightly ahead of the right hand. The movements are smooth and symmetrical, indicating good coordination between the two hands.

### Frame 14:
- **Frame 14**: The person has completed the movement, and both hands are positioned near the spherical objects. The movements are still smooth and symmetrical, showing no signs of hesitation, tremor, or asymmetry.

### Summary:
- **Symmetry**: Both hands move symmetrically over the two spherical objects throughout the sequence.
- **Coordination**: There is no indication of any asymmetry or hesitation in the movements.
- **Tremor**: No tremor is observed in the movements.

Overall, the

---

## 4. 전체 영상 직접 처리 대비 14프레임 정규화의 장점 및 고찰
1. **추론 속도 및 계산 효율**:
   - 80초 고해상도 영상을 매 초 디코딩하는 대신, 전체 진행 단계를 대표하는 14개의 정규화 키프레임만 처리하므로 토큰 수와 GPU 연산량이 대폭 절감되어 훨씬 빠르게 응답을 얻을 수 있습니다.
2. **시간적 대표성 보장 (Normalized Progression)**:
   - 0% (시작 대기), 20~50% (접근 및 파지), 70~100% (유지 및 대칭적 동작) 등 모션의 핵심 전이 국면(Transition phase)을 균등하게 커버합니다.
3. **타임스탬프 시각적 각인 효과**:
   - 프레임마다 시간(T=X.Xs)과 진행률(%)이 표기되어 있어 VLM이 시간 경과에 따른 움직임 변화를 더 정확하게 추적할 수 있습니다.
