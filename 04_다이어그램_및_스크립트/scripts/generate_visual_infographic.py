import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, Arc
import numpy as np

def generate_bold_clean_infographic(output_path="실험_프로토콜_시각화_인포그래픽.png"):
    # 폰트 설정 (Windows 맑은 고딕)
    plt.rc('font', family='Malgun Gothic')
    plt.rcParams['axes.unicode_minus'] = False

    # 16:9 슬라이드 비율 (18 x 10.2 인치, 300 DPI)
    fig, ax = plt.subplots(figsize=(18, 10.2), dpi=300)
    fig.patch.set_facecolor('#F8FAFC')
    ax.set_facecolor('#F8FAFC')
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis('off')

    # 색상 정의
    C_BORDER = '#0F172A'
    LW_BORDER = 2.4

    C_HDR_BLUE = '#1D4ED8'
    C_HDR_ORANGE = '#C2410C'
    C_HDR_PURPLE = '#6D28D9'
    C_HDR_GREEN = '#047857'

    C_BG_BLUE = '#EFF6FF'
    C_BG_ORANGE = '#FFFBEB'
    C_BG_PURPLE = '#FAF5FF'
    C_BG_GREEN = '#ECFDF5'

    # -------------------------------------------------------------
    # 0. 메인 타이틀 헤더 (크고 진하게)
    # -------------------------------------------------------------
    title_box = FancyBboxPatch((2, 90.5), 96, 7.8, boxstyle="round,pad=0.2,rounding_size=1.0",
                               linewidth=2.0, edgecolor='#94A3B8', facecolor='#FFFFFF')
    ax.add_patch(title_box)

    ax.text(4, 96.0, "CLINICAL STUDY PROTOCOL & SESSION PIPELINE", fontsize=12, fontweight='bold', color='#2563EB', va='center')
    ax.text(4, 92.8, "공압장갑 Master-Slave 물리적 미러테라피 임상 실험 프로토콜", fontsize=19, fontweight='bold', color='#0F172A', va='center')

    # -------------------------------------------------------------
    # 헬퍼 함수 정의
    # -------------------------------------------------------------
    def draw_header_card(x, y, w, h, num, title, header_color, bg_color):
        # 카드 전체 테두리 & 배경
        card = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.2,rounding_size=1.2",
                              linewidth=LW_BORDER, edgecolor=C_BORDER, facecolor='#FFFFFF')
        ax.add_patch(card)
        
        # 헤더 바
        header_h = 7.2
        header_bar = FancyBboxPatch((x, y + h - header_h), w, header_h, 
                                   boxstyle="round,pad=0.2,rounding_size=1.2",
                                   linewidth=LW_BORDER, edgecolor=C_BORDER, facecolor=header_color)
        ax.add_patch(header_bar)
        
        # 헤더 텍스트 (크고 굵게)
        ax.text(x + w/2, y + h - header_h/2, f"{num}. {title}", 
                fontsize=15.5, fontweight='bold', color='#FFFFFF', ha='center', va='center')
        
        # 컨텐츠 영역 배경
        body_bg = FancyBboxPatch((x + 0.6, y + 0.6), w - 1.2, h - header_h - 1.2,
                                 boxstyle="round,pad=0.1,rounding_size=0.8",
                                 linewidth=0, facecolor=bg_color)
        ax.add_patch(body_bg)

    def draw_arrow(start, end, lw=3.0):
        ax.annotate('', xy=end, xytext=start,
                    arrowprops=dict(facecolor=C_BORDER, edgecolor=C_BORDER,
                                    width=lw*0.7, headwidth=11, headlength=10))

    # -------------------------------------------------------------
    # 1. [Card 1] 대상 선정 & 임상 기준선
    # -------------------------------------------------------------
    c1_x, c1_y, c1_w, c1_h = 2, 45, 22.5, 43
    draw_header_card(c1_x, c1_y, c1_w, c1_h, "1", "대상 선정 & 기준선 평가", C_HDR_BLUE, C_BG_BLUE)

    # 1-1: 환자군 박스
    b1_1 = FancyBboxPatch((c1_x + 1.2, c1_y + 19.5), c1_w - 2.4, 15.5, boxstyle="round,pad=0.2,rounding_size=0.8",
                          linewidth=1.8, edgecolor='#93C5FD', facecolor='#FFFFFF')
    ax.add_patch(b1_1)
    ax.text(c1_x + 2.5, c1_y + 31.5, "편마비 환자군 (N=10~15)", fontsize=13.5, fontweight='bold', color='#1E3A8A', va='center')
    ax.text(c1_x + 2.5, c1_y + 27.5, "• Brunnstrom 4~5단계 환자", fontsize=12, fontweight='bold', color='#1E293B', va='center')
    ax.text(c1_x + 2.5, c1_y + 24.2, "• 인지기능 정상 (MMSE ≥ 24)", fontsize=12, fontweight='bold', color='#1E293B', va='center')
    ax.text(c1_x + 2.5, c1_y + 20.8, "▶ 치료사 FMA-UE 평가 (기준선)", fontsize=12, fontweight='bold', color='#2563EB', va='center')

    # 1-2: 일반인 대조군 박스
    b1_2 = FancyBboxPatch((c1_x + 1.2, c1_y + 2), c1_w - 2.4, 16, boxstyle="round,pad=0.2,rounding_size=0.8",
                          linewidth=1.8, edgecolor='#93C5FD', facecolor='#FFFFFF')
    ax.add_patch(b1_2)
    ax.text(c1_x + 2.5, c1_y + 14.5, "일반인 대조군 (N=20~30)", fontsize=13.5, fontweight='bold', color='#065F46', va='center')
    ax.text(c1_x + 2.5, c1_y + 10.8, "• 만 20~65세 성인 (질환 없음)", fontsize=12, fontweight='bold', color='#1E293B', va='center')
    ax.text(c1_x + 2.5, c1_y + 7.5, "• 장갑 미착용 양손 파지 과제", fontsize=12, fontweight='bold', color='#1E293B', va='center')
    ax.text(c1_x + 2.5, c1_y + 4.2, "▶ 정상 협응 기준 모델 구축", fontsize=12, fontweight='bold', color='#059669', va='center')

    # -------------------------------------------------------------
    # 2. [Card 2] 사전 기능 측정 (Pre-Test)
    # -------------------------------------------------------------
    c2_x, c2_y, c2_w, c2_h = 26.5, 45, 22.5, 43
    draw_header_card(c2_x, c2_y, c2_w, c2_h, "2", "사전 기능 측정 (Pre-Test)", C_HDR_ORANGE, C_BG_ORANGE)

    # 2-1: 3D 비전 측정 박스
    b2_1 = FancyBboxPatch((c2_x + 1.2, c2_y + 19.5), c2_w - 2.4, 15.5, boxstyle="round,pad=0.2,rounding_size=0.8",
                          linewidth=1.8, edgecolor='#FDE68A', facecolor='#FFFFFF')
    ax.add_patch(b2_1)
    ax.text(c2_x + 2.5, c2_y + 31.5, "3-카메라 3D 비전 리그", fontsize=13.5, fontweight='bold', color='#92400E', va='center')
    ax.text(c2_x + 2.5, c2_y + 27.5, "• MediaPipe 21개 관절 추출", fontsize=12, fontweight='bold', color='#1E293B', va='center')
    ax.text(c2_x + 2.5, c2_y + 24.2, "• IMU 융합 손떨림 노이즈 보정", fontsize=12, fontweight='bold', color='#1E293B', va='center')
    ax.text(c2_x + 2.5, c2_y + 20.8, "▶ 장갑 미착용 (맨손 자연 파지)", fontsize=12, fontweight='bold', color='#D97706', va='center')

    # 2-2: 파지 과제 2종 박스
    b2_2 = FancyBboxPatch((c2_x + 1.2, c2_y + 2), c2_w - 2.4, 16, boxstyle="round,pad=0.2,rounding_size=0.8",
                          linewidth=1.8, edgecolor='#FDE68A', facecolor='#FFFFFF')
    ax.add_patch(b2_2)
    ax.text(c2_x + 2.5, c2_y + 14.5, "양손 파지 과제 (총 16회)", fontsize=13.5, fontweight='bold', color='#92400E', va='center')
    ax.text(c2_x + 2.5, c2_y + 10.8, "• 원통형 물체 파지 (지름 5cm, 8회)", fontsize=12, fontweight='bold', color='#1E293B', va='center')
    ax.text(c2_x + 2.5, c2_y + 7.5, "• 구형 물체 파지 (지름 7cm, 8회)", fontsize=12, fontweight='bold', color='#1E293B', va='center')
    ax.text(c2_x + 2.5, c2_y + 4.2, "▶ 중재 전 초기 관절오차 측정", fontsize=12, fontweight='bold', color='#D97706', va='center')

    # -------------------------------------------------------------
    # 3. [Card 3] Master-Slave 물리적 중재
    # -------------------------------------------------------------
    c3_x, c3_y, c3_w, c3_h = 51, 45, 23.5, 43
    draw_header_card(c3_x, c3_y, c3_w, c3_h, "3", "Master-Slave 물리적 중재", C_HDR_PURPLE, C_BG_PURPLE)

    # 3-1: Master 센싱 박스
    b3_1 = FancyBboxPatch((c3_x + 1.2, c3_y + 23.5), c3_w - 2.4, 11.5, boxstyle="round,pad=0.2,rounding_size=0.8",
                          linewidth=1.8, edgecolor='#DDD6FE', facecolor='#FFFFFF')
    ax.add_patch(b3_1)
    ax.text(c3_x + 2.5, c3_y + 31.5, "건측 (Master 센서 장갑)", fontsize=13.5, fontweight='bold', color='#5B21B6', va='center')
    ax.text(c3_x + 2.5, c3_y + 27.5, "• 착용자 능동적 파지 의도 감지", fontsize=12, fontweight='bold', color='#1E293B', va='center')
    ax.text(c3_x + 2.5, c3_y + 24.5, "• 손가락 관절 각도 실시간 측정", fontsize=12, fontweight='bold', color='#1E293B', va='center')

    # 중앙 루프 배지 박스 (크고 진하게)
    loop_box = FancyBboxPatch((c3_x + 3.0, c3_y + 14.5), c3_w - 6.0, 7.5, boxstyle="round,pad=0.2,rounding_size=0.6",
                              linewidth=2.0, edgecolor='#7C3AED', facecolor='#EDE9FE')
    ax.add_patch(loop_box)
    ax.text(c3_x + c3_w/2, c3_y + 19.5, "10회 파지 반복 × 3세트", fontsize=13, fontweight='bold', color='#6D28D9', ha='center', va='center')
    ax.text(c3_x + c3_w/2, c3_y + 16.2, "(세트 간 2~3분 필수 휴식)", fontsize=11.5, fontweight='bold', color='#4C1D95', ha='center', va='center')

    # 3-2: Slave 공압 구동 박스
    b3_2 = FancyBboxPatch((c3_x + 1.2, c3_y + 2), c3_w - 2.4, 11.5, boxstyle="round,pad=0.2,rounding_size=0.8",
                          linewidth=1.8, edgecolor='#DDD6FE', facecolor='#FFFFFF')
    ax.add_patch(b3_2)
    ax.text(c3_x + 2.5, c3_y + 10.0, "환측 (Slave 소프트 공압장갑)", fontsize=13.5, fontweight='bold', color='#5B21B6', va='center')
    ax.text(c3_x + 2.5, c3_y + 6.2, "• 공압 액추에이터 물리적 굽힘/폄", fontsize=12, fontweight='bold', color='#1E293B', va='center')
    ax.text(c3_x + 2.5, c3_y + 3.2, "• 환자별 맞춤 ROM 제한 (과신전 방지)", fontsize=12, fontweight='bold', color='#DC2626', va='center')

    # -------------------------------------------------------------
    # 4. [Card 4] 사후 평가 & 임상 리포트
    # -------------------------------------------------------------
    c4_x, c4_y, c4_w, c4_h = 76.5, 45, 21.5, 43
    draw_header_card(c4_x, c4_y, c4_w, c4_h, "4", "사후 평가 & 임상 리포트", C_HDR_GREEN, C_BG_GREEN)

    # 4-1: 사후 측정 박스
    b4_1 = FancyBboxPatch((c4_x + 1.2, c4_y + 19.5), c4_w - 2.4, 15.5, boxstyle="round,pad=0.2,rounding_size=0.8",
                          linewidth=1.8, edgecolor='#A7F3D0', facecolor='#FFFFFF')
    ax.add_patch(b4_1)
    ax.text(c4_x + 2.5, c4_y + 31.5, "사후 측정 (Post-Test)", fontsize=13.5, fontweight='bold', color='#065F46', va='center')
    ax.text(c4_x + 2.5, c4_y + 27.5, "• 중재 직후 장갑 미착용 파지", fontsize=12, fontweight='bold', color='#1E293B', va='center')
    ax.text(c4_x + 2.5, c4_y + 24.2, "• 동일 16회 파지 과제 재실시", fontsize=12, fontweight='bold', color='#1E293B', va='center')
    ax.text(c4_x + 2.5, c4_y + 20.8, "▶ 즉각적 관절 가동성 회복 평가", fontsize=12, fontweight='bold', color='#047857', va='center')

    # 4-2: 정량 분석 리포트 박스
    b4_2 = FancyBboxPatch((c4_x + 1.2, c4_y + 2), c4_w - 2.4, 16, boxstyle="round,pad=0.2,rounding_size=0.8",
                          linewidth=1.8, edgecolor='#A7F3D0', facecolor='#FFFFFF')
    ax.add_patch(b4_2)
    ax.text(c4_x + 2.5, c4_y + 14.5, "정량 임상 리포트 출력", fontsize=13.5, fontweight='bold', color='#065F46', va='center')
    ax.text(c4_x + 2.5, c4_y + 10.8, "• 중재 전후 관절오차 유의미 감소", fontsize=12, fontweight='bold', color='#1E293B', va='center')
    ax.text(c4_x + 2.5, c4_y + 7.5, "• 손가락 마디별(MCP/PIP) 각도 분석", fontsize=12, fontweight='bold', color='#1E293B', va='center')
    ax.text(c4_x + 2.5, c4_y + 4.2, "▶ 치료사용 객관적 바이오마커", fontsize=12, fontweight='bold', color='#047857', va='center')

    # -------------------------------------------------------------
    # 메인 가로 연결 화살표 (1 ➔ 2 ➔ 3 ➔ 4)
    # -------------------------------------------------------------
    draw_arrow((c1_x + c1_w, c1_y + c1_h/2), (c2_x, c2_y + c2_h/2))
    draw_arrow((c2_x + c2_w, c2_y + c2_h/2), (c3_x, c3_y + c3_h/2))
    draw_arrow((c3_x + c3_w, c3_y + c3_h/2), (c4_x, c4_y + c4_h/2))

    # -------------------------------------------------------------
    # 하단: 세션 타임라인 바 (크고 시원시원하게)
    # -------------------------------------------------------------
    bot_box = FancyBboxPatch((2, 3), 96, 38, boxstyle="round,pad=0.2,rounding_size=1.0",
                             linewidth=2.0, edgecolor='#94A3B8', facecolor='#FFFFFF')
    ax.add_patch(bot_box)

    # 타임라인 메인 타이틀
    ax.text(4, 37.0, "1회 방문 세션 타임라인 (총 35~40분 소요: 환자 피로도 최소화 설계)", fontsize=15, fontweight='bold', color='#0F172A', va='center')

    # 5개 타임라인 카드
    t_steps = [
        ("00~10분", "사전 임상 평가", "치료사 FMA-UE 평가", '#DBEAFE', '#1E40AF'),
        ("10~15분", "사전 기능 측정", "장갑 미착용 파지 16회", '#FEF3C7', '#B45309'),
        ("15~28분", "Master-Slave 중재", "10회×3세트 (물리적 미러링)", '#F3E8FF', '#7E22CE'),
        ("28~33분", "사후 기능 재측정", "장갑 미착용 파지 16회", '#D1FAE5', '#065F46'),
        ("33~38분", "피드백 및 종료", "착용감/통증 확인 (SUS)", '#F1F5F9', '#475569')
    ]

    t_w = 16.8
    t_gap = 2.4
    t_start = 4.2
    for i, (t_time, t_name, t_sub, t_bg, t_col) in enumerate(t_steps):
        tx = t_start + i * (t_w + t_gap)
        t_card = FancyBboxPatch((tx, 18), t_w, 14.5, boxstyle="round,pad=0.2,rounding_size=0.7",
                                linewidth=1.6, edgecolor='#CBD5E1', facecolor=t_bg)
        ax.add_patch(t_card)
        ax.text(tx + t_w/2, 28.5, t_time, fontsize=12.5, fontweight='bold', color=t_col, ha='center', va='center')
        ax.text(tx + t_w/2, 24.5, t_name, fontsize=14, fontweight='bold', color='#0F172A', ha='center', va='center')
        ax.text(tx + t_w/2, 20.8, t_sub, fontsize=11.5, fontweight='bold', color='#334155', ha='center', va='center')
        
        # 다음 단계 화살표
        if i < len(t_steps) - 1:
            ax.annotate('', xy=(tx + t_w + t_gap - 0.4, 25.2), xytext=(tx + t_w + 0.4, 25.2),
                        arrowprops=dict(facecolor=C_BORDER, edgecolor=C_BORDER, width=2.5, headwidth=8, headlength=7))

    # 구분선
    ax.plot([4, 96], [14.5, 14.5], color='#CBD5E1', lw=1.2)

    # 하단 3대 핵심 요약 포인트 (크고 진하게)
    p1 = FancyBboxPatch((4.5, 5), 28.5, 7.5, boxstyle="round,pad=0.2,rounding_size=0.6",
                        linewidth=1.4, edgecolor='#FCA5A5', facecolor='#FEF2F2')
    ax.add_patch(p1)
    ax.text(6, 10.2, "[안전] 환자 안전 최우선", fontsize=12.5, fontweight='bold', color='#DC2626', va='center')
    ax.text(6, 7.0, "• 개별 손가락 맞춤 ROM 제한 (과신전 방지)\n• 비상정지(E-Stop) 및 세트 간 2~3분 필수 휴식", fontsize=10.5, fontweight='bold', color='#475569', va='center')

    p2 = FancyBboxPatch((35.5, 5), 28.5, 7.5, boxstyle="round,pad=0.2,rounding_size=0.6",
                        linewidth=1.4, edgecolor='#93C5FD', facecolor='#EFF6FF')
    ax.add_patch(p2)
    ax.text(37, 10.2, "[측정] 마커리스 3D 비전 시스템", fontsize=12.5, fontweight='bold', color='#2563EB', va='center')
    ax.text(37, 7.0, "• 마커 부착 없이 3-카메라로 21개 관절 추출\n• MediaPipe + IMU 융합을 통한 노이즈 제거", fontsize=10.5, fontweight='bold', color='#475569', va='center')

    p3 = FancyBboxPatch((66.5, 5), 29, 7.5, boxstyle="round,pad=0.2,rounding_size=0.6",
                        linewidth=1.4, edgecolor='#86EFAC', facecolor='#F0FDF4')
    ax.add_patch(p3)
    ax.text(68, 10.2, "[결과] 치료사용 객관적 정량 리포트", fontsize=12.5, fontweight='bold', color='#059669', va='center')
    ax.text(68, 7.0, "• 주관적 육안 평가 보완 손가락 각도 제공\n• 중재 전후 즉각적 회복량(Pre vs Post) 검증", fontsize=10.5, fontweight='bold', color='#475569', va='center')

    # 최종 저장
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='#F8FAFC')
    plt.close()
    print(f"Bold clean infographic generated successfully: {output_path}")

if __name__ == "__main__":
    generate_bold_clean_infographic("c:/Users/passp/Desktop/univercity/4-2/캡스톤/실험_프로토콜_시각화_인포그래픽.png")
