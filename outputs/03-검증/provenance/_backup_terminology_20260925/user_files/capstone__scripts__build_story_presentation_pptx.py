# -*- coding: utf-8 -*-
"""
Generate '연구계획서_발표자료_20260911_최종수정본.pptx' & Update '연구계획서_발표자료_20260911.pptx'
사용자 확정 스토리라인 및 고가독성/수정가능 네이티브 차트·표 전면 적용 버전:
  1. 연구의 필요성: 영상 기반 사람 채점 시 513.6시간 소요, 재활 지속 확인 필요하나 만성적 인력·시간 부족 (수정 가능한 막대 차트)
  2. 기존 연구의 시도와 한계: 딥러닝(시간 단축, 정확도 보통, 미세관절 한계) vs VLM(ADL 양호, FMA/미세동작 35% 급락, 시각적 환각) (수정 가능한 비교 차트)
  3. 해결 방안: 영상 기반 VLM 성능 향상을 위해 3D 운동학 수치(Kinematics) 프롬프트 결합
  4. 생체역학 근거: Qiu(2022) MGA/tMGA FMA 연관성, Lang(2005, 2009) 신전 변위, Amprimo(2024) 깊이 결합 손 추적
  5. 실험 조건 체계: A1(순수영상), A2(영상+운동학 [Primary]), A3(영상+수치+정상군), A4(수치전용), A0(순서형 로지스틱) (수정 가능한 매트릭스 표)
  6. 100% 로컬 인프라: RTX 5090 (32GB) 5종 VLM 벤치마크 (수정 가능한 VRAM 차트 및 표)
  7. 환각 방지 채점: 0/1/2점 결정론적 루브릭 및 11,580회 실행 (수정 가능한 루브릭 표)
  8. 결론 및 기대효과: 임상 비디오 판독 90% 단축 보조 시스템

특징:
  - 100% 파워포인트 네이티브 차트 및 표 (더블 클릭 시 엑셀/셀에서 즉시 데이터 및 글자 수정 가능)
  - 글자 크기 극대화 (헤더 24~26pt, 본문/불릿 15.5~18pt, 표 13~14pt, 콜아웃 15~16pt)
  - 간결하고 임팩트 있는 카드 레이아웃 (텍스트 벽 제거)
"""

import os
from pathlib import Path
import pptx
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION, XL_DATA_LABEL_POSITION
from pptx.chart.data import CategoryChartData
from pptx.oxml.xmlchemy import OxmlElement

# ================================ COLOR PALETTE ================================
C_NAVY_DARK   = RGBColor(11, 19, 43)     # #0B132B (Title Slide Background)
C_NAVY_MAIN   = RGBColor(16, 44, 87)     # #102C57 (Primary Headers & Main Accents)
C_SLATE_DARK  = RGBColor(15, 23, 42)     # #0F172A (High-contrast Body Text)
C_SLATE_MUTED = RGBColor(71, 85, 105)    # #475569 (Secondary Text)
C_BLUE_ACCENT = RGBColor(2, 132, 199)    # #0284C7 (Active Blue)
C_BLUE_LIGHT  = RGBColor(224, 242, 254)  # #E0F2FE (Soft Blue)
C_TEAL_ACCENT = RGBColor(13, 148, 136)   # #0D9488 (Success Teal)
C_AMBER_ACCENT= RGBColor(217, 119, 6)    # #D97706 (Warning Amber)
C_RED_ACCENT  = RGBColor(220, 38, 38)    # #DC2626 (Highlight Red)
C_BG_LIGHT    = RGBColor(248, 250, 252)  # #F8FAFC (Slide Neutral Background)
C_CARD_BG     = RGBColor(255, 255, 255)  # #FFFFFF (Card White)
C_CARD_BORDER = RGBColor(203, 213, 225)  # #CBD5E1 (Card Border)
C_CALLOUT_BG  = RGBColor(238, 246, 255)  # #EEF6FF (Callout Soft Blue)
C_CALLOUT_BDR = RGBColor(147, 197, 253)  # #93C5FD (Callout Blue Border)
C_WHITE       = RGBColor(255, 255, 255)

FONT_NAME = "맑은 고딕"

def set_font(run, size_pt=15.0, bold=False, italic=False, color=C_SLATE_DARK):
    run.font.name = FONT_NAME
    run.font.size = Pt(size_pt)
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = color
    # Explicitly set East Asian font tag in DrawingML XML so PowerPoint guarantees Malgun Gothic
    rPr = run._r.get_or_add_rPr()
    ea = rPr.find('{http://schemas.openxmlformats.org/drawingml/2006/main}ea')
    if ea is None:
        ea = OxmlElement('a:ea')
        rPr.append(ea)
    ea.set('typeface', FONT_NAME)

