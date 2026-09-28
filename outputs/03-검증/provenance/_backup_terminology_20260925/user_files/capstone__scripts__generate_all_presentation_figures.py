# -*- coding: utf-8 -*-
"""
Generate high-resolution visual charts and diagrams for the presentation slide deck.
Figures are saved to scripts/figures/
"""

import os
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False

out_dir = Path(r"C:\Users\passp\OneDrive\바탕 화면\jeayong\capstone\scripts\figures")
out_dir.mkdir(parents=True, exist_ok=True)

# -------------------------------------------------------------------------
# Figure 1: PrimSeq Clinical Bottleneck Bar Chart
# -------------------------------------------------------------------------
def make_fig_primseq():
    fig, ax = plt.subplots(figsize=(6.2, 4.2), dpi=200)
    fig.patch.set_facecolor('#FFFFFF')
    ax.set_facecolor('#F8FAFC')

    categories = ['숙련된 치료사\n(Manual Annotation)', 'AI 자동화\n(PrimSeq Pipeline)']
    values = [513.6, 1.4]
    colors = ['#DC2626', '#0284C7']

    bars = ax.bar(categories, values, color=colors, width=0.48, edgecolor=['#991B1B', '#0369A1'], linewidth=1.5)
    ax.set_yscale('log')
    ax.set_ylim(0.5, 1200)
    ax.set_ylabel('비디오 판독 소요 시간 (시간, Log scale)', fontsize=11, fontweight='bold', color='#1E293B')
    ax.set_title('6.4시간 분량 재활 비디오 분석 시간 비교 (PrimSeq)', fontsize=12.5, fontweight='bold', color='#102C57', pad=14)

    # Value Labels
    ax.text(0, 560, '513.6 시간\n(약 21.4일 연속)', ha='center', va='bottom', fontsize=11, fontweight='bold', color='#DC2626')
    ax.text(1, 1.8, '1.4 시간\n(약 84분)', ha='center', va='bottom', fontsize=11, fontweight='bold', color='#0284C7')

    # Badge Box
    ax.text(0.5, 45, '[실증] AI 도입 시 366배 고속화!\n사람 치료사의 극심한 판독 피로도 해소',
            ha='center', va='center', fontsize=11, fontweight='bold', color='#0F172A',
            bbox=dict(boxstyle='round,pad=0.6', facecolor='#FEF3C7', edgecolor='#F59E0B', linewidth=1.5))

    ax.grid(axis='y', linestyle='--', alpha=0.5)
    ax.tick_params(axis='x', labelsize=11)
    ax.tick_params(axis='y', labelsize=10)
    plt.tight_layout()
    fig.savefig(out_dir / 'fig_primseq.png')
    plt.close(fig)

# -------------------------------------------------------------------------
# Figure 2: Visual Hallucination Mechanism
# -------------------------------------------------------------------------
def make_fig_hallucination():
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.2, 4.0), dpi=200)
    fig.patch.set_facecolor('#FFFFFF')

    # Left: 2D Perspective (Overlap -> Hallucination)
    ax1.set_facecolor('#FEF2F2')
    ax1.set_xlim(0, 10)
    ax1.set_ylim(0, 10)
    ax1.axis('off')
    ax1.set_title('2D 카메라 시야 (단안 RGB)\n깊이 축 소실로 인한 환각', fontsize=11.5, fontweight='bold', color='#DC2626')

    # Draw Cup
    cup = patches.Rectangle((4.5, 3.0), 2.5, 3.5, facecolor='#93C5FD', edgecolor='#1D4ED8', linewidth=2)
    ax1.add_patch(cup)
    ax1.text(5.75, 4.75, '컵\n(Cup)', ha='center', va='center', fontsize=10.5, fontweight='bold', color='#1E3A8A')

    # Draw Hand overlapping
    hand = patches.Rectangle((3.5, 4.0), 3.0, 3.0, facecolor='#FCA5A5', edgecolor='#DC2626', linewidth=2, alpha=0.7)
    ax1.add_patch(hand)
    ax1.text(4.2, 6.2, '환자 손 (Hand)', ha='center', va='center', fontsize=10, fontweight='bold', color='#991B1B')

    ax1.text(5.0, 1.2, '[2D 오판] 화면상 겹침 발생\n→ VLM: "파지 완료" 허위 판독 (환각!)',
             ha='center', va='center', fontsize=10.5, fontweight='bold', color='#DC2626',
             bbox=dict(boxstyle='round,pad=0.5', facecolor='#FFFFFF', edgecolor='#DC2626', linewidth=1.5))

    # Right: 3D Top View (Actual Z-distance -> Contact False)
    ax2.set_facecolor('#F0FDF4')
    ax2.set_xlim(0, 10)
    ax2.set_ylim(0, 10)
    ax2.axis('off')
    ax2.set_title('3D 실측 공간 (RealSense Depth)\n물리적 거리 검증', fontsize=11.5, fontweight='bold', color='#15803D')

    # Draw Cup in 3D
    cup3d = patches.Circle((5.0, 7.0), 1.2, facecolor='#93C5FD', edgecolor='#1D4ED8', linewidth=2)
    ax2.add_patch(cup3d)
    ax2.text(5.0, 7.0, '컵\nZ=75cm', ha='center', va='center', fontsize=9.5, fontweight='bold', color='#1E3A8A')

    # Draw Hand in 3D (separated by 10cm)
    hand3d = patches.Rectangle((3.8, 2.5), 2.4, 1.8, facecolor='#86EFAC', edgecolor='#15803D', linewidth=2)
    ax2.add_patch(hand3d)
    ax2.text(5.0, 3.4, '환자 손\nZ=65cm', ha='center', va='center', fontsize=9.5, fontweight='bold', color='#14532D')

    # Arrow showing gap
    ax2.annotate('', xy=(5.0, 5.8), xytext=(5.0, 4.3),
                 arrowprops=dict(arrowstyle='<->', color='#DC2626', lw=2))
    ax2.text(5.8, 5.0, '거리 10cm\n(미접촉!)', color='#DC2626', fontsize=10, fontweight='bold')

    ax2.text(5.0, 1.2, '[3D 정답] 실제 물리 거리 10cm\n→ 센서: "접촉 실패" 정확히 판정!',
             ha='center', va='center', fontsize=10.5, fontweight='bold', color='#15803D',
             bbox=dict(boxstyle='round,pad=0.5', facecolor='#FFFFFF', edgecolor='#15803D', linewidth=1.5))

    plt.tight_layout()
    fig.savefig(out_dir / 'fig_hallucination.png')
    plt.close(fig)

