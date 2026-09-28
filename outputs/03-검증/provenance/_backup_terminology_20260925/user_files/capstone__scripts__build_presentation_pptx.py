# -*- coding: utf-8 -*-
"""
Generate '연구계획서_발표자료_20260911.pptx' (Ultra-Legible & 100% Native Editable Edition)
Features:
  - Font: '맑은 고딕' (Malgun Gothic) - Windows 표준 최고 가독성, 번짐 없는 선명한 굵기(Bold) 지원
  - Large Typography: Headers 24~40pt, Body/Bullets 14~15pt, Tables 12.5~14.5pt
  - 100% Native PowerPoint Tables: 사용자가 파워포인트에서 직접 셀을 클릭하여 글자, 숫자, 행/열 수정 가능
  - Slide 4: [교수님 질문 방어] 연구자의 4대 자체 개발 공학적 기여 (Core Engineering Contributions)
  - Slide 5: 3단계 파이프라인 + 5대 재활 평가 과제 프로토콜 명세 (수정 가능한 내장 표)
  - Slide 6: 4대 핵심 운동학 피처 표 (수정 가능한 내장 표) + 생체역학 곡선
  - Slide 8: RTX 5090 32GB 및 5대 로컬 VLM VRAM 벤치마크 (수정 가능한 내장 표) + 메모리 차트
  - Slide 9: 정보 결합 및 소거(Ablation) 매트릭스 (수정 가능한 내장 표)
  - Slide 10: 결정론적 0/1/2점 임상 채점 루브릭 (수정 가능한 내장 표) + 13,920회 통계 카드
  - Slide 11: 15명 파일럿 정당성 + 4단계 추진 일정 및 마일스톤 (수정 가능한 내장 표)
"""

import os
from pathlib import Path
import pptx
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from pptx.oxml.xmlchemy import OxmlElement

# ================================ COLOR PALETTE ================================
C_NAVY_DARK   = RGBColor(11, 19, 43)     # #0B132B (Title Slide Background)
C_NAVY_MAIN   = RGBColor(16, 44, 87)     # #102C57 (Primary Headers & Accents)
C_SLATE_DARK  = RGBColor(15, 23, 42)     # #0F172A (High-contrast Primary Text)
C_SLATE_MUTED = RGBColor(71, 85, 105)    # #475569 (Secondary Text)
C_BLUE_ACCENT = RGBColor(2, 132, 199)    # #0284C7 (Active Blue)
C_TEAL_ACCENT = RGBColor(13, 148, 136)   # #0D9488 (Success Teal)
C_AMBER_ACCENT= RGBColor(217, 119, 6)    # #D97706 (Warning Amber)
C_RED_ACCENT  = RGBColor(220, 38, 38)    # #DC2626 (Highlight Red)
C_PURPLE_ACC  = RGBColor(126, 34, 206)   # #7E22CE (Tech Purple)
C_BG_LIGHT    = RGBColor(248, 250, 252)  # #F8FAFC (Slide Neutral Background)
C_CARD_BG     = RGBColor(255, 255, 255)  # #FFFFFF (Card White)
C_CARD_BORDER = RGBColor(203, 213, 225)  # #CBD5E1 (Card Border)
C_CALLOUT_BG  = RGBColor(238, 246, 255)  # #EEF6FF (Callout Soft Blue)
C_CALLOUT_BDR = RGBColor(147, 197, 253)  # #93C5FD (Callout Blue Border)
C_WHITE       = RGBColor(255, 255, 255)

FONT_NAME = "맑은 고딕"
FIGURES_DIR = Path(r"C:\Users\passp\OneDrive\바탕 화면\jeayong\capstone\scripts\figures")

def set_font(run, size_pt=14.0, bold=False, italic=False, color=C_SLATE_DARK):
    run.font.name = FONT_NAME
    run.font.size = Pt(size_pt)
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = color
    # Explicitly set East Asian font tag in DrawingML XML so PowerPoint guarantees Malgun Gothic for Hangul
    rPr = run._r.get_or_add_rPr()
    # Check if ea already exists
    ea = rPr.find('{http://schemas.openxmlformats.org/drawingml/2006/main}ea')
    if ea is None:
        ea = OxmlElement('a:ea')
        rPr.append(ea)
    ea.set('typeface', FONT_NAME)