def add_header(slide, slide_num_str, title_kr, subtitle_en):
    # Category / English Subtitle (14pt Bold Blue)
    tx_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.26), Inches(11.733), Inches(0.35))
    tf = tx_box.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
    p = tf.paragraphs[0]
    r = p.add_run()
    r.text = f"{slide_num_str}  |  {subtitle_en}"
    set_font(r, size_pt=14.0, bold=True, color=C_BLUE_ACCENT)

    # Korean Main Title (Enlarged to 25.5pt Bold Navy)
    tx_box2 = slide.shapes.add_textbox(Inches(0.8), Inches(0.60), Inches(11.733), Inches(0.58))
    tf2 = tx_box2.text_frame
    tf2.word_wrap = True
    tf2.margin_left = tf2.margin_top = tf2.margin_right = tf2.margin_bottom = 0
    p2 = tf2.paragraphs[0]
    r2 = p2.add_run()
    r2.text = title_kr
    set_font(r2, size_pt=25.0, bold=True, color=C_NAVY_MAIN)

    # Dividing Accent Line
    line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(1.22), Inches(11.733), Inches(0.025))
    line.fill.solid()
    line.fill.fore_color.rgb = C_BLUE_ACCENT
    line.line.color.rgb = C_BLUE_ACCENT

def add_card(slide, left_in, top_in, width_in, height_in, title="", items=None, 
             badge_text="", badge_color=C_BLUE_ACCENT, bg_color=C_CARD_BG, border_color=C_CARD_BORDER,
             title_size=18.0, item_size=15.5):
    card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(left_in), Inches(top_in), Inches(width_in), Inches(height_in))
    card.fill.solid()
    card.fill.fore_color.rgb = bg_color
    card.line.color.rgb = border_color
    card.line.width = Pt(1.5)
    
    tf = card.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.TOP
    tf.margin_left = Inches(0.24)
    tf.margin_top = Inches(0.20)
    tf.margin_right = Inches(0.24)
    tf.margin_bottom = Inches(0.20)

    p_first = tf.paragraphs[0]
    p_first.space_after = Pt(8)
    if badge_text:
        r_b = p_first.add_run()
        r_b.text = f"[{badge_text}] "
        set_font(r_b, size_pt=title_size - 2.5, bold=True, color=badge_color)
    if title:
        r_t = p_first.add_run()
        r_t.text = title
        set_font(r_t, size_pt=title_size, bold=True, color=C_NAVY_MAIN)

    if items:
        for item in items:
            p = tf.add_paragraph()
            p.space_after = Pt(8)
            p.line_spacing = 1.25
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
        set_font(r_t, size_pt=15.0, bold=True, color=C_NAVY_MAIN)
    r_body = p0.add_run()
    r_body.text = text
    set_font(r_body, size_pt=14.5, bold=True, color=C_SLATE_DARK)
    return callout

def add_native_table(slide, left_in, top_in, width_in, height_in, headers, rows, col_widths, font_size_pt=13.5):
    """
    Creates a 100% native editable PowerPoint table.
    The user can click any cell in PowerPoint and freely edit text, numbers, and layout.
    """
    table_shape = slide.shapes.add_table(len(rows) + 1, len(headers), Inches(left_in), Inches(top_in), Inches(width_in), Inches(height_in))
    tbl = table_shape.table
    
    for i, w in enumerate(col_widths):
        tbl.columns[i].width = Inches(w)

    # Header Row (Navy Blue, White Bold Text, 14.5pt)
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
        set_font(r, size_pt=font_size_pt + 1.0, bold=True, color=C_WHITE)

    # Data Rows (Alternating Light Gray/White, 13~14pt)
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
            if j == 0 or len(str(val)) <= 8 or str(val).startswith("과제") or str(val).startswith("F") or str(val).startswith("A"):
                p.alignment = PP_ALIGN.CENTER
            else:
                p.alignment = PP_ALIGN.LEFT
            r = p.add_run()
            r.text = str(val)
            is_bold = (j == 0 or "★" in str(val) or "✔" in str(val) or "Primary" in str(val) or "점" in str(val) or "F1" in str(val) or "F2" in str(val) or "F3" in str(val) or "F4" in str(val))
            color = C_NAVY_MAIN if is_bold else C_SLATE_DARK
            set_font(r, size_pt=font_size_pt, bold=is_bold, color=color)

    return table_shape