# -------------------------------------------------------------------------
# Figure 3: Core Engineering Contributions Block Diagram
# -------------------------------------------------------------------------
def make_fig_engineering():
    fig, ax = plt.subplots(figsize=(11.5, 3.8), dpi=200)
    fig.patch.set_facecolor('#FFFFFF')
    ax.set_facecolor('#FFFFFF')
    ax.set_xlim(0, 11.5)
    ax.set_ylim(0, 3.8)
    ax.axis('off')

    boxes = [
        ("1. 3D 생체역학 엔진", "• RealSense D455 하드웨어 정렬\n• OpenCV K행렬 왜곡 보정\n• 21개 관절 3D mm 좌표 역투영", "#EFF6FF", "#0284C7"),
        ("2. 속도 변곡점 알고리즘", "• |v(t)| < 10 mm/s 진입/이탈 탐색\n• 환자 3초 버퍼 지시 연동\n• 2초 유지(Plateau) 객관적 검출", "#F0FDF4", "#0D9488"),
        ("3. 결정론적 채점 머신", "• VLM은 증거 기반 상태만 추출\n• 파이썬 규칙 엔진 0/1/2점 변환\n• 모델 점수 왜곡/환각 원천 차단", "#FFFBEB", "#D97706"),
        ("4. 엣지 아키텍처 최적화", "• 단일 PC RTX 5090 32GB 구동\n• AWQ 4-bit / SDPA 메모리 바운딩\n• 외부 API 의존 0%, 의료 보안 100%", "#FAF5FF", "#7E22CE"),
    ]

    for i, (title, desc, bg, bdr) in enumerate(boxes):
        x = 0.2 + i * 2.85
        rect = patches.FancyBboxPatch((x, 0.4), 2.6, 3.0, boxstyle="round,pad=0.15",
                                      facecolor=bg, edgecolor=bdr, linewidth=2.0)
        ax.add_patch(rect)
        ax.text(x + 1.3, 3.05, title, ha='center', va='center', fontsize=11.5, fontweight='bold', color=bdr)
        ax.text(x + 0.15, 1.65, desc, ha='left', va='center', fontsize=9.8, color='#1E293B', linespacing=1.35)

        if i < 3:
            ax.annotate('', xy=(x + 2.85, 1.9), xytext=(x + 2.6, 1.9),
                        arrowprops=dict(arrowstyle='->', color='#64748B', lw=2.5))

    plt.tight_layout()
    fig.savefig(out_dir / 'fig_engineering.png')
    plt.close(fig)