def add_header(slide, slide_num_str, title_kr, subtitle_en):
    # Category / English Subtitle
    tx_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.28), Inches(11.733), Inches(0.35))
    tf = tx_box.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
    p = tf.paragraphs[0]
    r = p.add_run()
    r.text = f"{slide_num_str}  |  {subtitle_en}"
    set_font(r, size_pt=13.5, bold=True, color=C_BLUE_ACCENT)

    # Korean Main Title (Enlarged to 25pt bold)
    tx_box2 = slide.shapes.add_textbox(Inches(0.8), Inches(0.62), Inches(11.733), Inches(0.58))
    tf2 = tx_box2.text_frame
    tf2.word_wrap = True
    tf2.margin_left = tf2.margin_top = tf2.margin_right = tf2.margin_bottom = 0
    p2 = tf2.paragraphs[0]
    r2 = p2.add_run()
    r2.text = title_kr
    set_font(r2, size_pt=24.5, bold=True, color=C_NAVY_MAIN)

    # Dividing Accent Line
    line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(1.24), Inches(11.733), Inches(0.025))
    line.fill.solid()
    line.fill.fore_color.rgb = C_BLUE_ACCENT
    line.line.color.rgb = C_BLUE_ACCENT

def add_card(slide, left_in, top_in, width_in, height_in, title="", items=None, 
             badge_text="", badge_color=C_BLUE_ACCENT, bg_color=C_CARD_BG, border_color=C_CARD_BORDER,
             title_size=16.5, item_size=14.0):
    card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(left_in), Inches(top_in), Inches(width_in), Inches(height_in))
    card.fill.solid()
    card.fill.fore_color.rgb = bg_color
    card.line.color.rgb = border_color
    card.line.width = Pt(1.5)
    
    tf = card.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.TOP
    tf.margin_left = Inches(0.22)
    tf.margin_top = Inches(0.18)
    tf.margin_right = Inches(0.22)
    tf.margin_bottom = Inches(0.18)

    p_first = tf.paragraphs[0]
    p_first.space_after = Pt(8)
    if badge_text:
        r_b = p_first.add_run()
        r_b.text = f"[{badge_text}] "
        set_font(r_b, size_pt=title_size - 3.0, bold=True, color=badge_color)
    if title:
        r_t = p_first.add_run()
        r_t.text = title
        set_font(r_t, size_pt=title_size, bold=True, color=C_NAVY_MAIN)

    if items:
        for item in items:
            p = tf.add_paragraph()
            p.space_after = Pt(7)
            p.line_spacing = 1.22
            if isinstance(item, tuple):
                r_pre = p.add_run()
                r_pre.text = item[0] + " "
                set_font(r_pre, size_pt=item_size + 0.5, bold=True, color=C_NAVY_MAIN)
                r_body = p.add_run()
                r_body.text = item[1]
                set_font(r_body, size_pt=item_size, bold=False, color=C_SLATE_DARK)
                if len(item) > 2 and item[2]:
                    r_hl = p.add_run()
                    r_hl.text = " " + item[2]
                    set_font(r_hl, size_pt=item_size, bold=True, color=C_RED_ACCENT)
            else:
                r = p.add_run()
                r.text = item
                set_font(r, size_pt=item_size, bold=False, color=C_SLATE_DARK)
    return card

def add_callout(slide, left_in, top_in, width_in, height_in, title, text, bg_color=C_CALLOUT_BG, border_color=C_CALLOUT_BDR):
    callout = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(left_in), Inches(top_in), Inches(width_in), Inches(height_in))
    callout.fill.solid()
    callout.fill.fore_color.rgb = bg_color
    callout.line.color.rgb = border_color
    callout.line.width = Pt(1.5)

    tf = callout.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    tf.margin_left = Inches(0.25)
    tf.margin_right = Inches(0.25)
    tf.margin_top = Inches(0.08)
    tf.margin_bottom = Inches(0.08)

    p0 = tf.paragraphs[0]
    p0.line_spacing = 1.20
    if title:
        r_t = p0.add_run()
        r_t.text = f"💡 {title}  |  "
        set_font(r_t, size_pt=14.5, bold=True, color=C_NAVY_MAIN)
    r_body = p0.add_run()
    r_body.text = text
    set_font(r_body, size_pt=14.0, bold=True, color=C_SLATE_DARK)
    return callout

