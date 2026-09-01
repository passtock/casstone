import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, BoxStyle
import numpy as np

def generate_paper_style_diagram(output_path="실험_프로토콜_플로우차트.png"):
    # 폰트 설정 (Windows 맑은 고딕)
    plt.rcParams['font.family'] = 'Malgun Gothic'
    plt.rcParams['axes.unicode_minus'] = False

    # 캔버스 생성 (가로로 긴 비율, 16 x 8 인치, 300 DPI -> 초고해상도)
    fig, ax = plt.subplots(figsize=(16, 7.5), dpi=300)
    fig.patch.set_facecolor('#FFFFFF')
    ax.set_facecolor('#FFFFFF')
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis('off')

    # 공통 스타일 정의
    BORDER_COLOR = '#1E1E1E'
    LINE_WIDTH = 2.0
    
    # 파스텔 색상 정의
    C_BLUE = '#D6E4FF'       # Step 1: 대상 및 사전 평가 (연파랑)
    C_ORANGE = '#FFE6CC'     # Step 2: 실험 및 중재 (연주황)
    C_GRAY = '#EDE9FE'       # Step 3: 데이터 추출 (연보라/연회색)
    C_GREEN = '#DCFCE7'      # Step 4: 최종 임상/AI 결과 (연초록)

    # -------------------------------------------------------------
    # 1. 상단 섹션 헤더 (아이콘 + 카테고리 명칭)
    # -------------------------------------------------------------
    # 섹션 1
    ax.text(18, 92, "🩺 1. Baseline & Controls", fontsize=15, fontweight='bold', color='#111827', ha='center', va='center')
    # 섹션 2
    ax.text(51, 92, "🤖 2. Clinical Protocol & Intervention", fontsize=15, fontweight='bold', color='#111827', ha='center', va='center')
    # 섹션 3
    ax.text(84, 92, "📊 3. Analytics & Clinical Report", fontsize=15, fontweight='bold', color='#111827', ha='center', va='center')

    # -------------------------------------------------------------
    # 노드 그리기 헬퍼 함수
    # -------------------------------------------------------------
    def draw_node(x, y, w, h, text_lines, bg_color, title_weight='bold', font_size=11):
        box = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.2,rounding_size=1.2",
                             linewidth=LINE_WIDTH, edgecolor=BORDER_COLOR, facecolor=bg_color)
        ax.add_patch(box)
        
        # 텍스트 세로 정렬
        total_lines = len(text_lines)
        line_height = h / (total_lines + 1)
        for idx, line in enumerate(text_lines):
            ty = y + h - (idx + 1) * line_height
            is_first = (idx == 0)
            weight = 'bold' if is_first else 'normal'
            size = font_size if is_first else font_size - 1.5
            color = '#000000' if is_first else '#374151'
            ax.text(x + w/2, ty, line, fontsize=size, fontweight=weight, color=color, ha='center', va='center')

    # 화살표 그리기 헬퍼 함수 (직선 및 꺾은선)
    def draw_arrow(start, end, rad=0.0):
        ax.annotate('', xy=end, xytext=start,
                    arrowprops=dict(facecolor=BORDER_COLOR, edgecolor=BORDER_COLOR, 
                                    width=LINE_WIDTH*0.8, headwidth=8, headlength=7,
                                    connectionstyle=f"arc3,rad={rad}" if rad != 0 else None))

    def draw_polyline_arrow(points):
        # points: list of (x, y)
        for i in range(len(points)-1):
            if i == len(points)-2:
                # 마지막 선분만 화살표 머리
                ax.annotate('', xy=points[i+1], xytext=points[i],
                            arrowprops=dict(facecolor=BORDER_COLOR, edgecolor=BORDER_COLOR,
                                            width=LINE_WIDTH*0.8, headwidth=8, headlength=7))
            else:
                ax.plot([points[i][0], points[i+1][0]], [points[i][1], points[i+1][1]],
                        color=BORDER_COLOR, linewidth=LINE_WIDTH*0.8)

    # -------------------------------------------------------------
    # 2. [섹션 1: Baseline & Controls] 노드 배치
    # -------------------------------------------------------------
    # 노드 1-1: 일반인 대조군 (Normative Model)
    draw_node(5, 68, 14, 15, ["일반인 대조군", "(Healthy N=20~30)", "양손 파지 16회 측정"], C_BLUE)
    
    # 노드 1-2: 정상 기준 모델 구축
    draw_node(5, 41, 14, 15, ["정상 기준 모델", "(Normative Model)", "양손 각도 오차 분포"], C_BLUE)

    # 노드 1-3: 환자 임상 기준선 평가
    draw_node(5, 14, 14, 15, ["임상 기준선 평가", "(Patient Baseline)", "치료사 FMA-UE 평가"], C_BLUE)

    # 섹션 1 내부 화살표
    draw_arrow((12, 68), (12, 56))  # 일반인 -> 정상 기준 모델

    # -------------------------------------------------------------
    # 3. [섹션 2: Clinical Protocol & Intervention] 노드 배치
    # -------------------------------------------------------------
    # 노드 2-1: 사전 기능 측정 (Pre-Test)
    draw_node(26, 68, 15, 15, ["사전 기능 측정 (Pre)", "장갑 미착용 (Bare-hand)", "양손 파지 과제 16회", "(원통형 8회 + 구형 8회)"], C_ORANGE)

    # 점선 영역: Master-Slave 물리적 중재 반복 세션
    dot_box = FancyBboxPatch((24.5, 11), 38.5, 47, boxstyle="round,pad=0.3,rounding_size=1.5",
                             linewidth=2.0, linestyle='--', edgecolor='#4B5563', facecolor='#FFFDF9')
    ax.add_patch(dot_box)
    ax.text(43.75, 55, "🔄 Master-Slave 물리적 미러테라피 중재", fontsize=11.5, fontweight='bold', color='#B45309', ha='center', va='center')

    # 점선 내부 노드 2-2: Master 각도 센싱
    draw_node(26, 36, 16, 14, ["건측 (Master)", "관절 각도 실시간 측정", "착용자 운동 의도 파악"], C_ORANGE)

    # 점선 내부 노드 2-3: Slave 공압 물리 구동
    draw_node(45.5, 36, 16, 14, ["환측 (Slave)", "공압 액추에이터 구동", "물리적 동작 추종 재현"], C_ORANGE)

    # 점선 내부 노드 2-4: 반복 세트 및 안전 휴식
    draw_node(33, 16, 21.5, 13, ["파지-이완 10회 × 3세트", "• 세트 간 2~3분 필수 휴식", "• 환자별 맞춤 ROM 제한"], C_ORANGE)

    # 점선 내부 화살표
    draw_arrow((42, 43), (45.5, 43))  # Master -> Slave
    draw_polyline_arrow([(53.5, 36), (53.5, 29), (43.75, 29)]) # Slave -> 3세트
    draw_polyline_arrow([(33, 22.5), (29, 22.5), (29, 36)])   # 3세트 -> Master (루프)

    # 노드 2-5: 사후 기능 측정 (Post-Test)
    draw_node(45.5, 68, 16, 15, ["사후 기능 측정 (Post)", "장갑 미착용 (Bare-hand)", "동일 양손 파지 16회", "(중재 직후 즉각 효과)"], C_ORANGE)

    # -------------------------------------------------------------
    # 4. [섹션 3: Analytics & Clinical Report] 노드 배치
    # -------------------------------------------------------------
    # 노드 3-1: 데이터 추출
    draw_node(70, 68, 16, 15, ["3D 생체역학 데이터", "• 21개 관절각도 시계열", "• 건환측 오차 (MAE/RMSE)", "• 최대파지구경 (MGA)"], C_GRAY)

    # 노드 3-2: AI 모델링 및 관절 손상 국소화
    draw_node(70, 41, 16, 15, ["AI 모델링 & 판별", "• 정상 vs 환자 분류 (AUC)", "• 관절별 손상 국소화", "  (SHAP 기여도 히트맵)"], C_GRAY)

    # 노드 3-3: 최종 임상 리포트 (정량 재활 효과 검증)
    draw_node(70, 14, 16, 15, ["정량 재활 평가 리포트", "• Pre vs Post 오차 감소율", "• 통계 유의성 (Paired t-test)", "• 치료사 보조 리포트 제공"], C_GREEN)

    # -------------------------------------------------------------
    # 5. 노드 간 연결 화살표 (Flow Arrow Routing)
    # -------------------------------------------------------------
    # 환자 임상 기준선 -> Pre-Test (꺾은선)
    draw_polyline_arrow([(19, 21.5), (22.5, 21.5), (22.5, 75.5), (26, 75.5)])

    # Pre-Test -> Master-Slave 중재 세션 (꺾은선)
    draw_polyline_arrow([(34, 68), (34, 50)])

    # Master-Slave 중재 세션 -> Post-Test
    draw_arrow((53.5, 50), (53.5, 68))

    # Post-Test -> 데이터 추출
    draw_arrow((61.5, 75.5), (70, 75.5))

    # 정상 기준 모델 -> AI 모델링 & 판별 (점선 또는 꺾은선으로 연결)
    draw_polyline_arrow([(19, 48.5), (66, 48.5), (70, 48.5)])

    # 데이터 추출 -> AI 모델링
    draw_arrow((78, 68), (78, 56))

    # AI 모델링 -> 최종 임상 리포트
    draw_arrow((78, 41), (78, 29))

    # -------------------------------------------------------------
    # 6. 하단 전체 루프 피드백 (종단적 치료 계획 피드백 점선)
    # -------------------------------------------------------------
    # 최종 결과 -> 환자 임상 기준선 (치료 경과 반영 피드백 루프)
    ax.annotate('', xy=(12, 14), xytext=(70, 18),
                arrowprops=dict(arrowstyle="->", color='#6B7280', lw=1.8, linestyle=':',
                                connectionstyle="arc3,rad=0.25"))
    ax.text(41, 4, "🔄 맞춤형 재활 계획 수정 및 장기 추적 피드백 (Longitudinal Clinical Feedback)", 
            fontsize=10.5, fontweight='bold', color='#4B5563', ha='center', va='center')

    # 저장
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='#FFFFFF')
    plt.close()
    print(f"Diagram successfully generated: {output_path}")

if __name__ == "__main__":
    generate_paper_style_diagram("c:/Users/passp/Desktop/univercity/4-2/캡스톤/실험_프로토콜_플로우차트.png")