# -------------------------------------------------------------------------
# Figure 4: Biomechanical Kinematic Features Curve
# -------------------------------------------------------------------------
def make_fig_kinematics():
    fig, ax = plt.subplots(figsize=(6.6, 4.0), dpi=200)
    fig.patch.set_facecolor('#FFFFFF')
    ax.set_facecolor('#F8FAFC')

    t = np.linspace(0, 8, 500)
    # Synthetic grasp aperture curve: reach -> peak -> grasp hold -> release
    a = (25 + 75 / (1 + np.exp(-3.5 * (t - 1.2))) * (1 / (1 + np.exp(4.0 * (t - 2.8))))
         + 45 / (1 + np.exp(-4.0 * (t - 2.7))) * (1 / (1 + np.exp(3.0 * (t - 5.5))))
         + 85 / (1 + np.exp(-3.5 * (t - 5.6))))
    # add small realistic noise
    np.random.seed(42)
    a += np.random.normal(0, 0.6, len(t))

    ax.plot(t, a, color='#1E40AF', lw=2.5, label='손가락 간격 a(t) [mm]')

    # F1 Peak Aperture
    idx_peak = np.argmax(a[:250])
    t_peak, a_peak = t[idx_peak], a[idx_peak]
    ax.plot(t_peak, a_peak, 'r*', markersize=14, label='F1: 최대 파지폭 (Peak Aperture)')
    ax.annotate(f'F1 (MGA)\n{a_peak:.1f} mm', xy=(t_peak, a_peak), xytext=(t_peak - 0.7, a_peak + 10),
                fontsize=9.8, fontweight='bold', color='#DC2626',
                arrowprops=dict(arrowstyle='->', color='#DC2626', lw=1.5))

    # F2 Time to Peak
    ax.axvline(t_peak, color='#DC2626', linestyle=':', lw=1.5)
    ax.annotate(f'F2: tMGA = {t_peak:.2f}s', xy=(t_peak / 2, 28), fontsize=9.5, fontweight='bold', color='#DC2626', ha='center')

    # F3 Hold Region (2 seconds plateau)
    ax.axvspan(3.2, 5.2, color='#FEF3C7', alpha=0.6, label='F3: 2초 유지 구간 (Plateau)')
    ax.text(4.2, 48, 'F3: 유지 떨림 SD\n(2초간 흔들림 측정)', ha='center', va='center', fontsize=9.5, fontweight='bold', color='#D97706')

    # F4 Release Change
    ax.annotate('', xy=(7.2, 85), xytext=(5.2, 45),
                arrowprops=dict(arrowstyle='->', color='#059669', lw=2.0))
    ax.text(6.6, 60, 'F4: 능동 펴기\n변위 (Release)', fontsize=9.5, fontweight='bold', color='#059669')

    ax.set_xlabel('시간 (초, Time in seconds)', fontsize=10.5, fontweight='bold', color='#1E293B')
    ax.set_ylabel('손가락 사이 간격 (mm)', fontsize=10.5, fontweight='bold', color='#1E293B')
    ax.set_title('물체 파지 과제 4대 운동학 피처 (F1~F4) 시계열 곡선', fontsize=11.5, fontweight='bold', color='#102C57')
    ax.set_ylim(15, 115)
    ax.grid(True, linestyle='--', alpha=0.5)
    ax.legend(loc='upper left', fontsize=8.8)

    plt.tight_layout()
    fig.savefig(out_dir / 'fig_kinematics.png')
    plt.close(fig)