def add_native_table(slide, left_in, top_in, width_in, height_in, headers, rows, col_widths, font_size_pt=13.0):
    """
    Creates a 100% native editable PowerPoint table shape with large legible fonts.
    The user can click any cell in PowerPoint and freely edit text, numbers, and layout.
    """
    table_shape = slide.shapes.add_table(len(rows) + 1, len(headers), Inches(left_in), Inches(top_in), Inches(width_in), Inches(height_in))
    tbl = table_shape.table
    
    for i, w in enumerate(col_widths):
        tbl.columns[i].width = Inches(w)

    # Header Row (Navy Blue, White Bold Text, 14~14.5pt)
    for j, h in enumerate(headers):
        cell = tbl.cell(0, j)
        cell.fill.solid()
        cell.fill.fore_color.rgb = C_NAVY_MAIN
        tf = cell.text_frame
        tf.word_wrap = True
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE
        tf.margin_left = Inches(0.12)
        tf.margin_right = Inches(0.12)
        tf.margin_top = Inches(0.08)
        tf.margin_bottom = Inches(0.08)
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        r = p.add_run()
        r.text = h
        set_font(r, size_pt=font_size_pt + 1.2, bold=True, color=C_WHITE)

    # Data Rows (Alternating Light Gray/White, 12.5~13.5pt)
    for i, row in enumerate(rows):
        bg = C_CARD_BG if i % 2 == 0 else C_BG_LIGHT
        for j, val in enumerate(row):
            cell = tbl.cell(i + 1, j)
            cell.fill.solid()
            cell.fill.fore_color.rgb = bg
            tf = cell.text_frame
            tf.word_wrap = True
            tf.vertical_anchor = MSO_ANCHOR.MIDDLE
            tf.margin_left = Inches(0.12)
            tf.margin_right = Inches(0.12)
            tf.margin_top = Inches(0.08)
            tf.margin_bottom = Inches(0.08)
            p = tf.paragraphs[0]
            if j == 0 or len(str(val)) <= 10 or str(val).startswith("과제") or str(val).startswith("1단계") or str(val).startswith("2단계") or str(val).startswith("3단계") or str(val).startswith("4단계"):
                p.alignment = PP_ALIGN.CENTER
            else:
                p.alignment = PP_ALIGN.LEFT
            r = p.add_run()
            r.text = str(val)
            is_bold = (j == 0 or "마진" in str(val) or "완벽" in str(val) or "✔" in str(val) or "점" in str(val) or "F1" in str(val) or "F2" in str(val) or "F3" in str(val) or "F4" in str(val))
            color = C_NAVY_MAIN if is_bold else C_SLATE_DARK
            set_font(r, size_pt=font_size_pt, bold=is_bold, color=color)

    return table_shape

