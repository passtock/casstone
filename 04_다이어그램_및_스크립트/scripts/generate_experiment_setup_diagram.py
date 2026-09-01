import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, Circle, Rectangle, Wedge, Polygon
import numpy as np

def generate_bimanual_korean_setup_diagram(output_path="실험_세팅_및_방법_다이어그램.png"):
    # 폰트 설정 (Windows 맑은 고딕)
    plt.rc('font', family='Malgun Gothic')
    plt.rcParams['axes.unicode_minus'] = False

    # 16:9 고화질 캔버스 (18 x 10.2 인치, 300 DPI -> 5400x3060)
    fig, ax = plt.subplots(figsize=(18, 10.2), dpi=300)
    fig.patch.set_facecolor('#FFFFFF')
    ax.set_facecolor('#FFFFFF')
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis('off')

    # 공통 스타일 토큰
    BORDER_COLOR = '#0F172A'
    LW_MAIN = 2.4

    # -------------------------------------------------------------
    # 0. 상단 메인 헤더
    # -------------------------------------------------------------
    title_box = FancyBboxPatch((2, 90.5), 96, 8.0, boxstyle="round,pad=0.2,rounding_size=0.8",
                               linewidth=1.8, edgecolor='#CBD5E1', facecolor='#F8FAFC')
    ax.add_patch(title_box)
    ax.text(4, 94.5, "공압장갑 Master-Slave 미러테라피 실험 구성 및 세부 프로토콜", fontsize=26, fontweight='bold', color='#0F172A', va='center')

    # -------------------------------------------------------------
    # 1. [좌측 영역] 양손 동시 파지 실험 배치도 (Top-Down Setup)
    # -------------------------------------------------------------
    left_w = 47.5
    left_bg = FancyBboxPatch((2, 2.0), left_w, 87.0, boxstyle="round,pad=0.2,rounding_size=1.0",
                             linewidth=LW_MAIN, edgecolor=BORDER_COLOR, facecolor='#F8FAFC')
    ax.add_patch(left_bg)

    # 좌측 헤더 바
    lh_box = FancyBboxPatch((2, 80.5), left_w, 8.5, boxstyle="round,pad=0.2,rounding_size=1.0",
                            linewidth=LW_MAIN, edgecolor=BORDER_COLOR, facecolor='#1E293B')
    ax.add_patch(lh_box)
    ax.text(2 + left_w/2, 84.75, "양손 동시 파지 실험 환경 배치도", fontsize=22, fontweight='bold', color='#FFFFFF', ha='center', va='center')

    # --- 1) 메인 책상 (통합형 데스크) ---
    desk_box = FancyBboxPatch((5.5, 23.0), 40.5, 47.5, boxstyle="round,pad=0.1,rounding_size=0.8",
                              linewidth=2.0, edgecolor='#94A3B8', facecolor='#E2E8F0')
    ax.add_patch(desk_box)
    ax.text(10.5, 68.0, "[실험 테이블]", fontsize=14, fontweight='bold', color='#64748B', ha='center', va='center')

    # 노트북 (우측 상단)
    nb_box = FancyBboxPatch((33.0, 63.0), 11.5, 5.8, boxstyle="round,pad=0.1,rounding_size=0.4",
                            linewidth=1.6, edgecolor=BORDER_COLOR, facecolor='#334155')
    ax.add_patch(nb_box)
    ax.add_patch(FancyBboxPatch((34.2, 64.0), 9.1, 3.8, boxstyle="round,pad=0.05,rounding_size=0.2",
                                linewidth=0.8, edgecolor='none', facecolor='#38BDF8'))
    ax.text(38.7, 60.5, "노트북 (데이터 수집)", fontsize=13.5, fontweight='bold', color='#0F172A', ha='center', va='center')

    # --- 2) 전방 3D 뎁스 카메라 (Depth Camera 단일 구성) 및 시야각(FOV) ---
    cam_pos = (25.75, 71.0)
    
    # 뎁스 카메라 시야각 (테이블 및 양손 영역을 부드럽게 감싸는 조화로운 FOV)
    fov_pts = np.array([
        [cam_pos[0], cam_pos[1]-1.5],
        [7.0, 32.0],
        [44.5, 32.0]
    ])
    fov_poly = Polygon(fov_pts, closed=True, facecolor=(14/255, 165/255, 233/255, 0.15), 
                       edgecolor='#0284C7', lw=1.8, linestyle='--')
    ax.add_patch(fov_poly)

    # 뎁스 센서 본체 (RGB-D 센서 바 디자인: 와이드 직사각형)
    cam_w, cam_h = 11.0, 3.2
    ax.add_patch(FancyBboxPatch((cam_pos[0]-cam_w/2, cam_pos[1]-cam_h/2), cam_w, cam_h, 
                                boxstyle="round,pad=0.1,rounding_size=0.5",
                                linewidth=1.8, edgecolor=BORDER_COLOR, facecolor='#0284C7'))
    # 뎁스 센서 렌즈 3종 (IR 이미저 + RGB + IR 프로젝터)
    ax.add_patch(Circle((cam_pos[0]-3.2, cam_pos[1]), 0.65, facecolor='#0F172A'))
    ax.add_patch(Circle((cam_pos[0], cam_pos[1]), 0.85, facecolor='#0F172A', edgecolor='#38BDF8', lw=1.0))
    ax.add_patch(Circle((cam_pos[0]+3.2, cam_pos[1]), 0.65, facecolor='#0F172A'))
    
    # 카메라 라벨
    ax.text(cam_pos[0], cam_pos[1]+3.2, "전방 3D 뎁스 카메라 (Depth Camera)", fontsize=15, fontweight='bold', color='#0369A1', ha='center', va='center')

    # 종횡비 보정 계수 (18 / 10.2 = 1.7647)
    AR = 18.0 / 10.2

    # --- 3) 양손 파지 물체 2개 (원통 5cm / 구 7cm) ---
    t_left = (16.5, 47.5)
    t_right = (35.0, 47.5)
    w_ball = 3.6
    h_ball = w_ball * AR
    w_ring = 4.8
    h_ring = w_ring * AR

    # 좌측 물체 (왼손용)
    ax.add_patch(patches.Ellipse(t_left, w_ring, h_ring, facecolor='#FFFFFF', edgecolor='#2563EB', lw=1.6, linestyle=':'))
    ax.add_patch(patches.Ellipse(t_left, w_ball, h_ball, facecolor='#F59E0B', edgecolor=BORDER_COLOR, lw=1.8))
    ax.add_patch(patches.Ellipse((t_left[0]-0.5, t_left[1]+0.8), 1.0, 1.0*AR, facecolor='#FEF3C7'))
    ax.text(t_left[0], t_left[1]+6.0, "좌측 물체 (원통/구)", fontsize=14.5, fontweight='bold', color='#B45309', ha='center', va='center')

    # 우측 물체 (오른손용)
    ax.add_patch(patches.Ellipse(t_right, w_ring, h_ring, facecolor='#FFFFFF', edgecolor='#2563EB', lw=1.6, linestyle=':'))
    ax.add_patch(patches.Ellipse(t_right, w_ball, h_ball, facecolor='#F59E0B', edgecolor=BORDER_COLOR, lw=1.8))
    ax.add_patch(patches.Ellipse((t_right[0]-0.5, t_right[1]+0.8), 1.0, 1.0*AR, facecolor='#FEF3C7'))
    ax.text(t_right[0], t_right[1]+6.0, "우측 물체 (원통/구)", fontsize=14.5, fontweight='bold', color='#B45309', ha='center', va='center')

    # --- 4) 양손 시작 마커 2개 (물체 바로 뒤쪽에서 대기) ---
    m_left = (16.5, 30.0)
    m_right = (35.0, 30.0)

    # 좌측 시작 마커 (왼손 대기)
    ax.add_patch(FancyBboxPatch((m_left[0]-3.0, m_left[1]-3.0), 6.0, 6.0, boxstyle="round,pad=0.1,rounding_size=0.5",
                                linewidth=2.0, edgecolor='#2563EB', facecolor='#DBEAFE'))
    ax.text(m_left[0], m_left[1], "왼손 시작\n마커", fontsize=13.5, fontweight='bold', color='#1D4ED8', ha='center', va='center')
    ax.text(m_left[0], m_left[1]-5.0, "[손 쥔 상태 대기]", fontsize=13, fontweight='bold', color='#1E40AF', ha='center', va='center')

    # 우측 시작 마커 (오른손 대기)
    ax.add_patch(FancyBboxPatch((m_right[0]-3.0, m_right[1]-3.0), 6.0, 6.0, boxstyle="round,pad=0.1,rounding_size=0.5",
                                linewidth=2.0, edgecolor='#2563EB', facecolor='#DBEAFE'))
    ax.text(m_right[0], m_right[1], "오른손 시작\n마커", fontsize=13.5, fontweight='bold', color='#1D4ED8', ha='center', va='center')
    ax.text(m_right[0], m_right[1]-5.0, "[손 쥔 상태 대기]", fontsize=13, fontweight='bold', color='#1E40AF', ha='center', va='center')

    # --- 5) 직선 접근 궤적 화살표 ---
    # 좌측 직선 화살표
    ax.annotate('', xy=(t_left[0], t_left[1]-h_ball/2-0.8), xytext=(m_left[0], m_left[1]+3.4),
                arrowprops=dict(facecolor='#DC2626', edgecolor='#DC2626', width=4.0, headwidth=12, headlength=10))
    ax.text(m_left[0]-5.6, (t_left[1]+m_left[1])/2, "앞으로 이동", fontsize=14, fontweight='bold', color='#DC2626', 
            ha='center', va='center', bbox=dict(boxstyle='round,pad=0.3', facecolor='#FFFFFF', edgecolor='#FCA5A5', lw=1.5))

    # 우측 직선 화살표
    ax.annotate('', xy=(t_right[0], t_right[1]-h_ball/2-0.8), xytext=(m_right[0], m_right[1]+3.4),
                arrowprops=dict(facecolor='#DC2626', edgecolor='#DC2626', width=4.0, headwidth=12, headlength=10))
    ax.text(m_right[0]+5.6, (t_right[1]+m_right[1])/2, "앞으로 이동", fontsize=14, fontweight='bold', color='#DC2626', 
            ha='center', va='center', bbox=dict(boxstyle='round,pad=0.3', facecolor='#FFFFFF', edgecolor='#FCA5A5', lw=1.5))

    # --- 6) 피험자 (하단 중앙) ---
    human_pos = (25.75, 11.0)
    # 의자
    ax.add_patch(FancyBboxPatch((human_pos[0]-7.5, human_pos[1]-4.5), 15, 7.5, boxstyle="round,pad=0.2,rounding_size=1.0",
                                linewidth=1.6, edgecolor='#94A3B8', facecolor='#E2E8F0'))
    # 머리
    ax.add_patch(patches.Ellipse((human_pos[0], human_pos[1]+1.2), 3.4, 3.4*AR, facecolor='#FED7AA', edgecolor=BORDER_COLOR, lw=1.6))
    # 어깨 및 상체
    ax.add_patch(FancyBboxPatch((human_pos[0]-8.5, human_pos[1]-3.5), 17, 5.2, boxstyle="round,pad=0.5,rounding_size=1.2",
                                linewidth=2.0, edgecolor=BORDER_COLOR, facecolor='#3B82F6'))
    ax.text(human_pos[0], human_pos[1]-0.5, "피험자 (환자 / 대조군)", fontsize=16, fontweight='bold', color='#FFFFFF', ha='center', va='center')

    # --- 7) 치수선 ---
    def draw_dim(p1, p2, label, offset=(0,0), text_pos='center', color='#334155'):
        ax.annotate('', xy=p2, xytext=p1,
                    arrowprops=dict(arrowstyle="<->", color=color, lw=2.2))
        mid_x = (p1[0] + p2[0])/2 + offset[0]
        mid_y = (p1[1] + p2[1])/2 + offset[1]
        ax.text(mid_x, mid_y, label, fontsize=15, fontweight='bold', color=color,
                ha=text_pos, va='center', bbox=dict(boxstyle='round,pad=0.25', facecolor='#FFFFFF', edgecolor='none', alpha=0.95))

    # 전방 뎁스 카메라 <-> 물체 라인: 50cm
    draw_dim((25.75, 47.5), (25.75, 69.0), "50 cm", offset=(-3.6, 0))
    # 피험자 <-> 테이블/마커: 50cm
    draw_dim((25.75, 26.0), (25.75, 14.0), "50 cm", offset=(-3.6, 0))

    # 좌측 하단 강조 배지
    ax.add_patch(FancyBboxPatch((3.5, 3.5), left_w - 3.0, 5.2, boxstyle="round,pad=0.2,rounding_size=0.4",
                                linewidth=1.2, edgecolor='#94A3B8', facecolor='#FFFFFF'))
    ax.text(2 + left_w/2, 6.1, "★ 책상 위 양손 동시 파지 & 전방 3D 뎁스 카메라(50cm) 실시간 측정", 
            fontsize=14.5, fontweight='bold', color='#0F172A', ha='center', va='center')

    # -------------------------------------------------------------
    # 2. [우측 영역] 연구계획서 기반 세부 실험 프로토콜
    # -------------------------------------------------------------
    right_x = 51.0
    right_w = 47.0
    right_bg = FancyBboxPatch((right_x, 2.0), right_w, 87.0, boxstyle="round,pad=0.2,rounding_size=1.0",
                              linewidth=LW_MAIN, edgecolor=BORDER_COLOR, facecolor='#F8FAFC')
    ax.add_patch(right_bg)

    # 우측 헤더 바
    rh_box = FancyBboxPatch((right_x, 80.5), right_w, 8.5, boxstyle="round,pad=0.2,rounding_size=1.0",
                            linewidth=LW_MAIN, edgecolor=BORDER_COLOR, facecolor='#1E293B')
    ax.add_patch(rh_box)
    ax.text(right_x + right_w/2, 84.75, "연구계획서 기반 세부 실험 프로토콜", fontsize=22, fontweight='bold', color='#FFFFFF', ha='center', va='center')

    # --- [카드 1] 파지 과제 및 물체 규격 (원통 8회 + 구 8회) ---
    c1_box = FancyBboxPatch((right_x + 1.5, 62.5), right_w - 3.0, 16.5, boxstyle="round,pad=0.2,rounding_size=0.8",
                            linewidth=2.0, edgecolor='#2563EB', facecolor='#FFFFFF')
    ax.add_patch(c1_box)

    # 카드 1 배지
    ax.add_patch(FancyBboxPatch((right_x + 2.8, 73.8), 29.5, 4.6, boxstyle="round,pad=0.1,rounding_size=0.4",
                                linewidth=1.2, edgecolor='#2563EB', facecolor='#DBEAFE'))
    ax.text(right_x + 17.5, 76.1, "[파지 과제] 파지 물체 2종 (총 16회)", fontsize=16, fontweight='bold', color='#1E40AF', ha='center', va='center')
    ax.text(right_x + 33.8, 76.1, "(양손 동시 파지)", fontsize=14, fontweight='bold', color='#64748B', va='center')

    ax.text(right_x + 3.5, 70.0, "① 원통형 파지 (지름 5cm)", fontsize=15.5, fontweight='bold', color='#0F172A', va='center')
    ax.text(right_x + 27.5, 70.0, "• 8회 반복 (Cylinder Grasp)", fontsize=14.5, fontweight='bold', color='#2563EB', va='center')
    ax.text(right_x + 3.5, 66.2, "② 구형 파지 (지름 7cm)", fontsize=15.5, fontweight='bold', color='#0F172A', va='center')
    ax.text(right_x + 27.5, 66.2, "• 8회 반복 (Spherical Grasp)", fontsize=14.5, fontweight='bold', color='#2563EB', va='center')
    ax.text(right_x + 3.5, 63.2, "• 일반인: 장갑 미착용 양손 동시 파지 -> 정상 기준 모델(Normative) 구축", fontsize=13.5, fontweight='bold', color='#475569', va='center')

    # --- [카드 2] 편마비 환자 4단계 임상 실험 절차 ---
    c2_box = FancyBboxPatch((right_x + 1.5, 20.0), right_w - 3.0, 41.0, boxstyle="round,pad=0.2,rounding_size=0.8",
                            linewidth=2.0, edgecolor='#D97706', facecolor='#FFFFFF')
    ax.add_patch(c2_box)

    # 카드 2 배지
    ax.add_patch(FancyBboxPatch((right_x + 2.8, 55.2), 31.5, 4.6, boxstyle="round,pad=0.1,rounding_size=0.4",
                                linewidth=1.2, edgecolor='#D97706', facecolor='#FEF3C7'))
    ax.text(right_x + 18.5, 57.5, "[환자 프로토콜] 4단계 임상 절차", fontsize=16, fontweight='bold', color='#92400E', ha='center', va='center')
    ax.text(right_x + 35.5, 57.5, "(미러테라피 중재)", fontsize=14, fontweight='bold', color='#64748B', va='center')

    p_steps = [
        ("1단계. FMA 상태 평가", "전문 치료사가 FMA-UE 평가를 실시하여 환자 기능 기준선 확보", '#0F172A'),
        ("2단계. 사전 측정 (장갑 미착용)", "일반인과 동일한 양손 동시 파지(원통 8회+구 8회) -> 중재 전 오차 측정", '#0F172A'),
        ("3단계. Master-Slave 중재", "공압장갑 착용 후 건측 움직임을 환측이 물리적으로 추종 (10회×3세트)", '#C2410C'),
        ("4단계. 사후 측정 (장갑 미착용)", "2단계와 동일하게 재실시 -> 중재 전후 관절각도 오차 즉각 개선도 검증", '#0F172A')
    ]
    py = 51.5
    for title, desc, col in p_steps:
        ax.text(right_x + 3.5, py, title, fontsize=15.5, fontweight='bold', color=col, va='center')
        ax.text(right_x + 3.5, py - 2.8, f"• {desc}", fontsize=14.0, fontweight='bold', color='#334155', va='center')
        py -= 6.2

    # --- 하단 핵심 측정 지표 및 안전 안내 ---
    bot_box = FancyBboxPatch((right_x + 1.5, 3.5), right_w - 3.0, 15.0, boxstyle="round,pad=0.2,rounding_size=0.8",
                             linewidth=2.0, edgecolor='#DC2626', facecolor='#FEF2F2')
    ax.add_patch(bot_box)

    ax.text(right_x + 3.5, 15.6, "[핵심 측정 지표 및 임상 안전]", fontsize=16, fontweight='bold', color='#DC2626', va='center')
    ax.text(right_x + 3.5, 11.8, "① 정량 평가: 3D 뎁스 카메라로 손가락 21개 관절 3차원 각도 오차(MAE), 파지구경 측정", fontsize=13.0, fontweight='bold', color='#1E293B', va='center')
    ax.text(right_x + 3.5, 7.6, "② 임상 안전: 공압장갑 압력 상한·ROM 초과 방지 안전장치, 세트 간 2~3분 휴식", fontsize=13.0, fontweight='bold', color='#1E293B', va='center')

    # 최종 저장
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='#FFFFFF')
    plt.close()
    print(f"Refined single depth camera diagram successfully saved: {output_path}")

if __name__ == "__main__":
    generate_bimanual_korean_setup_diagram("c:/Users/passp/Desktop/univercity/4-2/캡스톤/실험_세팅_및_방법_다이어그램.png")