# -------------------------------------------------------------------------
# Figure 5: Plateau Velocity Inflection Point Detection
# -------------------------------------------------------------------------
def make_fig_plateau():
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(6.6, 4.2), sharex=True, dpi=200)
    fig.patch.set_facecolor('#FFFFFF')

    t = np.linspace(0, 7.5, 400)
    # Barehand distance r(t): opens -> closes to fist (plateau) -> reopens
    r = 75 - 45 / (1 + np.exp(-4.0 * (t - 1.2))) + 45 / (1 + np.exp(-3.5 * (t - 4.8)))
    v = np.abs(np.gradient(r, t))

    # Top: Distance r(t)
    ax1.set_facecolor('#F8FAFC')
    ax1.plot(t, r, color='#0284C7', lw=2.2, label='손바닥-손가락 거리 r(t) [mm]')
    ax1.axvspan(2.0, 4.5, color='#DCFCE7', alpha=0.6, label='유지 구간 (Hold Plateau >= 2.0s)')
    ax1.set_ylabel('거리 (mm)', fontsize=10, fontweight='bold', color='#1E293B')
    ax1.set_title('속도 변곡점 기반 무인 2초 유지 자동 검출 알고리즘', fontsize=11.5, fontweight='bold', color='#102C57')
    ax1.grid(True, linestyle='--', alpha=0.4)
    ax1.legend(loc='upper right', fontsize=8.5)

    # Bottom: Velocity |v(t)|
    ax2.set_facecolor('#F8FAFC')
    ax2.plot(t, v, color='#D97706', lw=2.0, label='움직임 속도 |v(t)| [mm/s]')
    ax2.axhline(10, color='#DC2626', linestyle='--', lw=1.5, label='평탄화 임계치 (10 mm/s)')

    # Inflection points
    ax2.plot([2.0, 4.5], [10, 10], 'ro', markersize=8)
    ax2.annotate('진입 변곡점 (t_onset)\n속도 < 10 mm/s', xy=(2.0, 10), xytext=(0.7, 30),
                 fontsize=8.8, fontweight='bold', color='#DC2626',
                 arrowprops=dict(arrowstyle='->', color='#DC2626', lw=1.2))
    ax2.annotate('이탈 변곡점 (t_offset)\n속도 > 10 mm/s', xy=(4.5, 10), xytext=(4.3, 30),
                 fontsize=8.8, fontweight='bold', color='#DC2626',
                 arrowprops=dict(arrowstyle='->', color='#DC2626', lw=1.2))

    ax2.set_xlabel('시간 (초)', fontsize=10, fontweight='bold', color='#1E293B')
    ax2.set_ylabel('속도 (mm/s)', fontsize=10, fontweight='bold', color='#1E293B')
    ax2.set_ylim(0, 50)
    ax2.grid(True, linestyle='--', alpha=0.4)
    ax2.legend(loc='upper right', fontsize=8.5)

    plt.tight_layout()
    fig.savefig(out_dir / 'fig_plateau.png')
    plt.close(fig)

# -------------------------------------------------------------------------
# Figure 6: Single PC RTX 5090 VRAM Footprint Chart
# -------------------------------------------------------------------------
def make_fig_vram():
    fig, ax = plt.subplots(figsize=(6.8, 4.0), dpi=200)
    fig.patch.set_facecolor('#FFFFFF')
    ax.set_facecolor('#F8FAFC')

    models = [
        'Qwen3-VL-8B\n(BF16 무손실)',
        'Qwen3-VL-30B-A3B\n(AWQ 4-bit MoE)',
        'LLaVA-NeXT-Video-7B\n(BF16 비디오 특화)',
        'Qwen2.5-VL-32B\n(AWQ 4-bit NYU 베이스)',
        'LLaVA-OneVision-7B\n(BF16 멀티모달 표준)'
    ]
    weights_vram = [16.0, 16.5, 14.5, 18.5, 15.0]
    tokens_vram  = [4.5, 6.0, 4.5, 6.0, 4.5]
    total_vram   = [w + t for w, t in zip(weights_vram, tokens_vram)]

    y_pos = np.arange(len(models))
    p1 = ax.barh(y_pos, weights_vram, height=0.55, color='#1E3A8A', label='모델 가중치 VRAM')
    p2 = ax.barh(y_pos, tokens_vram, left=weights_vram, height=0.55, color='#0284C7', label='14프레임 비전 + KV캐시')

    # Total text label
    for y, tot in zip(y_pos, total_vram):
        margin = 32.0 - tot
        ax.text(tot + 0.6, y, f'{tot:.1f} GB (여유 {margin:.1f}GB)', va='center', fontsize=9.2, fontweight='bold', color='#0F172A')

    # 32GB Limit line
    ax.axvline(32.0, color='#DC2626', linestyle='--', lw=2.0, label='RTX 5090 하드웨어 한계 (32GB)')
    ax.axvline(25.0, color='#059669', linestyle=':', lw=1.8, label='안전 운용선 (25GB)')

    ax.set_yticks(y_pos)
    ax.set_yticklabels(models, fontsize=9.5, fontweight='bold', color='#1E293B')
    ax.invert_yaxis()
    ax.set_xlim(0, 36)
    ax.set_xlabel('VRAM 점유량 (GB)', fontsize=10.5, fontweight='bold', color='#1E293B')
    ax.set_title('단일 PC RTX 5090 (32GB) 5개 모델 정밀 VRAM 점유율 검증', fontsize=11.5, fontweight='bold', color='#102C57')
    ax.grid(axis='x', linestyle='--', alpha=0.5)
    ax.legend(loc='lower right', fontsize=8.8)

    plt.tight_layout()
    fig.savefig(out_dir / 'fig_vram.png')
    plt.close(fig)

if __name__ == '__main__':
    print('Generating all presentation figures...')
    make_fig_primseq()
    make_fig_hallucination()
    make_fig_engineering()
    make_fig_kinematics()
    make_fig_plateau()
    make_fig_vram()
    print('Successfully generated 6 figures in scripts/figures/!')
