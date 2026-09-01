import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, Arc
import numpy as np

def generate_reference_style_diagram(output_path="실험_프로토콜_플로우차트.png"):
    # 맑은 고딕 및 Arial 설정
    plt.rc('font', family='Malgun Gothic')
    plt.rcParams['axes.unicode_minus'] = False

    # 16:7.8 비율의 고화질 캔버스
    fig, ax = plt.subplots(figsize=(16, 7.8), dpi=300)
    fig.patch.set_facecolor('#FFFFFF')
    ax.set_facecolor('#FFFFFF')
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis('off')

    # 스타일 파라미터
    BORDER_COLOR = '#111827'
    LINE_WIDTH = 2.2
    
    # 레퍼런스 이미지와 동일한 파스텔 컬러
    C_BLUE = '#DDE7FA'      # 1단계 (연파랑)
    C_ORANGE = '#FDEBD0'    # 2단계 (연살구/주황)
    C_GRAY = '#F3F4F6'      # 3단계 (연회색)
    C_GREEN = '#D5F5E3'     # 최종 산출물 (연초록)

    # -------------------------------------------------------------
    # 1. 상단 카테고리 헤더 (아이콘 + 영문/한글 카테고리명)
    # -------------------------------------------------------------
    # 헤더 1
    ax.text(14.5, 93.5, "Normative Baseline", fontsize=15, fontweight='bold', color='#111827', ha='center', va='center')
    ax.text(14.5, 89.5, "[정상 기준 모델 구축]", fontsize=11, fontweight='bold', color='#4B5563', ha='center', va='center')

    # 헤더 2
    ax.text(49.5, 93.5, "Clinical Trial & Intervention", fontsize=15, fontweight='bold', color='#111827', ha='center', va='center')
    ax.text(49.5, 89.5, "[환자 임상 시험 및 중재]", fontsize=11, fontweight='bold', color='#4B5563', ha='center', va='center')

    # 헤더 3
    ax.text(85, 93.5, "Analytics & Clinical Report", fontsize=15, fontweight='bold', color='#111827', ha='center', va='center')
    ax.text(85, 89.5, "[정량 분석 및 임상 리포트]", fontsize=11, fontweight='bold', color='#4B5563', ha='center', va='center')

    # -------------------------------------------------------------
    # 헬퍼 함수 정의
    # -------------------------------------------------------------
    def draw_box(x, y, w, h, text_list, bg_color):
        box = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.2,rounding_size=1.2",
                             linewidth=LINE_WIDTH, edgecolor=BORDER_COLOR, facecolor=bg_color)
        ax.add_patch(box)
        
        num_lines = len(text_list)
        line_spacing = h / (num_lines + 1)
        for i, text in enumerate(text_list):
            ty = y + h - (i + 1) * line_spacing
            is_title = (i == 0)
            weight = 'bold' if is_title else 'normal'
            size = 11.5 if is_title else 10.0
            color = '#000000' if is_title else '#374151'
            ax.text(x + w/2, ty, text, fontsize=size, fontweight=weight, color=color, ha='center', va='center')

    def draw_down_arrow(start_x, start_y, end_y):
        ax.annotate('', xy=(start_x, end_y), xytext=(start_x, start_y),
                    arrowprops=dict(facecolor=BORDER_COLOR, edgecolor=BORDER_COLOR,
                                    width=LINE_WIDTH*0.7, headwidth=9, headlength=8))

    def draw_right_arrow(start_x, start_y, end_x):
        ax.annotate('', xy=(end_x, start_y), xytext=(start_x, start_y),
                    arrowprops=dict(facecolor=BORDER_COLOR, edgecolor=BORDER_COLOR,
                                    width=LINE_WIDTH*0.7, headwidth=9, headlength=8))

    def draw_polyline(points):
        for i in range(len(points)-1):
            if i == len(points)-2:
                ax.annotate('', xy=points[i+1], xytext=points[i],
                            arrowprops=dict(facecolor=BORDER_COLOR, edgecolor=BORDER_COLOR,
                                            width=LINE_WIDTH*0.7, headwidth=9, headlength=8))
            else:
                ax.plot([points[i][0], points[i+1][0]], [points[i][1], points[i+1][1]],
                        color=BORDER_COLOR, linewidth=LINE_WIDTH*0.7)

    # -------------------------------------------------------------
    # 2. [섹션 1] Baseline & Controls (왼쪽 세로 3단)
    # -------------------------------------------------------------
    bw1, bh1 = 17, 18
    # 1-1 상단
    draw_box(6, 64, bw1, bh1, ["Healthy Controls", "일반인 대조군 (N=20~30)", "만 20~65세 정상 성인", "장갑 미착용 (Bare-hand)"], C_BLUE)
    draw_down_arrow(14.5, 64, 55)

    # 1-2 중단
    draw_box(6, 37, bw1, bh1, ["Bilateral Grasping", "양손 동시 파지 16회", "• 원통형 (ø 5cm) 8회", "• 구형 (ø 7cm) 8회"], C_BLUE)
    draw_down_arrow(14.5, 37, 28)

    # 1-3 하단
    draw_box(6, 10, bw1, bh1, ["Normative Model", "정상 기준 모델 구축", "• 3D 관절각도 오차분포", "• 정상 기준선(Baseline)"], C_BLUE)

    # 섹션 1 하단 -> 섹션 2 상단으로 이동하는 꺾은선 화살표
    draw_polyline([(23, 19), (26.5, 19), (26.5, 73), (30, 73)])

    # -------------------------------------------------------------
    # 3. [섹션 2] Patient Protocol & Intervention (중앙)
    # -------------------------------------------------------------
    bw2, bh2 = 17, 18
    
    # 2-1 상단: 임상 기준선
    draw_box(30, 64, bw2, bh2, ["FMA-UE Baseline", "환자 임상 기준선 평가", "• 치료사 FMA-UE 측정", "• Brunnstrom 4~5단계"], C_ORANGE)
    draw_down_arrow(38.5, 64, 55)

    # 2-2 중단: Pre-Test
    draw_box(30, 37, bw2, bh2, ["Pre-Intervention Test", "사전 기능 측정 (Pre)", "• 장갑 미착용 파지 16회", "• 중재 전 초기 오차 산출"], C_ORANGE)
    draw_down_arrow(38.5, 37, 28)

    # 2-3 하단: 센싱 시작점
    draw_box(30, 10, bw2, bh2, ["Motion Sensing", "건측(Master) 각도 측정", "• 멀티카메라 + IMU", "• 착용자 파지 의도 감지"], C_ORANGE)

    # 2-3 하단 -> 점선 루프 박스로 들어가는 화살표
    draw_right_arrow(47, 19, 51)

    # --- [중앙 점선 루프 박스: Master-Slave 물리적 중재] ---
    dot_box = FancyBboxPatch((51, 10), 17, 72, boxstyle="round,pad=0.3,rounding_size=1.5",
                             linewidth=2.2, linestyle='--', edgecolor='#374151', facecolor='#FFFAF0')
    ax.add_patch(dot_box)

    # 점선 박스 내부 노드 1 (상단: Post-Test)
    draw_box(52.5, 64, 14, 15, ["Post-Test", "사후 측정 (Post)", "장갑 미착용 16회", "즉각 효과 검증"], C_ORANGE)

    # 점선 박스 내부: 중앙 순환 화살표 아이콘 그리기
    # 🔄 아이콘을 원호와 화살표로 직접 그리기
    circle_center = (59.5, 46)
    radius = 4.5
    arc1 = Arc(circle_center, radius*2, radius*2, angle=0, theta1=30, theta2=150, color=BORDER_COLOR, linewidth=3.5)
    arc2 = Arc(circle_center, radius*2, radius*2, angle=0, theta1=210, theta2=330, color=BORDER_COLOR, linewidth=3.5)
    ax.add_patch(arc1)
    ax.add_patch(arc2)
    # 화살표 머리
    ax.annotate('', xy=(59.5 + radius*np.cos(np.radians(30)), 46 + radius*np.sin(np.radians(30))),
                xytext=(59.5 + radius*np.cos(np.radians(40)), 46 + radius*np.sin(np.radians(40))),
                arrowprops=dict(facecolor=BORDER_COLOR, edgecolor=BORDER_COLOR, width=3.5, headwidth=8, headlength=7))
    ax.annotate('', xy=(59.5 + radius*np.cos(np.radians(210)), 46 + radius*np.sin(np.radians(210))),
                xytext=(59.5 + radius*np.cos(np.radians(220)), 46 + radius*np.sin(np.radians(220))),
                arrowprops=dict(facecolor=BORDER_COLOR, edgecolor=BORDER_COLOR, width=3.5, headwidth=8, headlength=7))

    ax.text(59.5, 46, "10 reps\n× 3 sets", fontsize=10.5, fontweight='bold', color='#9A3412', ha='center', va='center')

    # 점선 박스 내부 노드 2 (하단: Slave 물리 구동)
    draw_box(52.5, 12, 14, 15, ["Pneumatic Assist", "환측(Slave) 구동", "• 공압 장갑 굽힘/폄", "• 세트간 2분 휴식"], C_ORANGE)

    # 점선 내부 루프 화살표
    draw_down_arrow(59.5, 64, 53)
    draw_down_arrow(59.5, 39, 27)

    # Post-Test -> 섹션 3 상단으로 이동하는 꺾은선 화살표
    draw_polyline([(66.5, 71.5), (71.5, 71.5), (71.5, 82), (76.5, 82)])

    # -------------------------------------------------------------
    # 4. [섹션 3] Analytics & Clinical Report (오른쪽 세로 4단)
    # -------------------------------------------------------------
    bw3, bh3 = 17, 16.5
    
    # 3-1: 3D 데이터 추출
    draw_box(76.5, 74, bw3, bh3, ["Kinematic Features", "3D 생체역학 데이터", "• 21개 관절각도 시계열", "• 좌우 MAE / RMSE 오차"], C_GRAY)
    draw_down_arrow(85, 74, 69)

    # 3-2: AI 모델링
    draw_box(76.5, 52.5, bw3, bh3, ["AI Classification", "AI 모델링 및 이상탐지", "• 정상 vs 환자 분류 (AUC)", "• One-Class SVM / XGB"], C_GRAY)
    draw_down_arrow(85, 52.5, 47.5)

    # 3-3: 손상 국소화 히트맵
    draw_box(76.5, 31, bw3, bh3, ["Joint Localization", "관절별 손상 국소화", "• 손가락별 SHAP 기여도", "• 관절 이상도 히트맵"], C_GRAY)
    draw_down_arrow(85, 31, 26)

    # 3-4 (최종 강조 노드 - 연초록): 임상 리포트
    draw_box(76.5, 9.5, bw3, bh3, ["Clinical Report", "정량 재활 평가 리포트", "• Pre vs Post 회복량 검정", "• 치료사 보조 리포트"], C_GREEN)

    # -------------------------------------------------------------
    # 5. 전체 피드백 점선 루프 (하단 ➔ 좌측 환자 평가로 피드백)
    # -------------------------------------------------------------
    feedback_points = [(76.5, 17.5), (2, 17.5), (2, 73), (6, 73)]
    for i in range(len(feedback_points)-1):
        if i == len(feedback_points)-2:
            ax.annotate('', xy=feedback_points[i+1], xytext=feedback_points[i],
                        arrowprops=dict(arrowstyle="->", color='#6B7280', lw=2.0, linestyle=':',
                                        shrinkA=0, shrinkB=0))
        else:
            ax.plot([feedback_points[i][0], feedback_points[i+1][0]], 
                    [feedback_points[i][1], feedback_points[i+1][1]],
                    color='#6B7280', linewidth=2.0, linestyle=':')
    
    ax.text(39, 4, "Longitudinal Feedback (장기 재활 추적 및 맞춤형 치료 계획 피드백)", 
            fontsize=10, fontweight='bold', color='#4B5563', ha='center', va='center')

    # 파일 저장
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='#FFFFFF')
    plt.close()
    print(f"Diagram successfully saved to: {output_path}")

if __name__ == "__main__":
    generate_reference_style_diagram("c:/Users/passp/Desktop/univercity/4-2/캡스톤/실험_프로토콜_플로우차트.png")
