import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.path import Path
import numpy as np

def create_protocol_image(output_path="실험프로토콜_병원미팅용.png"):
    # 한글 폰트 설정 (Windows 맑은 고딕)
    plt.rcParams['font.family'] = 'Malgun Gothic'
    plt.rcParams['axes.unicode_minus'] = False

    # 16:9 비율 캔버스 생성 (19.2 x 10.8 인치, DPI 150 -> 2880 x 1620 고화질)
    fig, ax = plt.subplots(figsize=(19.2, 10.8), dpi=150)
    fig.patch.set_facecolor('#0B1120')
    ax.set_facecolor('#0B1120')
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis('off')

    # 색상 팔레트
    C_HEADER_BG = '#1E293B'
    C_CARD_BG = '#131D31'
    C_CARD_BORDER = '#2E3D59'
    C_CYAN = '#38BDF8'
    C_BLUE = '#3B82F6'
    C_GREEN = '#10B981'
    C_PURPLE = '#A855F7'
    C_AMBER = '#F59E0B'
    C_TEXT_WHITE = '#FFFFFF'
    C_TEXT_LIGHT = '#E2E8F0'
    C_TEXT_MUTED = '#94A3B8'
    C_STEP_BG = '#1E293B'
    C_STEP_ACTIVE = '#1D3B53'

    # --- 1. 상단 헤더 영역 ---
    header_box = patches.FancyBboxPatch((2, 88), 96, 10, boxstyle="round,pad=0.5,rounding_size=1.2",
                                        linewidth=1.5, edgecolor=C_CARD_BORDER, facecolor=C_HEADER_BG)
    ax.add_patch(header_box)

    # 헤더 태그 & 텍스트
    ax.text(4, 95.5, "CLINICAL STUDY PROTOCOL & SESSION OVERVIEW", fontsize=11, fontweight='bold', color=C_CYAN, va='center')
    ax.text(4, 91.5, "공압장갑 Master-Slave 기반 물리적 미러테라피 임상 실험 프로토콜", fontsize=21, fontweight='bold', color=C_TEXT_WHITE, va='center')
    
    ax.text(96, 95.5, "한동대학교 기계제어공학 / Human Robotics Lab", fontsize=11, fontweight='bold', color=C_TEXT_LIGHT, ha='right', va='center')
    ax.text(96, 91.5, "편마비 환자 손 기능 재활 및 AI 정량 평가 연구", fontsize=13, color=C_TEXT_MUTED, ha='right', va='center')

    # --- 2. 환자 선정 및 안전 관리 (Inclusion & Safety) ---
    sec1_box = patches.FancyBboxPatch((2, 75), 96, 11, boxstyle="round,pad=0.5,rounding_size=1.0",
                                      linewidth=1.2, edgecolor='#1E3A8A', facecolor='#0F233F')
    ax.add_patch(sec1_box)

    # 섹션 1 타이틀
    ax.text(4, 83.5, "1. 연구 대상자 기준 및 환자 안전 프로토콜 (Patient Inclusion & Safety)", fontsize=13, fontweight='bold', color='#60A5FA', va='center')

    # 내용 2분할 카드
    # 1) 대상자 기준
    ax.text(5, 79.5, "• 대상 환자군:", fontsize=11, fontweight='bold', color=C_CYAN, va='center')
    ax.text(14, 79.5, "뇌졸중 편마비 환자 (Brunnstrom 4~5단계, 인지기능 MMSE ≥ 24, 심한 관절구축 없음)", fontsize=11, color=C_TEXT_LIGHT, va='center')
    ax.text(5, 76.5, "• 대조군 (비교):", fontsize=11, fontweight='bold', color=C_GREEN, va='center')
    ax.text(14, 76.5, "성인 일반인 대조군 (만 20~65세, 상지 질환 이력 없음) ➔ 양손 협응 정상 기준 모델(Normative) 구축", fontsize=11, color=C_TEXT_LIGHT, va='center')

    # 2) 안전 장치
    ax.text(62, 79.5, "🛡️ 환자 개별 ROM 제한:", fontsize=11, fontweight='bold', color=C_AMBER, va='center')
    ax.text(77, 79.5, "사전 측정한 손가락별 가동범위 내에서만 작동 (과신전 원천 차단)", fontsize=10.5, color=C_TEXT_LIGHT, va='center')
    ax.text(62, 76.5, "🛡️ 비상정지 및 휴식:", fontsize=11, fontweight='bold', color=C_AMBER, va='center')
    ax.text(77, 76.5, "치료사 비상정지(E-Stop) 구비 / 세트 간 2~3분 필수 휴식(피로도 방지)", fontsize=10.5, color=C_TEXT_LIGHT, va='center')

    # --- 3. 중앙 영역: 1회 세션 타임라인 (Session Timeline - 5 Steps) ---
    timeline_bg = patches.FancyBboxPatch((2, 38), 96, 35, boxstyle="round,pad=0.5,rounding_size=1.0",
                                         linewidth=1.2, edgecolor=C_CARD_BORDER, facecolor=C_CARD_BG)
    ax.add_patch(timeline_bg)

    ax.text(4, 70, "2. 1회 방문 임상 세션 타임라인 (총 35~40분 소요: 환자 부담 최소화 설계)", fontsize=14, fontweight='bold', color=C_TEXT_WHITE, va='center')
    ax.text(96, 70, "※ 단일 세션으로 진행되며 환자 피로도를 고려해 충분한 휴식 제공", fontsize=11, color=C_TEXT_MUTED, ha='right', va='center')

    # 5개 스텝 박스 정의
    steps = [
        {
            "num": "Step 1 (0~10분)",
            "title": "임상 기준선 평가",
            "actor": "치료사 직접 수행",
            "desc": ["• FMA-UE 상지/손 평가", "• 손가락 관절 ROM 측정", "• 환자 상태 기준선 확보"],
            "color": C_PURPLE,
            "badge": "Clinical Baseline"
        },
        {
            "num": "Step 2 (10~15분)",
            "title": "사전 기능 측정 (Pre)",
            "actor": "장갑 미착용 (Bare-hand)",
            "desc": ["• 카메라 캘리브레이션", "• 양손 동시 파지 16회", "  (원통형 8회 + 구형 8회)", "• 중재 전 초기 각도오차 산출"],
            "color": C_CYAN,
            "badge": "Pre-Test"
        },
        {
            "num": "Step 3 (15~28분)",
            "title": "Master-Slave 물리적 중재",
            "actor": "공압장갑 착용 (핵심 중재)",
            "desc": ["• 건측(Master) 동작 측정", "➔ 환측(Slave) 공압 물리 구동", "• 파지-이완 10회 × 3세트", "• 세트 간 2~3분 필수 휴식"],
            "color": C_BLUE,
            "badge": "Physical Mirror Intervention",
            "highlight": True
        },
        {
            "num": "Step 4 (28~33분)",
            "title": "사후 기능 측정 (Post)",
            "actor": "장갑 미착용 (Bare-hand)",
            "desc": ["• Step 2와 동일 과제 재실시", "• 양손 동시 파지 16회", "• 중재 직후 즉각적", "  관절 오차 개선율 비교"],
            "color": C_GREEN,
            "badge": "Post-Test"
        },
        {
            "num": "Step 5 (33~38분)",
            "title": "환자 피드백 & 설문",
            "actor": "사용성 및 안전성 확인",
            "desc": ["• 장갑 착용감/만족도 (SUS)", "• 통증/불편감 여부 확인", "• 세션 종료 및 환자 귀가"],
            "color": C_AMBER,
            "badge": "Survey & Debrief"
        }
    ]

    box_w = 17.5
    box_gap = 1.6
    start_x = 4.2
    box_y = 41.5
    box_h = 24.5

    for i, s in enumerate(steps):
        bx = start_x + i * (box_w + box_gap)
        
        # 박스 테두리 & 배경
        if s.get("highlight"):
            step_box = patches.FancyBboxPatch((bx, box_y), box_w, box_h, boxstyle="round,pad=0.3,rounding_size=0.8",
                                              linewidth=2.0, edgecolor=C_BLUE, facecolor='#152A4A')
        else:
            step_box = patches.FancyBboxPatch((bx, box_y), box_w, box_h, boxstyle="round,pad=0.3,rounding_size=0.8",
                                              linewidth=1.0, edgecolor=C_CARD_BORDER, facecolor=C_STEP_BG)
        ax.add_patch(step_box)

        # 상단 번호 & 배지
        ax.text(bx + 1, box_y + box_h - 2.2, s["num"], fontsize=10, fontweight='bold', color=s["color"], va='center')
        ax.text(bx + 1, box_y + box_h - 5.0, s["title"], fontsize=13, fontweight='bold', color=C_TEXT_WHITE, va='center')
        
        # 수행 주체/조건 바
        actor_badge = patches.FancyBboxPatch((bx + 1, box_y + box_h - 8.5), box_w - 2, 2.3, boxstyle="round,pad=0.1,rounding_size=0.4",
                                             linewidth=0, facecolor='rgba(255,255,255,0.07)')
        ax.add_patch(actor_badge)
        ax.text(bx + (box_w / 2), box_y + box_h - 7.3, s["actor"], fontsize=9.5, fontweight='bold', color=s["color"], ha='center', va='center')

        # 세부 항목들
        cur_y = box_y + box_h - 11.2
        for line in s["desc"]:
            ax.text(bx + 1.2, cur_y, line, fontsize=10, color=C_TEXT_LIGHT, va='center')
            cur_y -= 2.6

        # 다음 스텝 화살표 (마지막 제외)
        if i < len(steps) - 1:
            ax.text(bx + box_w + (box_gap / 2), box_y + (box_h / 2), "➔", fontsize=15, fontweight='bold', color='#475569', ha='center', va='center')

    # --- 4. 하단 영역: 2개 카드 (좌측: 실험 장비 / 우측: 의료진 제공 리포트) ---
    
    # 4-1 좌측: 실험 장비 및 피험자 세팅
    hw_box = patches.FancyBboxPatch((2, 3), 46.5, 33, boxstyle="round,pad=0.5,rounding_size=1.0",
                                    linewidth=1.2, edgecolor=C_CARD_BORDER, facecolor=C_CARD_BG)
    ax.add_patch(hw_box)
    ax.text(4, 33, "3. 실험 셋업 및 환자 착용 형태 (Setup)", fontsize=13, fontweight='bold', color=C_CYAN, va='center')

    hw_items = [
        ("📷 3D 마커리스 비전 리그", "Top/Left/Right 3방향 카메라 ➔ MediaPipe 21개 랜드마크 3D 관절각도 실시간 추출 (환자 마커 부착 부담 제로)"),
        ("🤖 Master-Slave 공압장갑", "건측(Master 센서 장갑): 착용자 의도 파악 ➔ 환측(Slave 공압 장갑): 부드러운 공압 굽힘/폄 물리 구동"),
        ("🎯 일상동작(ADL) 파지 과제", "원통형(ø 5cm, 물컵/손잡이 모사) & 구형(ø 7cm, 공/과일 모사) 파지 과제 각 8회 반복 (총 16회)"),
        ("🛡️ 센서 융합 및 신호 보정", "IMU 관성 센서 융합 + One-Euro Filter로 환자 손 떨림 및 측정 노이즈 완벽 보정")
    ]

    h_y = 28.5
    for title, detail in hw_items:
        item_bg = patches.FancyBboxPatch((4, h_y - 4.5), 42.5, 5.5, boxstyle="round,pad=0.2,rounding_size=0.5",
                                         linewidth=0.8, edgecolor='#24334C', facecolor='#0F1829')
        ax.add_patch(item_bg)
        ax.text(5.5, h_y - 1.2, title, fontsize=11, fontweight='bold', color=C_TEXT_WHITE, va='center')
        ax.text(5.5, h_y - 3.4, detail, fontsize=9.5, color=C_TEXT_MUTED, va='center')
        h_y -= 6.5

    # 4-2 우측: 의료진에게 제공되는 정량 분석 리포트 (Clinical Outputs)
    res_box = patches.FancyBboxPatch((51.5, 3), 46.5, 33, boxstyle="round,pad=0.5,rounding_size=1.0",
                                     linewidth=1.2, edgecolor=C_CARD_BORDER, facecolor=C_CARD_BG)
    ax.add_patch(res_box)
    ax.text(53.5, 33, "4. 의료진에게 제공되는 정량적 재활 평가 리포트 (Outputs)", fontsize=13, fontweight='bold', color=C_GREEN, va='center')

    res_items = [
        ("📊 관절별 정량 각도 회복 리포트", "손가락 5개 × (MCP, PIP, DIP) 및 손목 각도의 정량적 가동범위(ROM) & 건측 대비 오차(MAE/RMSE) 수치화"),
        ("⚡ 물리적 미러테라피 즉각 효과 검증", "중재 전(Pre) vs 중재 직후(Post) 관절 오차 감소율(ΔError) 및 통계적 유의성(Paired t-test, Cohen's d) 도출"),
        ("🧩 AI 기반 손상 관절 국소화 히트맵", "정상 모델(일반인) 대비 환자의 어떤 손가락 마디가 주로 저하되었는지 SHAP 기여도 히트맵으로 시각 제공"),
        ("🩺 기존 주관적 임상 평가(FMA) 보완", "치료사의 육안 관찰 평가에 더해, 객관적인 디지털 바이오마커 데이터를 제공하여 맞춤형 재활 계획 지원")
    ]

    r_y = 28.5
    for title, detail in res_items:
        item_bg = patches.FancyBboxPatch((53.5, r_y - 4.5), 42.5, 5.5, boxstyle="round,pad=0.2,rounding_size=0.5",
                                         linewidth=0.8, edgecolor='#24334C', facecolor='#0F1829')
        ax.add_patch(item_bg)
        ax.text(55, r_y - 1.2, title, fontsize=11, fontweight='bold', color=C_TEXT_WHITE, va='center')
        ax.text(55, r_y - 3.4, detail, fontsize=9.5, color=C_TEXT_MUTED, va='center')
        r_y -= 6.5

    plt.tight_layout()
    plt.savefig(output_path, dpi=200, facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close()
    print(f"Image successfully saved to {output_path}")

if __name__ == "__main__":
    create_protocol_image("실험프로토콜_병원미팅용.png")