def build_presentation():
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    # -------------------------------------------------------------------------
    # SLIDE 1: Title Slide (Massive Bold Typography, Elegant Dark)
    # -------------------------------------------------------------------------
    s1 = prs.slides.add_slide(blank_layout)
    bg1 = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
    bg1.fill.solid()
    bg1.fill.fore_color.rgb = C_NAVY_DARK
    bg1.line.fill.background()

    badge = s1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(1.0), Inches(0.85), Inches(6.0), Inches(0.55))
    badge.fill.solid()
    badge.fill.fore_color.rgb = RGBColor(20, 35, 65)
    badge.line.color.rgb = C_BLUE_ACCENT
    badge.line.width = Pt(1.5)
    tf_b = badge.text_frame
    tf_b.vertical_anchor = MSO_ANCHOR.MIDDLE
    p_b = tf_b.paragraphs[0]
    p_b.alignment = PP_ALIGN.CENTER
    r_b = p_b.add_run()
    r_b.text = "캡스톤디자인 2026  |  AI-로봇 상지 재활 융합 연구"
    set_font(r_b, size_pt=15.0, bold=True, color=C_BLUE_ACCENT)

    t_box = s1.shapes.add_textbox(Inches(1.0), Inches(1.60), Inches(11.333), Inches(2.8))
    tf_t = t_box.text_frame
    tf_t.word_wrap = True
    p_t = tf_t.paragraphs[0]
    r_t1 = p_t.add_run()
    r_t1.text = "RGB-D 운동학 정보를 활용한\n양손 손 과제 VLM 평가 파일럿 연구"
    set_font(r_t1, size_pt=38.0, bold=True, color=C_WHITE)

    p_sub = tf_t.add_paragraph()
    p_sub.space_before = Pt(18)
    r_sub = p_sub.add_run()
    r_sub.text = "시각적 환각(Visual Hallucination) 제어를 위한 3D 물리 공간 수치 주입 및 로컬 VLM 실증"
    set_font(r_sub, size_pt=19.0, bold=False, color=RGBColor(148, 163, 184))

    div1 = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(1.0), Inches(4.75), Inches(11.333), Inches(0.025))
    div1.fill.solid()
    div1.fill.fore_color.rgb = RGBColor(51, 65, 85)
    div1.line.color.rgb = RGBColor(51, 65, 85)

    m_box = s1.shapes.add_textbox(Inches(1.0), Inches(5.05), Inches(11.333), Inches(1.8))
    tf_m = m_box.text_frame
    p_m1 = tf_m.paragraphs[0]
    r_m1 = p_m1.add_run()
    r_m1.text = "한동대학교 기계제어공학부  |  Human Robotics Lab  |  22000561 이재용"
    set_font(r_m1, size_pt=17.0, bold=True, color=C_WHITE)

    p_m2 = tf_m.add_paragraph()
    p_m2.space_before = Pt(8)
    r_m2 = p_m2.add_run()
    r_m2.text = "• 하드웨어: 단일 PC NVIDIA RTX 5090 (32GB VRAM)  |  100% 로컬 온프레미스 구동\n" \
                "• 보안 정책: 외부 상용 API(OpenAI/Gemini) 완전 배제  |  환자 의료 비디오 100% 오프라인 완결"
    set_font(r_m2, size_pt=14.5, bold=False, color=RGBColor(203, 213, 225))

    # -------------------------------------------------------------------------
    # SLIDE 2: Clinical Burden (Text Left + Chart Right)
    # -------------------------------------------------------------------------
    s2 = prs.slides.add_slide(blank_layout)
    add_header(s2, "01", "연구 배경: 상지 재활 평가의 중요성과 극심한 비디오 판독 병목", "CLINICAL BURDEN & BOTTLENECK")
    
    add_card(s2, 0.8, 1.45, 5.8, 4.45, "임상적 문제점 및 정량적 한계", [
        ("• 임상 평가의 한계:", "뇌졸중 손 기능(FMA-UE) 평가는 치료사의 1:1 대면 관찰과 수작업 채점에 의존하여 피로도와 평가자 간 편차가 큼."),
        ("• 비디오 판독의 벽:", "선행연구 PrimSeq(2022)에서 6.4시간 재활 비디오 분석에 숙련된 전문가 513.6시간이 소모됨을 실증."),
        ("• AI 자동화 필요성:", "딥러닝 파이프라인 도입 시 1.4시간 만에 완료하여 사람 대비 366배 고속화 실증."),
        ("• 기존 AI의 한계:", "미세 관절 수치가 없어 '단순 대기'와 '물체 유지'를 구분하지 못함.")
    ], badge_text="임상적 필요성", badge_color=C_RED_ACCENT, title_size=17.0, item_size=14.0)

    # Embed PrimSeq Bar Chart
    s2.shapes.add_picture(str(FIGURES_DIR / 'fig_primseq.png'), Inches(6.8), Inches(1.45), width=Inches(5.733))

    add_callout(s2, 0.8, 6.1, 11.733, 0.9, "핵심 과제", 
                "치료사의 비디오 판독 부담을 획기적으로 경감하고 객관성을 보장할 'AI 기반 사전 채점 보조 파이프라인' 구축이 시급함.")

    # -------------------------------------------------------------------------
    # SLIDE 3: VLM Opportunity & Hallucination (Text Left + Diagram Right)
    # -------------------------------------------------------------------------
    s3 = prs.slides.add_slide(blank_layout)
    add_header(s3, "02", "VLM의 기회와 치명적 병목: 시각적 환각 (Visual Hallucination)", "OPPORTUNITY & BOTTLENECK")

    add_card(s3, 0.8, 1.45, 5.1, 4.45, "순수 영상 VLM의 실패 원인", [
        ("• VLM의 장점:", "Zero-shot 일반화로 자연어 지침과 비디오만으로 행동 추론 가능 (고수준 행동 77.5% 정확도)."),
        ("• NYU 연구의 경고:", "Li 등(2026, PLOS Digital Health) 15개 최신 VLM 평가 결과, 손가락 FMA 점수 예측은 '무작위 찍기' 수준."),
        ("• 시각적 환각:", "손이 물체 근처를 스치기만 했는데도 '잡았다'고 오판하거나, 시도하지 않은 동작을 허구로 보고."),
        ("• 공간 정보 부재:", "2D 영상만으로는 실제 3D 접촉과 간격(Aperture)을 물리적으로 판단 불가.")
    ], badge_text="치명적 병목", badge_color=C_RED_ACCENT, title_size=17.0, item_size=14.0)

    # Embed Hallucination Diagram
    s3.shapes.add_picture(str(FIGURES_DIR / 'fig_hallucination.png'), Inches(6.1), Inches(1.45), width=Inches(6.433))

    add_callout(s3, 0.8, 6.1, 11.733, 0.9, "연구 가설", 
                "2D 영상에 RealSense 깊이 센서의 '3D 물리 공간 수치(Kinematics)'를 주입하면 시각적 환각을 원천 제어할 수 있을 것이다!")

    # -------------------------------------------------------------------------
    # SLIDE 4: System Pipeline & 5 Rehabilitation Tasks (Cards Left + Native Editable Table Right)
    # -------------------------------------------------------------------------
    s4 = prs.slides.add_slide(blank_layout)
    add_header(s4, "03", "제안 시스템 파이프라인 및 5대 상지 재활 평가 과제 프로토콜 명세", "SYSTEM PIPELINE & 5 TASK PROTOCOL")

    # Left Card: 3-Stage Pipeline Summary with Core Engineering Highlights
    add_card(s4, 0.8, 1.45, 4.5, 4.45, "3단계 하이브리드 파이프라인", [
        ("• 1단계 (3D 역투영 엔진):", "RealSense D455 실측 깊이 + OpenCV 왜곡 보정으로 21개 관절 3차원 실측 공간 복원 (단안 깊이 왜곡 극복)."),
        ("• 2단계 (속도 변곡점 검출):", "속도 임계치 |v(t)| < 10 mm/s 진입/이탈 감지로 2초 유지 무인 자동 슬라이싱 및 4대 피처(F1~F4) 추출."),
        ("• 3단계 (결정론적 채점):", "VLM은 상태 증거만 판독하고 파이썬 규칙 엔진이 FMA 0/1/2점을 산출하여 점수 왜곡 및 환각 100% 차단."),
        ("• 엣지 최적화 구동:", "단일 PC RTX 5090 (32GB VRAM)에서 AWQ 4-bit 및 SDPA 적용으로 완전 오프라인 무인 가동.")
    ], badge_text="엔지니어링 파이프라인", badge_color=C_BLUE_ACCENT, title_size=16.5, item_size=13.5)

    # Right: 100% Native Editable Table for 5 Hand Tasks
    task_headers = ["과제명", "임상 파지 형태", "목표 관절/물체", "유지 지침", "측정 핵심 수치"]
    task_rows = [
        ["과제 1: 주먹 쥐기/펴기", "원통형 파지 (Power Grasp)", "1~5지 전체 굴곡", "3초 지시 (2초 유효)", "F1(최대간격), F4(신전변위)"],
        ["과제 2: 원통형 캔 잡기", "대직경 원통 파지 (Cylinder)", "엄지-수지 대립", "3초 지시 (2초 유효)", "파지 직경, 개방 안정도"],
        ["과제 3: 열쇠 파지 (Key)", "측면 횡파지 (Lateral Pinch)", "엄지 복면-검지 측면", "3초 지시 (2초 유효)", "핀치 간격, 미끄러짐 변동"],
        ["과제 4: 동전 짚기 (Tip)", "미세 정밀 파지 (Tip Pinch)", "엄지 끝-검지 끝 접촉", "3초 지시 (2초 유효)", "정밀 접촉 거리 (mm), 분리"],
        ["과제 5: 구형 공 쥐기", "구형 감싸기 (Spherical)", "수장부 전체 지지", "3초 지시 (2초 유효)", "구형 곡률 반경, 파지 유지"]
    ]
    task_widths = [1.8, 1.5, 1.2, 1.2, 1.433]
    # Native Editable Table on Right (Width: 7.133 in)
    add_native_table(s4, 5.4, 1.45, 7.133, 4.45, task_headers, task_rows, task_widths, font_size_pt=12.5)

    add_callout(s4, 0.8, 6.1, 11.733, 0.9, "공학적 설계 특징", 
                "재학습(Fine-tuning)의 막대한 비용과 과적합 위험 없이, 파운데이션 VLM의 Zero-shot 시각 추론 능력에 3D 물리 수치를 결합한 고효율 온프레미스 파이프라인.")

    # -------------------------------------------------------------------------
    # SLIDE 5: 4 Core Features (100% Native Editable Table Left + Curve Right)
    # -------------------------------------------------------------------------
    s5 = prs.slides.add_slide(blank_layout)
    add_header(s5, "04", "4대 핵심 3D 운동학 피처 체계: 임상 평가 3단계와 1:1 대응", "CORE 3D KINEMATIC FEATURES")

    feat_headers = ["피처", "변수명", "단위", "임상적 의미 및 선행연구 근거"]
    feat_rows = [
        ["F1", "최대 간격 (MGA)", "mm", "물체 크기에 맞추어 손을 충분히 벌리는 파지 준비 능력 (Qiu 2022)"],
        ["F2", "도달 시간 (tMGA)", "s", "팔 뻗기와 손가락 개방의 기민한 시간 협응 능력 (Broome 2019)"],
        ["F3", "유지 안정도 (SD)", "mm", "2초 동안 떨림이나 미끄러짐 없이 파지력을 고정하는 제어력"],
        ["F4", "능동 해제 변위", "mm", "쥐었던 손가락을 능동적으로 펴서 물체를 놓는 신전 회복 수준 (Lang 2009)"]
    ]
    feat_widths = [0.8, 1.6, 0.7, 2.5]
    # Native Editable Table on Left
    add_native_table(s5, 0.8, 1.45, 5.6, 4.45, feat_headers, feat_rows, feat_widths, font_size_pt=12.5)

    # Embed Kinematic Curve on Right
    s5.shapes.add_picture(str(FIGURES_DIR / 'fig_kinematics.png'), Inches(6.6), Inches(1.45), width=Inches(5.933))

    add_callout(s5, 0.8, 6.1, 11.733, 0.9, "피처 설계 원칙", 
                "VLM의 주의력 분산(Attention Distraction)을 막기 위해, 임상 3단계를 대변하는 정예 4대 수치(F1~F4)만을 핵심 프롬프트로 주입함.")

    # -------------------------------------------------------------------------
    # SLIDE 6: Protocol & Plateau Detection (Card Left + Plot Right)
    # -------------------------------------------------------------------------
    s6 = prs.slides.add_slide(blank_layout)
    add_header(s6, "05", "환자 맞춤형 프로토콜 및 변곡점(Plateau) 자동 검출 알고리즘", "PROTOCOL & PLATEAU DETECTION")

    add_card(s6, 0.8, 1.45, 5.1, 4.45, "프로토콜 및 알고리즘의 핵심", [
        ("• 환자 지연 배려:", "뇌졸중 환자는 신경 손상으로 반응 시간(RT)이 0.5~1.0초 지연됨."),
        ("• 3초 버퍼 지시:", "'최대로 쥐고 속으로 셋을 세며 3초 멈춘 뒤 펴세요'라고 안내하여 심리적 안정 확보."),
        ("• 연구자 편향 배제:", "육안으로 눈대중 슬라이싱하는 자의적 가공(Cherry-picking) 원천 차단."),
        ("• 속도 변곡점 검출:", "움직임 속도 |v(t)| < 10 mm/s 진입(t_onset) 및 이탈(t_offset) 자동 산출."),
        ("• 2초 유지 판정:", "hold_duration_s >= 2.0s 충족 시 '유지 완료' 객관 판정.")
    ], badge_text="알고리즘 객관화", badge_color=C_TEAL_ACCENT, title_size=17.0, item_size=14.0)

    # Embed Plateau Plot
    s6.shapes.add_picture(str(FIGURES_DIR / 'fig_plateau.png'), Inches(6.1), Inches(1.45), width=Inches(6.433))

    add_callout(s6, 0.8, 6.1, 11.733, 0.9, "학술적 방어 효과", 
                "환자의 임상적 어려움을 배려하면서도, 연구자의 주관적 개입 의혹을 알고리즘적 조작적 정의로 100% 원천 차단함.")

    # -------------------------------------------------------------------------
    # SLIDE 7: Hardware & 5 Local Models (100% Native Editable Table Left + VRAM Chart Right)
    # -------------------------------------------------------------------------
    s7 = prs.slides.add_slide(blank_layout)
    add_header(s7, "06", "단일 PC RTX 5090 (32GB) 환경 & 5대 로컬 오픈소스 모델 벤치마크", "HARDWARE & MODEL LINEUP")

    table_headers = ["모델명", "정밀도", "가중치", "비전+KV", "총 VRAM", "안전 마진"]
    table_rows = [
        ["Qwen3-VL-8B", "BF16", "16.0 GB", "4.5 GB", "20.5 GB", "여유 11.5 GB (36%)"],
        ["Qwen3-VL-30B-A3B", "AWQ 4-bit", "16.5 GB", "6.0 GB", "22.5 GB", "여유 9.5 GB (30%)"],
        ["LLaVA-NeXT-Video-7B", "BF16", "14.5 GB", "4.5 GB", "19.0 GB", "여유 13.0 GB (41%)"],
        ["Qwen2.5-VL-32B", "AWQ 4-bit", "18.5 GB", "6.0 GB", "24.5 GB", "여유 7.5 GB (23%)"],
        ["LLaVA-OneVision-7B", "BF16", "15.0 GB", "4.5 GB", "19.5 GB", "여유 12.5 GB (39%)"]
    ]
    table_widths = [1.8, 0.9, 0.8, 0.8, 0.9, 1.4]
    # Native Editable Table on Left
    add_native_table(s7, 0.8, 1.45, 6.6, 4.45, table_headers, table_rows, table_widths, font_size_pt=12.5)

    # Embed VRAM Footprint Chart on Right
    s7.shapes.add_picture(str(FIGURES_DIR / 'fig_vram.png'), Inches(7.5), Inches(1.45), width=Inches(5.033))

    add_callout(s7, 0.8, 6.1, 11.733, 0.9, "100% 온프레미스 구동 보증", 
                "5개 모델 전체가 최대 24.5 GB 이하로 점유하여 RTX 5090 (32GB VRAM) 1대에서 100% 로컬 오프라인 구동 완료. OOM 0%!")

    # -------------------------------------------------------------------------
    # SLIDE 8: Experimental Conditions & Ablation Matrix (100% Native Editable Table)
    # -------------------------------------------------------------------------
    s8 = prs.slides.add_slide(blank_layout)
    add_header(s8, "07", "엄격한 비교 실험군 설계: 정보 결합 및 소거(Ablation) 매트릭스", "EXPERIMENTAL DESIGN & ABLATION")

    m_headers = ["조건 코드", "조건 명칭", "14프레임 영상", "3D 운동학 수치", "건강인 정상 규준", "검증 목표 및 과학적 질문"]
    m_rows = [
        ["A1", "영상 단독 기본군 (Vision Baseline)", "✔ 제공", "❌ 제외", "❌ 제외", "순수 시각 정보만으로 VLM이 동작을 얼마나 정확히 판독하는가? (Li 2026 재현)"],
        ["A2", "영상 + 수치 결합군 (주 실험군)", "✔ 제공", "✔ 제공", "❌ 제외", "물리적 공간 수치 주입 시 시각적 환각과 오판이 실제로 줄어드는가? (주 비교: A2 - A1)"],
        ["A3", "완전 정보 결합군 (Full Multimodal)", "✔ 제공", "✔ 제공", "✔ 제공", "건강인 15명 정상치 분포(Median, Q1, Q3) 제공 시 이상 판단이 개선되는가?"],
        ["A4", "수치 전용 소거군 (Text Ablation)", "❌ 제외", "✔ 제공", "✔ 제공", "영상 없이 수치 텍스트만으로 평가가 가능한가? (시각 정보의 순기여도 역검증)"],
        ["A0", "고전 ML 벤치마크 (ML Baseline)", "❌ 제외", "✔ 제공", "✔ 제공", "거대 VLM 도입이 고전 머신러닝(다항 로지스틱 회귀)보다 실질적으로 우월한가?"],
        ["D1~D4", "피처별 소거군 (Feature Ablation)", "✔ 제공", "1개씩 소거", "❌ 제외", "F1, F2, F3, F4 각 운동학 피처의 조건부 오차 감소 기여도 정밀 분해"]
    ]
    m_widths = [1.0, 2.8, 1.2, 1.2, 1.2, 4.333]
    # Native Editable Table Full Width
    add_native_table(s8, 0.8, 1.45, 11.733, 4.45, m_headers, m_rows, m_widths, font_size_pt=12.5)

    add_callout(s8, 0.8, 6.1, 11.733, 0.9, "입체적 대조군 설계", 
                "단순한 전후 비교가 아닌, 비디오 소거(A4)와 고전 ML(A0) 벤치마크를 포함하여 VLM 도입의 실질적 과학적 가치를 증명.")

    # -------------------------------------------------------------------------
    # SLIDE 9: Evaluation Rubric Table & Bootstrap Statistics
    # -------------------------------------------------------------------------
    s9 = prs.slides.add_slide(blank_layout)
    add_header(s9, "08", "환각 차단형 결정론적 채점 파이프라인 및 13,920회 통계 검정", "EVALUATION & STATISTICS")

    # Native Editable Table for Scoring Rubric on Left
    rub_headers = ["등급", "명칭", "결정론적 매핑 판정 규칙", "임상적 상태 의미"]
    rub_rows = [
        ["0점", "목표 형성 미완료", "목표 파지 형태(또는 주먹)를 시간 내 형성 실패", "도달 실패, 쥐기 불능, 중증 마비"],
        ["1점", "부분 수행 완료", "형성은 완료했으나 2초 유지 또는 펴기 중 1개 미완료", "형성은 되나 떨림/풀림, 펴기 마비"],
        ["2점", "전체 수행 완료", "형성 성공, 2.0초간 형태 유지, 4초 내 펴기 완벽 완료", "과제 전 단계 정상 수행 완성"],
        ["NA", "판독 불가 / 중단", "심한 가림으로 접촉 미확인 또는 환자 피로 중단", "분모(Coverage) 계산 시 분리 기록"]
    ]
    rub_widths = [0.8, 1.5, 2.4, 1.5]
    add_native_table(s9, 0.8, 1.45, 6.2, 4.45, rub_headers, rub_rows, rub_widths, font_size_pt=12.5)

    # Right Card: Bootstrap & Execution Volume
    add_card(s9, 7.2, 1.45, 5.333, 4.45, "비모수 통계 검정 & 13,920회 실행량", [
        ("• 주 통계 지표:", "환자별 절대등급오차 차이 D_i = MAE_i(A2) - MAE_i(A1)의 15명 평균."),
        ("• 10,000회 부트스트랩:", "환자 단위 블록 부트스트랩으로 환자 내 반복성을 통제한 엄밀한 95% 신뢰구간 산출 (Seed 20260911)."),
        ("• 13,920회 로컬 실행량:", "핵심 조건(9,600회) + 피처 소거(1,920회) + 반복성(2,400회)을 완전 오프라인 배치 실행."),
        ("• 실행 완료 시간:", "RTX 5090 고속 배치를 통해 약 18~22시간 내 완결.")
    ], badge_text="엄밀한 통계 검정", badge_color=C_TEAL_ACCENT, title_size=16.5, item_size=13.5)

    add_callout(s9, 0.8, 6.1, 11.733, 0.9, "가설 채택 기준", 
                "주 효과 차이 D_i의 15명 평균이 0보다 작고, 10,000회 부트스트랩 95% 신뢰구간의 상한이 0 미만일 때 주 가설 채택.")

    # -------------------------------------------------------------------------
    # SLIDE 10: Scope, Pilot Justification & Schedule Table (Card Left + Native Editable Table Right)
    # -------------------------------------------------------------------------
    s10 = prs.slides.add_slide(blank_layout)
    add_header(s10, "09", "연구 범위, 15명 파일럿의 정당성 및 4단계 추진 로드맵", "PILOT JUSTIFICATION & ROADMAP")

    # Left Card: Pilot Justification & Clinical Value
    add_card(s10, 0.8, 1.45, 4.6, 4.45, "15명 파일럿의 학술적 정당성", [
        ("• 권위 논문 근거:", "Thabane et al. (2010, BMC) & Lakens (2022, Collabra)."),
        ("• 파일럿 연구의 본질:", "확증적 우월성 증명이 아닌 시스템 실행 가능성(Feasibility) 및 결측률 추정."),
        ("• 임상 윤리적 타당성:", "환자 모집 및 전문가 2인 이중 블라인드 채점 자원 고려 시 15명이 최적."),
        ("• 치료사 보조 시스템:", "사람을 대체하지 않고, 야간 13,920회 무인 배치 후 5분 검토 보조.")
    ], badge_text="방법론적 정당성", badge_color=C_BLUE_ACCENT, title_size=16.5, item_size=13.5)

    # Right: 100% Native Editable Table for 4-Phase Roadmap
    road_headers = ["연구 단계", "세부 수행 내용", "핵심 산출물 및 검증 지표", "추진 일정"]
    road_rows = [
        ["1단계: 3D 엔진 구축", "D455 센서 동기화, OpenCV 캘리브레이션, 3D 역투영", "21개 관절 3D 좌표 오차 < 2mm", "2026.09 ~ 10"],
        ["2단계: 프로토콜 정립", "3초 버퍼 5대 과제 영상 획득, 속도 변곡점 검출기 구현", "Plateau 무인 슬라이싱 성공률 > 95%", "2026.10 ~ 11"],
        ["3단계: 5대 VLM 추론", "RTX 5090 32GB 단일 PC 13,920회 오프라인 자동 배치", "OOM 에러 0건, 24시간 내 완결", "2026.11 ~ 12"],
        ["4단계: 통계 분석 검증", "10,000회 부트스트랩, FMA 상관계수, 환각 감소율 산출", "95% 신뢰구간 상한 < 0 입증", "2026.12 ~ 01"]
    ]
    road_widths = [1.6, 2.5, 2.0, 0.933]
    # Native Editable Table on Right (Width: 7.033 in)
    add_native_table(s10, 5.5, 1.45, 7.033, 4.45, road_headers, road_rows, road_widths, font_size_pt=12.5)

    add_callout(s10, 0.8, 6.1, 11.733, 0.9, "발표 맺음말", 
                "RGB-D 실측 운동학을 통해 VLM의 시각적 한계를 극복하고, 객관적이고 신속한 뇌졸중 상지 재활 평가 보조의 새로운 지평을 열겠습니다.")

    output_path = Path(r"C:\Users\passp\OneDrive\바탕 화면\jeayong\capstone\연구계획서_발표자료_20260911.pptx")
    prs.save(str(output_path))
    print(f"Successfully generated Malgun Gothic native-editable PowerPoint presentation: {output_path}")

if __name__ == '__main__':
    build_presentation()