def build_presentation():
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    # =========================================================================
    # SLIDE 1: Title Slide (Massive Bold Typography, Elegant Dark Navy)
    # =========================================================================
    s1 = prs.slides.add_slide(blank_layout)
    bg1 = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
    bg1.fill.solid()
    bg1.fill.fore_color.rgb = C_NAVY_DARK
    bg1.line.fill.background()

    # Top Badge
    badge = s1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(1.0), Inches(0.85), Inches(6.5), Inches(0.55))
    badge.fill.solid()
    badge.fill.fore_color.rgb = RGBColor(20, 35, 65)
    badge.line.color.rgb = C_BLUE_ACCENT
    badge.line.width = Pt(1.5)
    tf_b = badge.text_frame
    tf_b.vertical_anchor = MSO_ANCHOR.MIDDLE
    p_b = tf_b.paragraphs[0]
    p_b.alignment = PP_ALIGN.CENTER
    r_b = p_b.add_run()
    r_b.text = "캡스톤디자인 2026  |  AI-로봇 상지 재활 융합 연구 계획"
    set_font(r_b, size_pt=15.5, bold=True, color=C_BLUE_ACCENT)

    # Main Title
    t_box = s1.shapes.add_textbox(Inches(1.0), Inches(1.65), Inches(11.333), Inches(2.8))
    tf_t = t_box.text_frame
    tf_t.word_wrap = True
    p_t = tf_t.paragraphs[0]
    r_t1 = p_t.add_run()
    r_t1.text = "RGB-D 운동학 정보를 활용한\n양손 손 과제 VLM 평가 파일럿 연구"
    set_font(r_t1, size_pt=38.0, bold=True, color=C_WHITE)

    p_sub = tf_t.add_paragraph()
    p_sub.space_before = Pt(16)
    r_sub = p_sub.add_run()
    r_sub.text = "3D 물리 공간 수치(Kinematics) 주입을 통한 영상 기반 VLM 재활 평가 성능 개선"
    set_font(r_sub, size_pt=18.0, bold=False, color=RGBColor(186, 215, 248))

    # Author Box
    a_box = s1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(1.0), Inches(4.9), Inches(11.333), Inches(1.75))
    a_box.fill.solid()
    a_box.fill.fore_color.rgb = RGBColor(18, 30, 58)
    a_box.line.color.rgb = RGBColor(40, 65, 110)
    a_box.line.width = Pt(1.2)
    tf_a = a_box.text_frame
    tf_a.vertical_anchor = MSO_ANCHOR.MIDDLE
    tf_a.margin_left = Inches(0.35)

    p_a1 = tf_a.paragraphs[0]
    r_a1 = p_a1.add_run()
    r_a1.text = "연구자: 한동대학교 기계제어공학 · Human Robotics Lab  |  22000561 이재용\n"
    set_font(r_a1, size_pt=16.0, bold=True, color=C_WHITE)

    p_a2 = tf_a.add_paragraph()
    p_a2.space_before = Pt(6)
    r_a2 = p_a2.add_run()
    r_a2.text = "인프라: 단일 PC NVIDIA GeForce RTX 5090 (32GB VRAM) / 100% 로컬 온프레미스 구동\n센서 환경: Intel RealSense D455 Stereo RGB-D (30 fps Color-Depth Hardware Aligned)"
    set_font(r_a2, size_pt=14.0, bold=False, color=RGBColor(160, 180, 205))

    # =========================================================================
    # SLIDE 2: 연구의 필요성 - 임상 평가의 만성적 한계 (Story Step 1)
    # =========================================================================
    s2 = prs.slides.add_slide(blank_layout)
    add_header(s2, "01", "연구의 필요성: 영상 기반 임상 채점의 극심한 시간 소요와 인력 부족", "CLINICAL BOTTLENECK & TIME BURDEN")

    # Left: Core Cards (Enlarged Text, 17~18pt)
    add_card(s2, 0.8, 1.45, 5.3, 4.45, "임상 재활 현장의 만성적 병목", [
        ("🔴 지속적 확인의 필수성:", "뇌졸중 환자의 신경학적 회복 수준을 추적하기 위해 재활 과정 중 지속적인 상시 평가가 필수적임."),
        ("🔴 임상 인력의 극심한 부족:", "숙련된 물리·작업치료사가 모든 환자의 비디오를 전수 대면 관찰·채점하기에는 물리적 시간과 인력이 절대적으로 부족함."),
        ("🔴 주관적 편차 및 업무 과중:", "평가자 간 주관적 오차 발생 및 극심한 피로도로 인해 치료 본연의 시간에 집중하지 못하는 악순환 발생."),
        ("🔴 자동화 보조의 절실함:", "비디오 기반으로 상태를 신속·정확히 사전 채점해주는 AI 보조 파이프라인 도입이 시급함.")
    ], badge_text="임상 현실", badge_color=C_RED_ACCENT, title_size=18.5, item_size=15.5)

    # Right: Native Editable Chart (소요 시간 비교: 513.6시간 vs 1.4시간)
    # Native Clustered Column Chart that user can directly edit in PowerPoint
    chart_data = CategoryChartData()
    chart_data.categories = ['사람 숙련 평가자 (수작업)', 'AI 자동화 파이프라인']
    chart_data.add_series('비디오 주석 소요 시간 (시간)', (513.6, 1.4))

    chart_frame = s2.shapes.add_chart(
        XL_CHART_TYPE.COLUMN_CLUSTERED,
        Inches(6.4), Inches(1.45), Inches(6.133), Inches(4.45),
        chart_data
    )
    chart = chart_frame.chart
    chart.has_legend = False
    chart.has_title = True
    chart.chart_title.text_frame.text = "비디오 주석 소요 시간 비교 (PrimSeq 선행연구 실측치)"
    set_font(chart.chart_title.text_frame.paragraphs[0].runs[0], size_pt=14.0, bold=True, color=C_NAVY_MAIN)
    
    # Customize series bar colors & data labels
    series = chart.series[0]
    series.format.fill.solid()
    series.format.fill.fore_color.rgb = C_NAVY_MAIN
    plots = chart.plots[0]
    plots.has_data_labels = True
    data_labels = plots.data_labels
    data_labels.font.name = FONT_NAME
    data_labels.font.size = Pt(14.0)
    data_labels.font.bold = True
    data_labels.font.color.rgb = C_SLATE_DARK

    add_callout(s2, 0.8, 6.1, 11.733, 0.9, "핵심 임상 문제 요약", 
                "환자 1명의 재활 비디오 분석에 사람 치료사 513시간이 소요됩니다. 재활 현장의 인력·시간 부족을 해결할 자동화 파이프라인이 필수적입니다.")

    # =========================================================================
    # SLIDE 3: 기존 연구들의 시도와 엇갈린 결과: 딥러닝 vs VLM (Story Step 2)
    # =========================================================================
    s3 = prs.slides.add_slide(blank_layout)
    add_header(s3, "02", "기존 연구의 시도와 한계: 딥러닝의 가능성과 VLM의 성능 급락", "PRIOR ATTEMPTS & LIMITATIONS")

    # Left: Native Editable Chart (과제 난이도별 정확도: 딥러닝 vs VLM)
    chart_data2 = CategoryChartData()
    chart_data2.categories = ['고수준 일상동작 (ADL)', '미세 손과제 / FMA 임상 채점']
    chart_data2.add_series('특화 딥러닝 모델', (82.0, 68.0))
    chart_data2.add_series('범용 VLM (Qwen2.5-VL 등)', (77.5, 35.0))

    chart_frame2 = s3.shapes.add_chart(
        XL_CHART_TYPE.COLUMN_CLUSTERED,
        Inches(0.8), Inches(1.45), Inches(5.6), Inches(4.45),
        chart_data2
    )
    chart2 = chart_frame2.chart
    chart2.has_legend = True
    chart2.legend.position = XL_LEGEND_POSITION.TOP
    chart2.legend.font.name = FONT_NAME
    chart2.legend.font.size = Pt(12.5)
    chart2.has_title = True
    chart2.chart_title.text_frame.text = "과제 난이도별 인식 정확도 비교 (NYU Li et al., 2026)"
    set_font(chart2.chart_title.text_frame.paragraphs[0].runs[0], size_pt=14.0, bold=True, color=C_NAVY_MAIN)

    series_dl = chart2.series[0]
    series_dl.format.fill.solid()
    series_dl.format.fill.fore_color.rgb = C_BLUE_ACCENT
    series_vlm = chart2.series[1]
    series_vlm.format.fill.solid()
    series_vlm.format.fill.fore_color.rgb = C_RED_ACCENT

    plots2 = chart2.plots[0]
    plots2.has_data_labels = True
    for s in chart2.series:
        s.data_labels.font.name = FONT_NAME
        s.data_labels.font.size = Pt(13.0)
        s.data_labels.font.bold = True

    # Right: Analysis Cards
    add_card(s3, 6.7, 1.45, 5.833, 4.45, "선행 AI 시도의 명암과 치명적 병목", [
        ("🟢 특화 딥러닝 (Deep Learning):", "처리 시간을 1.4시간으로 단축하고 거친 동작은 양호하게 분류함. 그러나 손가락 미세 관절 정보 결여로 '단순 대기'와 '물체 유지'를 구분하지 못함."),
        ("🔴 범용 VLM (Vision-Language Model):", "빗질하기, 물건 집기 등 고수준 행동 인식은 77.5%로 우수했으나, 미세 손동작 및 FMA 채점은 35%로 무작위 수준에 그침 (성능 너무 안 좋음!)."),
        ("⚠️ 원인: 시각적 환각 (Visual Hallucination):", "2D 영상만으로는 손가락이 물체에 스치기만 해도 '파지 성공'으로 오판하거나, 환자가 시도하지 않은 동작을 생성하는 허위 판독 다수 발생."),
        ("💡 결론 및 연구 기회:", "순수 2D 영상의 시각적 환각을 제어할 물리적 공간 수치 보완이 필수적임.")
    ], badge_text="병목 발견", badge_color=C_AMBER_ACCENT, title_size=18.0, item_size=15.0)

    add_callout(s3, 0.8, 6.1, 11.733, 0.9, "기존 연구의 핵심 한계", 
                "영상만으로는 깊이 방향의 접촉 여부와 미세 벌림을 VLM이 해석할 수 없어 '시각적 환각'이 발생합니다. 물리적 3D 수치 결합이 필수적입니다.")

    # =========================================================================
    # SLIDE 4: 해결 방안: 영상 VLM에 3D 운동학 지표 결합 (Story Step 3)
    # =========================================================================
    s4 = prs.slides.add_slide(blank_layout)
    add_header(s4, "03", "본 연구의 해결 방안: 영상 기반 VLM에 3D 운동학(Kinematics) 지표 결합", "PROPOSED SOLUTION: HYBRID KINEMATICS")

    col_w = 3.644
    gap = 0.4
    left_base = 0.8

    # 3 Large Feature Cards
    add_card(s4, left_base, 1.45, col_w, 4.45, "1. 14프레임 시각 정보\n(Visual Context)", [
        ("• 수행단계 층화 추출:", "단순 균등 분할이 아닌 획득 6장 + 유지 2장 + 해제 6장 배분."),
        ("• 대역폭 최적화:", "비디오 토큰 폭증을 방지하고 핵심 동작 순간 14장 정밀 포착."),
        ("• 거시적 외형 제공:", "환자의 앉은 자세, 팔 뻗기 궤적, 물체 위치 등 거시적 맥락 전달.")
    ], badge_text="시각 문맥", badge_color=C_BLUE_ACCENT, title_size=17.5, item_size=15.0)

    add_card(s4, left_base + col_w + gap, 1.45, col_w, 4.45, "2. 3D 물리 공간 수치\n(F1~F4 Kinematics)", [
        ("• RealSense D455 실측:", "깊이(Depth) 센서 기반 손 관절 3D 공간 기하학 직접 연산."),
        ("• 4대 정예 피처 주입:", "최대 파지폭(F1), 도달시간(F2), 유지안정도(F3), 신전변위(F4)."),
        ("• 시각적 환각 차단:", "스친 것과 실제 쥔 것을 물리적 거리 수치(mm)로 즉시 판별.")
    ], badge_text="물리 수치", badge_color=C_TEAL_ACCENT, title_size=17.5, item_size=15.0)

    add_card(s4, left_base + (col_w + gap) * 2, 1.45, col_w, 4.45, "3. 건강인 기준 규준\n(Normative Anchor)", [
        ("• 건강인 15명 분포:", "과제별 중앙값(Median) 및 사분위수(IQR) 기준선 프롬프트 제공."),
        ("• 품질 플래그 결합:", "센서 유효율 80% 이상, 결측 사유 등 신뢰도 메타데이터 동시 주입."),
        ("• 중증도 판단 닻:", "모델이 마비측 동작의 비정상성과 지연 수준을 객관적 비교 판정.")
    ], badge_text="임상 규준", badge_color=C_AMBER_ACCENT, title_size=17.5, item_size=15.0)

    add_callout(s4, 0.8, 6.1, 11.733, 0.9, "연구 가설의 핵심", 
                "영상(VLM의 자연어 문맥 해석력) + 3D 수치(센서의 정밀 물리 기하학)를 결합하여, 순수 영상 대비 VLM 평가 오차를 의미 있게 줄입니다.")

    # =========================================================================
    # SLIDE 5: 운동학 지표의 과학적 근거: FMA 임상 점수와의 연관성 (Story Step 4)
    # =========================================================================
    s5 = prs.slides.add_slide(blank_layout)
    add_header(s5, "04", "운동학 지표의 과학적 근거: FMA 임상 점수 회복과의 직접적 연관성", "BIOMECHANICAL JUSTIFICATION & FMA")

    # Left: Research Evidence Cards (16pt)
    add_card(s5, 0.8, 1.45, 5.7, 4.45, "생체역학 선행연구가 입증한 핵심 지표", [
        ("🔹 Qiu et al. (2022, IEEE EMBC):", "뇌졸중 아급성기 환자 3D 분석 결과, 최대 파지폭(MGA, F1)과 도달 시점(tMGA, F2)이 FMA 상지 점수 호전과 직접적으로 연동됨을 규명."),
        ("🔹 Lang et al. (2005, 2009, J Neurophysiol):", "편마비 환자의 손가락 능동 신전(펴기) 변위(F4)가 파지 성공 및 기능 회복의 독립적 핵심 전제조건임을 임상적으로 입증."),
        ("🔹 Amprimo et al. (2024, BSPC):", "깊이 센서 결합 손 추적(GMH-D 원리)이 120fps OptiTrack 모션캡처와 높은 일치도를 보임을 검증 (본 연구는 D455 환경에서 별도 자체 검증)."),
        ("🔹 임상적 정당성 확보:", "단순 공학적 수치가 아닌 뇌졸중 환자의 FMA 기능 회복을 대변하는 검증된 물리량만을 엄선하여 VLM에 주입함.")
    ], badge_text="선행연구 입증", badge_color=C_TEAL_ACCENT, title_size=18.0, item_size=15.0)

    # Right: Native Editable Table (운동학 지표와 FMA 연관성 매핑)
    fma_headers = ["지표", "운동학 변수명", "연관 FMA 항목", "임상적 의미"]
    fma_rows = [
        ["F1", "최대 파지폭 (MGA)", "물체 맞춤 개방", "파지 준비 및 시각-운동 협응 능력"],
        ["F2", "도달 시간 (tMGA)", "동작 속도·기민성", "팔 뻗기와 손가락 개방의 시간적 협응"],
        ["F3", "유지 안정도 (SD)", "2초 형태 유지력", "불수의적 떨림 및 미끄러짐 제어력"],
        ["F4", "능동 해제 변위", "손가락 신전/펴기", "물체 분리 및 잔여 굴곡 구축 회복"]
    ]
    fma_widths = [0.9, 1.7, 1.4, 1.733]
    add_native_table(s5, 6.8, 1.45, 5.733, 4.45, fma_headers, fma_rows, fma_widths, font_size_pt=13.0)

    add_callout(s5, 0.8, 6.1, 11.733, 0.9, "피처 선정의 학술적 타당성", 
                "임상 3단계(형성, 유지, 해제)와 FMA 회복 궤적을 대변하는 4대 지표(F1~F4)를 엄선하여, VLM의 주의력 분산 없이 판독 정확도를 높입니다.")

    # =========================================================================
    # SLIDE 6: 4대 평가 과제 프로토콜 및 4대 운동학 피처 체계 (수정 가능한 표)
    # =========================================================================
    s6 = prs.slides.add_slide(blank_layout)
    add_header(s6, "05", "평가 과제 프로토콜 및 4대 핵심 운동학 피처 (F1~F4) 조작적 정의", "TASKS & KINEMATICS PROTOCOL")

    # Native Table 1: 4 Assessment Tasks (Top)
    task_headers = ["과제", "과제 명칭", "대상 물체 규격 및 재질", "목표 파지 형태 (임상의 합의 기준)"]
    task_rows = [
        ["과제 1", "맨손 쥐기와 펴기", "물체 없음 (테이블 맨손)", "네 손가락 완전 굴곡(주먹) 후 2.0초 유지, 편 시작 자세로 능동 개방"],
        ["과제 2", "원통 파지 (Cylinder)", "지름 5cm, 높이 10cm 무광 PLA", "엄지와 네 손가락이 원통 측면을 대향하여 완전히 감싸 쥐는 대향 파지"],
        ["과제 3", "구형 파지 (Spherical)", "지름 7cm 구형체 무광 PLA", "엄지와 굽힌 손가락들이 구면을 둥글게 감싸 쥐는 형태 (5mm 받침대)"],
        ["과제 4", "측면 집기 (Lateral Pinch)", "두께 1.5cm 직육면체 블록", "검지 외측면에 물체를 대고 엄지 끝으로 강하게 누르며 집는 형태"]
    ]
    task_widths = [1.1, 2.3, 3.2, 5.133]
    add_native_table(s6, 0.8, 1.40, 11.733, 2.15, task_headers, task_rows, task_widths, font_size_pt=13.0)

    # Native Table 2: 4 Kinematic Features Definition (Bottom)
    feat_headers = ["피처 ID", "물체 파지 과제 정의", "맨손 쥐기/펴기 과제 정의", "단위", "판정 대상 임상 단계"]
    feat_rows = [
        ["F1", "최대 파지 간격 (Peak Span MGA)", "능동 굴곡 변위 (Active Closing)", "mm", "1단계: 목표 파지 형성 (Formation)"],
        ["F2", "최대 간격 도달 시간 (tMGA)", "최대 주먹 도달 시간 (time to min)", "s", "1단계: 도달-파지 협응 (Coordination)"],
        ["F3", "2.0초 유지 표준편차 (Hold SD)", "2.0초 주먹 유지 표준편차", "mm", "2단계: 형태 유지 안정성 (Hold Stability)"],
        ["F4", "능동 손가락 개방 변위 (Release)", "손가락 능동 재개방 변위 (Reopening)", "mm", "3단계: 물체 분리 및 펴기 (Release)"]
    ]
    feat_widths = [1.1, 3.1, 3.1, 0.9, 3.533]
    add_native_table(s6, 0.8, 3.80, 11.733, 2.15, feat_headers, feat_rows, feat_widths, font_size_pt=13.0)

    add_callout(s6, 0.8, 6.1, 11.733, 0.9, "객관적 알고리즘 적용", 
                "주관적 눈대중 개입을 원천 배제하기 위해, 속도 변곡점(|v(t)| < 10mm/s) 기반으로 2초 유지 구간(hold_duration_s >= 2.0s)을 자동 검출합니다.")

    # =========================================================================
    # SLIDE 7: 조건별 VLM 성능 비교 설계 ($A_1 \sim A_4, A_0$) (Story Step 5)
    # =========================================================================
    s7 = prs.slides.add_slide(blank_layout)
    add_header(s7, "06", "조건별 VLM 성능 비교 설계: 주 질문(A2 - A1)과 소거 매트릭스", "EXPERIMENTAL CONDITIONS & COMPARISONS")

    # Native Table: Experimental Conditions Matrix
    matrix_headers = ["코드", "조건 명칭", "14프레임 영상", "3D 운동학 수치", "건강인 정상 규준", "답하려는 핵심 과학적 질문", "비교 역할"]
    matrix_rows = [
        ["A1", "영상 단독 기본군", "✔ 제공", "❌ 제외", "❌ 제외", "순수 시각 정보만으로 VLM이 동작을 얼마나 정확히 판독하는가?", "시각 기준선 (Li 2026 재현)"],
        ["A2", "영상+운동학 결합군", "✔ 제공", "✔ 제공 (좌우)", "❌ 제외", "정량적 3D 수치 주입 시 시각적 환각과 판독 오차가 줄어드는가?", "★ Primary 비교 (A2 − A1)"],
        ["A3", "영상+수치+규준군", "✔ 제공", "✔ 제공", "✔ 제공 (15명)", "정상인 기준 분포를 함께 제시할 때 모델의 이상 판단이 개선되는가?", "보조 비교 1 (A3 − A2)"],
        ["A4", "수치 전용 소거군", "❌ 제외", "✔ 제공", "✔ 제공", "영상 없이 수치 텍스트만으로 평가가 가능한가? (시각 순기여도 역검증)", "보조 비교 2 (A3 − A4)"],
        ["A0", "고전 ML 벤치마크", "❌ 제외", "✔ 제공", "✔ 제공", "순서형 로지스틱 회귀(지도학습)보다 거대 VLM이 실제로 우월한가?", "보조 비교 4 (A3 − A0)"],
        ["D1~D4", "피처별 소거군", "✔ 제공", "1개씩 소거", "❌ 제외", "F1, F2, F3, F4 중 어떤 피처가 오차 감소에 가장 결정적인가?", "조건부 피처 기여도 분석"]
    ]
    matrix_widths = [0.8, 2.1, 1.2, 1.3, 1.3, 3.433, 1.6]
    add_native_table(s7, 0.8, 1.45, 11.733, 4.45, matrix_headers, matrix_rows, matrix_widths, font_size_pt=12.5)

    add_callout(s7, 0.8, 6.1, 11.733, 0.9, "주 가설 (Primary Hypothesis)", 
                "주 비교인 A2 − A1의 환자별 절대등급오차(MAE) 차이가 0 미만(오차 감소)이며, 10,000회 부트스트랩 95% CI 상한이 0 미만임을 검증합니다.")

    # =========================================================================
    # SLIDE 8: 100% 로컬 온프레미스 인프라 & 5종 VLM 벤치마크
    # =========================================================================
    s8 = prs.slides.add_slide(blank_layout)
    add_header(s8, "07", "단일 PC RTX 5090 (32GB) 환경: 5대 로컬 VLM 100% 오프라인 구동", "HARDWARE & MODEL BENCHMARK")

    # Left: Native Editable Chart (VRAM Footprint vs 32GB Limit)
    chart_data3 = CategoryChartData()
    chart_data3.categories = ['Qwen3-VL-8B', 'Qwen3-VL-30B', 'LLaVA-NeXT', 'Qwen2.5-VL-32B', 'LLaVA-OneVision']
    chart_data3.add_series('총 VRAM 점유량 (GB)', (20.5, 22.5, 19.0, 24.5, 19.5))

    chart_frame3 = s8.shapes.add_chart(
        XL_CHART_TYPE.COLUMN_CLUSTERED,
        Inches(0.8), Inches(1.45), Inches(5.6), Inches(4.45),
        chart_data3
    )
    chart3 = chart_frame3.chart
    chart3.has_legend = False
    chart3.has_title = True
    chart3.chart_title.text_frame.text = "5대 로컬 VLM 총 VRAM 점유량 (GB) vs 32GB 한도"
    set_font(chart3.chart_title.text_frame.paragraphs[0].runs[0], size_pt=13.5, bold=True, color=C_NAVY_MAIN)

    series_vram = chart3.series[0]
    series_vram.format.fill.solid()
    series_vram.format.fill.fore_color.rgb = C_BLUE_ACCENT
    plots3 = chart3.plots[0]
    plots3.has_data_labels = True
    plots3.data_labels.font.name = FONT_NAME
    plots3.data_labels.font.size = Pt(13.0)
    plots3.data_labels.font.bold = True

    # Right: Native Editable Table (Model Specifications)
    model_headers = ["모델 식별자", "가중치", "VRAM", "안전 마진", "선정 배경"]
    model_rows = [
        ["Qwen3-VL-8B-Instruct", "BF16", "20.5 GB", "여유 36%", "최신 주 모델 (초고속 추론)"],
        ["Qwen3-VL-30B-A3B", "AWQ 4-bit", "22.5 GB", "여유 30%", "최신 고성능 MoE 단일 GPU"],
        ["LLaVA-NeXT-Video-7B", "BF16", "19.0 GB", "여유 41%", "비디오 시계열 특화 재현"],
        ["Qwen2.5-VL-32B-Instruct", "AWQ 4-bit", "24.5 GB", "여유 23%", "Li et al.(2026) 재현군"],
        ["LLaVA-OneVision-7B", "BF16", "19.5 GB", "여유 39%", "오픈소스 멀티모달 표준"]
    ]
    model_widths = [2.1, 0.9, 0.8, 0.8, 1.233]
    add_native_table(s8, 6.7, 1.45, 5.833, 4.45, model_headers, model_rows, model_widths, font_size_pt=12.5)

    add_callout(s8, 0.8, 6.1, 11.733, 0.9, "의료 데이터 프라이버시 보호", 
                "외부 상용 API 호출 0회! 5개 모델 전체가 RTX 5090 32GB 단일 워크스테이션에서 100% 로컬 오프라인으로 안전하게 구동됩니다.")

    # =========================================================================
    # SLIDE 9: 환각 방지형 2단계 채점 루브릭 및 총 실행 규모 (11,580회)
    # =========================================================================
    s9 = prs.slides.add_slide(blank_layout)
    add_header(s9, "08", "환각 방지형 결정론적 채점 루브릭 및 총 실행 규모 (11,580회)", "SCORING PIPELINE & COMPUTATIONAL SCALE")

    # Left: Native Editable Scoring Rubric Table
    rub_headers = ["등급", "명칭", "결정론적 매핑 규칙", "임상적 상태 의미"]
    rub_rows = [
        ["0점", "목표 형성 미완료", "목표 파지 형태(또는 주먹) 형성 실패", "도달 실패, 쥐기 불능, 중증 마비"],
        ["1점", "부분 수행 완료", "형성은 완료했으나 2초 유지 또는 펴기 미완료", "형성은 되나 떨림/미끄러짐, 펴기 마비"],
        ["2점", "전체 수행 완료", "형성 성공, 2.0초간 유지, 4초 내 펴기 완료", "과제 전 단계 정상 수행 완성"],
        ["NA", "판독 불가 / 중단", "심한 가림 또는 통증·피로로 중단된 경우", "성능 평가 분모(Coverage) 분리 기록"]
    ]
    rub_widths = [0.8, 1.7, 2.0, 1.333]
    add_native_table(s9, 0.8, 1.45, 5.833, 4.45, rub_headers, rub_rows, rub_widths, font_size_pt=13.0)

    # Right: Pipeline Mechanism & Computation Scale Cards
    add_card(s9, 6.9, 1.45, 5.633, 4.45, "환각 차단 파이프라인 & 실행량", [
        ("🔹 1단계: VLM 상태 추출:", "모델에게 점수를 직접 계산하게 하지 않고, complete/incomplete 상태와 프레임/수치 증거(JSON)만 출력하도록 통제."),
        ("🔹 2단계: 파이썬 규칙 엔진:", "외부 코드가 루브릭에 따라 0/1/2점으로 엄격히 결정론적 변환하여 점수 왜곡 및 환각 차단."),
        ("🔹 총 11,580회 로컬 추론:", ""),
        ("   • 핵심 조건 (A1~A4):", "480시행 × 4조건 × 5모델 = 9,600회"),
        ("   • 피처 소거 (D1~D4):", "480시행 × 4조건 = 1,920회"),
        ("   • 구현 재현성 확인:", "대표 60시행 1회 점검 = 60회 (재현성 점검)"),
        ("🔹 통계 검정:", "환자 단위 10,000회 블록 부트스트랩 95% CI 산출.")
    ], badge_text="결정론적 채점", badge_color=C_TEAL_ACCENT, title_size=18.0, item_size=14.5)

    add_callout(s9, 0.8, 6.1, 11.733, 0.9, "엄밀한 재현성 보장", 
                "do_sample=False 탐욕적 결정론적 추론과 비트 수준 구현 재현성 점검을 통해, 모델의 점수 왜곡 없는 투명한 평가를 실현합니다.")

    # =========================================================================
    # SLIDE 10: 결론 및 기대 효과 (Summary & Roadmap)
    # =========================================================================
    s10 = prs.slides.add_slide(blank_layout)
    add_header(s10, "09", "연구 기대 효과 및 향후 추진 로드맵: 임상 자동화의 새 지평", "CONCLUSION & EXPECTED IMPACT")

    # 3 Large Visual Impact Cards
    add_card(s10, left_base, 1.45, col_w, 4.45, "1. 학술적 기여\n(Academic Value)", [
        ("• 환각 극복 최초 실증:", "2D 비디오의 시각적 환각 한계를 3D 운동학 수치로 보완하는 최초의 체계적 실증 연구."),
        ("• Zero-shot 임상 평가:", "재학습(Fine-tuning) 없는 동결 VLM의 뇌졸중 재활 평가 가능성 규명."),
        ("• 프롬프팅 표준 수립:", "헬스케어 도메인 특화 멀티모달 센서-언어 결합 표준 방법론 정립.")
    ], badge_text="학술 가치", badge_color=C_BLUE_ACCENT, title_size=17.5, item_size=15.0)

    add_card(s10, left_base + col_w + gap, 1.45, col_w, 4.45, "2. 임상적 기여\n(Clinical Utility)", [
        ("• 판독 시간 90% 이상 절감:", "치료사의 수작업 비디오 주석 부담(513시간)을 획기적으로 경감하는 사전 채점 초안 제공."),
        ("• 객관적 정량 척도 제공:", "평가자 간 주관적 편차를 줄이고 표준화된 운동학 데이터베이스 구축."),
        ("• 재활 플랫폼 확장:", "향후 가정 및 원격 상지 재활 모니터링 시스템의 핵심 알고리즘으로 연계.")
    ], badge_text="임상 기여", badge_color=C_TEAL_ACCENT, title_size=17.5, item_size=15.0)

    add_card(s10, left_base + (col_w + gap) * 2, 1.45, col_w, 4.45, "3. 추진 로드맵\n(Execution Roadmap)", [
        ("• [1단계] 개발 건강인 4명:", "카메라 화각(70cm) 및 14프레임 샘플링 파이프라인 사전 점검."),
        ("• [2단계] 대조군 15명:", "양손 3D 운동학 정상치 규준(A3) 데이터베이스 산출 완료."),
        ("• [3단계] 편마비 환자 15명:", "양손 480시행 촬영 및 이중 블라인드 임상의 합의 채점."),
        ("• [4단계] 11,580회 추론:", "RTX 5090 기반 로컬 추론 완결 및 부트스트랩 통계 분석.")
    ], badge_text="추진 계획", badge_color=C_AMBER_ACCENT, title_size=17.5, item_size=15.0)

    add_callout(s10, 0.8, 6.1, 11.733, 0.9, "최종 연구 비전", 
                "인력과 시간이 부족한 재활 임상 현장에 정밀하고 안전한 100% 로컬 AI 보조 평가 솔루션을 제시하여, 환자의 지속적인 회복을 돕겠습니다.")

    # Save exclusively to the brand-new requested file: 연구계획서_발표자료_20260911_최종수정본.pptx
    out_new = Path(r"C:\Users\passp\OneDrive\바탕 화면\jeayong\capstone\연구계획서_발표자료_20260911_최종수정본.pptx")
    prs.save(str(out_new))
    print(f"Successfully generated brand-new presentation: {out_new}")

if __name__ == '__main__':
    build_presentation()
