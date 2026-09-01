import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, Arc
import numpy as np

def generate_perfect_paper_diagram(output_path="실험_프로토콜_플로우차트.png"):
    # 폰트 설정 (Windows 맑은 고딕)
    plt.rc('font', family='Malgun Gothic')
    plt.rcParams['axes.unicode_minus'] = False

    # 16:8.5 비율 고해상도 캔버스 (300 DPI)
    fig, ax = plt.subplots(figsize=(16, 8.5), dpi=300)
    fig.patch.set_facecolor('#FFFFFF')
    ax.set_facecolor('#FFFFFF')
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis('off')

    # 공통 디자인 토큰
    BORDER_COLOR = '#111827'
    LINE_WIDTH = 2.4
    
    # 레퍼런스와 동일한 깔끔한 파스텔 컬러
    C_BLUE = '#DCE8FA'      # 1열: 정상 기준 (연파랑)
    C_ORANGE = '#FDEBD0'    # 2열: 임상 프로토콜 & 중재 (연살구/주황)
    C_GRAY = '#F3F4F6'      # 3열: 분석/AI (연회색)
    C_GREEN = '#D5F5E3'     # 3열 최종: 임상 리포트 (연초록)

    # -------------------------------------------------------------
    # 1. 상단 섹션 카테고리 헤더
    # -------------------------------------------------------------
    ax.text(14.5, 95.5, "Normative Baseline", fontsize=16, fontweight='bold', color='#111827', ha='center', va='center')
    ax.text(14.5, 91.5, "[ 정상 기준 모델 구축 ]", fontsize=12, fontweight='bold', color='#4B5563', ha='center', va='center')

    ax.text(49.5, 95.5, "Clinical Protocol & Intervention", fontsize=16, fontweight='bold', color='#111827', ha='center', va='center')
    ax.text(49.5, 91.5, "[ 환자 임상 실험 & 중재 ]", fontsize=12, fontweight='bold', color='#4B5563', ha='center', va='center')

    ax.text(85.5, 95.5, "Analytics & Clinical Report", fontsize=16, fontweight='bold', color='#111827', ha='center', va='center')
    ax.text(85.5, 91.5, "[ 정량 분석 & 임상 리포트 ]", fontsize=12, fontweight='bold', color='#4B5563', ha='center', va='center')

    # -------------------------------------------------------------
    # 헬퍼 함수 정의
    # -------------------------------------------------------------
    def draw_box(x, y, w, h, title, sub_lines, bg_color):
        box = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.2,rounding_size=1.4",
                             linewidth=LINE_WIDTH, edgecolor=BORDER_COLOR, facecolor=bg_color)
        ax.add_patch(box)
        
        if len(sub_lines) == 0:
            ax.text(x + w/2, y + h/2, title, fontsize=14.5, fontweight='bold', color='#000000', ha='center', va='center')
        else:
            ax.text(x + w/2, y + h - 4.2, title, fontsize=14, fontweight='bold', color='#000000', ha='center', va='center')
            
            num_lines = len(sub_lines)
            start_y = y + h - 8.5
            spacing = (h - 9.5) / max(num_lines, 1)
            for i, line in enumerate(sub_lines):
                ty = start_y - i * spacing
                ax.text(x + w/2, ty, line, fontsize=11.5, fontweight='bold', color='#374151', ha='center', va='center')

    def draw_down_arrow(start_x, start_y, end_y):
        ax.annotate('', xy=(start_x, end_y), xytext=(start_x, start_y),
                    arrowprops=dict(facecolor=BORDER_COLOR, edgecolor=BORDER_COLOR,
                                    width=LINE_WIDTH*0.75, headwidth=10, headlength=9))

    def draw_right_arrow(start_x, start_y, end_x):
        ax.annotate('', xy=(end_x, start_y), xytext=(start_x, start_y),
                    arrowprops=dict(facecolor=BORDER_COLOR, edgecolor=BORDER_COLOR,
                                    width=LINE_WIDTH*0.75, headwidth=10, headlength=9))

    def draw_polyline(points, color=BORDER_COLOR, linestyle='-', lw=LINE_WIDTH*0.75):
        for i in range(len(points)-1):
            if i == len(points)-2:
                ax.annotate('', xy=points[i+1], xytext=points[i],
                            arrowprops=dict(facecolor=color, edgecolor=color,
                                            width=lw, headwidth=10, headlength=9, linestyle=linestyle))
            else:
                ax.plot([points[i][0], points[i+1][0]], [points[i][1], points[i+1][1]],
                        color=color, linewidth=lw, linestyle=linestyle)

    # -------------------------------------------------------------
    # 2. [1열: Normative Baseline] 일반인 대조군 트랙 (세로 3단)
    # -------------------------------------------------------------
    bw1, bh1 = 17, 19
    
    # 1-1 상단: 일반인 대조군
    draw_box(6, 65, bw1, bh1, "Healthy Controls", ["일반인 대조군 (N=20~30)", "만 20~65세 정상 성인", "장갑 미착용 (Bare-hand)"], C_BLUE)
    draw_down_arrow(14.5, 65, 56)

    # 1-2 중단: 양손 파지 과제
    draw_box(6, 37, bw1, bh1, "Bilateral Grasping", ["양손 동시 파지 (16회)", "• 원통형 (ø 5cm) 8회", "• 구형 (ø 7cm) 8회"], C_BLUE)
    draw_down_arrow(14.5, 37, 28)

    # 1-3 하단: 정상 기준 모델 구축
    draw_box(6, 9, bw1, bh1, "Normative Model", ["정상 기준 모델 구축", "3D 관절각도 오차 분포", "(환자 비교 기준선)"], C_BLUE)

    # -------------------------------------------------------------
    # 3. [2열 & 중앙 루프: Clinical Protocol & Intervention] 환자 트랙
    # -------------------------------------------------------------
    bw2, bh2 = 17, 19
    
    # 2-1 상단: 치료사 FMA-UE 평가
    draw_box(28.5, 65, bw2, bh2, "Clinical Baseline", ["치료사 FMA-UE 평가", "상지/손 기능 기준선", "Brunnstrom 4~5단계"], C_ORANGE)
    draw_down_arrow(37, 65, 56)

    # 2-2 중단: 사전 기능 측정 (Pre-Test)
    draw_box(28.5, 37, bw2, bh2, "Pre-Test (사전 측정)", ["장갑 미착용 양손 파지", "초기 3D 관절오차 측정", "16회 파지 과제 수행"], C_ORANGE)
    
    # Pre-Test(중단) ➔ 점선 중재 루프 상단(Master Sensing)으로 진입하는 꺾은선 화살표
    draw_polyline([(45.5, 46.5), (47.5, 46.5), (47.5, 74.5), (50, 74.5)])

    # --- [중앙 점선 루프 영역: Master-Slave 물리적 중재] ---
    dot_box = FancyBboxPatch((48.5, 9), 20, 76, boxstyle="round,pad=0.3,rounding_size=1.5",
                             linewidth=2.2, linestyle='--', edgecolor='#4B5563', facecolor='#FFFDF9')
    ax.add_patch(dot_box)
    ax.text(58.5, 82.5, "Master-Slave 중재 세션", fontsize=12.5, fontweight='bold', color='#B45309', ha='center', va='center')

    # 점선 박스 상단: 건측 마스터 센싱
    draw_box(50, 65, 17, 15, "Master Sensing", ["건측(Master) 각도 측정", "착용자 운동 의도 감지"], C_ORANGE)
    draw_down_arrow(58.5, 65, 58)

    # 점선 박스 중앙: 🔄 3세트 반복 루프 아이콘
    circle_center = (58.5, 49)
    radius = 4.8
    arc1 = Arc(circle_center, radius*2, radius*2, angle=0, theta1=30, theta2=150, color=BORDER_COLOR, linewidth=3.8)
    arc2 = Arc(circle_center, radius*2, radius*2, angle=0, theta1=210, theta2=330, color=BORDER_COLOR, linewidth=3.8)
    ax.add_patch(arc1)
    ax.add_patch(arc2)
    # 화살표 머리
    ax.annotate('', xy=(circle_center[0] + radius*np.cos(np.radians(30)), circle_center[1] + radius*np.sin(np.radians(30))),
                xytext=(circle_center[0] + radius*np.cos(np.radians(42)), circle_center[1] + radius*np.sin(np.radians(42))),
                arrowprops=dict(facecolor=BORDER_COLOR, edgecolor=BORDER_COLOR, width=3.8, headwidth=9, headlength=8))
    ax.annotate('', xy=(circle_center[0] + radius*np.cos(np.radians(210)), circle_center[1] + radius*np.sin(np.radians(210))),
                xytext=(circle_center[0] + radius*np.cos(np.radians(222)), circle_center[1] + radius*np.sin(np.radians(222))),
                arrowprops=dict(facecolor=BORDER_COLOR, edgecolor=BORDER_COLOR, width=3.8, headwidth=9, headlength=8))

    ax.text(circle_center[0], circle_center[1], "10회 파지\n× 3세트", fontsize=11.5, fontweight='bold', color='#9A3412', ha='center', va='center')
    draw_down_arrow(58.5, 40, 31)

    # 점선 박스 하단: 환측 슬레이브 공압 구동 & 안전 관리
    draw_box(50, 14, 17, 17, "Slave Assistance", ["환측(Slave) 공압 물리 재현", "• 세트 간 2~3분 휴식", "• 개별 ROM 제한(과신전 방지)"], C_ORANGE)

    # 점선 박스 하단(중재 완료) ➔ 3열 상단(Post-Test)으로 진입하는 꺾은선 화살표
    draw_polyline([(67, 22.5), (71.5, 22.5), (71.5, 74.5), (75.5, 74.5)])

    # -------------------------------------------------------------
    # 4. [3열: Analytics & Clinical Report] 사후측정 + 통합 AI분석 + 최종리포트
    # -------------------------------------------------------------
    bw3, bh3 = 18.5, 19
    
    # 4-1 상단: 사후 기능 측정 (Post-Test)
    draw_box(75.5, 65, bw3, bh3, "Post-Test (사후 측정)", ["장갑 미착용 양손 파지 (16회)", "중재 직후 관절 각도 측정", "즉각적 기능 회복 평가"], C_ORANGE)
    draw_down_arrow(84.75, 65, 56)

    # 4-2 중단: 3D 데이터 & AI 분석 (하나로 통합)
    draw_box(75.5, 37, bw3, bh3, "Kinematics & AI", ["3D 관절각도 오차 (MAE/RMSE)", "정상 모델 대비 손상 판별", "손가락별 손상 국소화 (SHAP)"], C_GRAY)
    draw_down_arrow(84.75, 37, 28)

    # 4-3 하단 (최종 핵심 산출물 - 연초록): 임상 리포트
    draw_box(75.5, 9, bw3, bh3, "Clinical Report", ["정량 재활 평가 리포트", "• Pre vs Post 오차 감소율", "• 치료사 맞춤형 보조 리포트"], C_GREEN)

    # -------------------------------------------------------------
    # 5. [연결선 수정]: Normative Model ➔ Kinematics & AI (하단 우회 연결)
    # -------------------------------------------------------------
    # 1열 Normative Model(하단)에서 출발하여 아래쪽을 통해 3열 Kinematics & AI로 깔끔하게 전달
    norm_points = [(23, 18.5), (25.5, 18.5), (25.5, 28), (47.5, 28), (47.5, 8), (73.5, 8), (73.5, 46.5), (75.5, 46.5)]
    # 더 직관적이고 깔끔한 경로: Normative Model 오른쪽 ➔ 2열 아래 ➔ 3열 Kinematics & AI
    draw_polyline([(23, 18.5), (25.5, 18.5), (25.5, 6.5), (73.5, 6.5), (73.5, 46.5), (75.5, 46.5)],
                  color='#4B5563', linestyle='--', lw=1.8)
    ax.text(49.5, 4.5, "Normative Baseline Data (정상 기준 데이터 전달)", fontsize=9.5, fontweight='bold', color='#4B5563', ha='center', va='center')

    # -------------------------------------------------------------
    # 6. 하단 전체 피드백 루프 (Clinical Report ➔ Clinical Baseline)
    # -------------------------------------------------------------
    draw_polyline([(94, 18.5), (96.5, 18.5), (96.5, 87), (37, 87), (37, 84.5)],
                  color='#2563EB', linestyle=':', lw=2.2)
    ax.text(66.75, 88.8, "Longitudinal Clinical Feedback (장기 재활 추적 및 맞춤 치료 피드백)", 
            fontsize=10.5, fontweight='bold', color='#1D4ED8', ha='center', va='center')

    # 최종 저장
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='#FFFFFF')
    plt.close()
    print(f"Updated diagram generated successfully: {output_path}")

if __name__ == "__main__":
    generate_perfect_paper_diagram("c:/Users/passp/Desktop/univercity/4-2/캡스톤/실험_프로토콜_플로우차트.png")
