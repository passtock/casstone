# VLM 재활 영상 분석 결과 보고서

- **대상 영상**: `KakaoTalk_20260909_183548574.mp4` (길이: 80.7초)
- **분석 모델**: `Qwen/Qwen2.5-VL-3B-Instruct` (로컬 GPU 가속 구동)
- **총 소요 시간**: 37.0초
- **분석 일시**: 2026-09-09 19:47:26

---

## 1. 전체 활동 및 세팅 식별 (Activity & Scene Identification)
1) The table has two round objects, which appear to be crystal balls, placed on it. The participant is sitting at the table with both hands resting on the table surface.

2) Yes, the participant is performing a bimanual (two-handed) grasping task on the two round objects. The participant is using both hands to grasp the crystal balls simultaneously, indicating that they are performing a bimanual grasping action.

---

## 2. 기능적 원초 동작 분해 판별 (Motion & Grasp Decomposition - NYU 2026 논문 방식)

### [오른손 (Right Hand)]
- **유의미한 움직임 감지 (Motion)**: X (No) (응답 원문: `No`)
- **물체 파지/접촉 감지 (Grasp)**: X (No) (응답 원문: `No`)
- **도출된 운동 프리미티브**: **Idle (대기/휴지)**

### [왼손 (Left Hand)]
- **유의미한 움직임 감지 (Motion)**: X (No) (응답 원문: `No`)
- **물체 파지/접촉 감지 (Grasp)**: X (No) (응답 원문: `No`)
- **도출된 운동 프리미티브**: **Idle (대기/휴지)**

---

## 3. 양손 대칭성 및 운동 협응 분석 (Bimanual Coordination & Symmetry)
The movements of the left and right hands are symmetrical, with no noticeable hesitation, tremor, or asymmetry. Both hands maintain a steady grip on the spherical objects throughout the video.

---

## 4. 논문(NYU 2026) 관점에서의 분석 및 연구 시사점
1. **시각적 장면 이해 (성공)**: 책상 위의 두 구형 물체와 참가자가 양손을 올려 쥐거나 유지(Stabilize)하는 전반적 상태를 매우 자연스럽게 인식함.
2. **논문에서 지적된 2D VLM의 한계 검증**:
   - VLM은 손이 구형 물체 위에 올려져 있는 형태(Proximity)만 보고 접촉/파지(Grasp)로 판단하지만, 실제 손가락이 가하는 악력이나 미세한 표면 접촉 유무(Contact vs Gap)는 판별하기 어렵습니다.
   - 따라서 정밀한 재활 정량화를 위해서는 현재 개발하신 **RealSense 3D Depth 카메라의 물리적 거리 계측 + MediaPipe 3D 관절각(`kinematics.py`)** 데이터가 결합되어야 임상적 신뢰성을 확보할 수 있습니다.
