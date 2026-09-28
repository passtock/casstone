# -*- coding: utf-8 -*-
"""손과제 VLM 연구계획 발표덱 v2 빌더 (2026-09-28).

목적: 0928 원본 덱을 '가독성 위주'로 재구성하고, 받은 피드백 2건을 반영한다.
  ① 실험 세팅이 어떻게 되는지 → 전용 슬라이드 + 사진 자리
  ② 왜 저 2개 동작인가 (ARAT 위계 질문) → 전용 슬라이드 + 근거
사진은 자리(placeholder)만 만들고, 필요한 그림 설명을 슬라이드에 적는다.

정본: outputs/research-plan-v6.md (v6.3)
출력: capstone/손과제_VLM_연구계획_v2.pptx
"""
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from pptx.oxml.ns import qn

# ── 팔레트 ───────────────────────────────────────────────
NAVY   = RGBColor(0x14, 0x2A, 0x4C)
INK    = RGBColor(0x1F, 0x2A, 0x37)
MUTED  = RGBColor(0x5B, 0x6B, 0x80)
TEAL   = RGBColor(0x0E, 0x83, 0x8A)
AMBER  = RGBColor(0xB8, 0x6A, 0x00)
RED    = RGBColor(0xB3, 0x2D, 0x2D)
GREEN  = RGBColor(0x1E, 0x7A, 0x46)
BG     = RGBColor(0xF7, 0xF9, 0xFC)
CARD   = RGBColor(0xFF, 0xFF, 0xFF)
EDGE   = RGBColor(0xD3, 0xDC, 0xE6)
LIGHT  = RGBColor(0xEC, 0xF2, 0xF7)
PH_FIL = RGBColor(0xF1, 0xF4, 0xF8)
PH_EDG = RGBColor(0xA9, 0xB6, 0xC6)
WHITE  = RGBColor(0xFF, 0xFF, 0xFF)
FONT   = "Malgun Gothic"

prs = Presentation()
prs.slide_width = Inches(13.3333)
prs.slide_height = Inches(7.5)
BLANK = prs.slide_layouts[6]


# ── 저수준 유틸 ───────────────────────────────────────────
def _ea(run, name=FONT):
    """한글이 깨지지 않도록 ea(latin 아님) 글꼴도 지정."""
    rPr = run._r.get_or_add_rPr()
    latin = rPr.find(qn("a:latin"))
    ea = rPr.find(qn("a:ea"))
    if ea is None:
        ea = rPr.makeelement(qn("a:ea"), {})
        if latin is not None:
            latin.addnext(ea)
        else:
            rPr.append(ea)
    ea.set("typeface", name)


def txt(slide, l, t, w, h, anchor=MSO_ANCHOR.TOP):
    tb = slide.shapes.add_textbox(Inches(l), Inches(t), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = Inches(0.05)
    tf.margin_top = tf.margin_bottom = Inches(0.02)
    return tf


def para(tf, first, text, size=13, bold=False, color=INK, space_before=2,
         space_after=2, align=PP_ALIGN.LEFT, line=0.95, bullet=None):
    p = tf.paragraphs[0] if first else tf.add_paragraph()
    p.alignment = align
    p.space_before = Pt(space_before)
    p.space_after = Pt(space_after)
    p.line_spacing = line
    if bullet:
        text = bullet + " " + text
    r = p.add_run()
    r.text = text
    r.font.size = Pt(size)
    r.font.bold = bold
    r.font.color.rgb = color
    r.font.name = FONT
    _ea(r)
    return p


def rich(tf, first, segs, size=13, space_before=2, space_after=2, line=0.95,
         align=PP_ALIGN.LEFT, bullet=None):
    """segs = [(text, bold, color), ...]"""
    p = tf.paragraphs[0] if first else tf.add_paragraph()
    p.alignment = align
    p.space_before = Pt(space_before)
    p.space_after = Pt(space_after)
    p.line_spacing = line
    if bullet:
        r = p.add_run(); r.text = bullet + " "
        r.font.size = Pt(size); r.font.name = FONT
        r.font.color.rgb = MUTED; _ea(r)
    for text, bold, color in segs:
        r = p.add_run()
        r.text = text
        r.font.size = Pt(size)
        r.font.bold = bold
        r.font.color.rgb = color
        r.font.name = FONT
        _ea(r)
    return p


def rect(slide, l, t, w, h, fill=CARD, line=EDGE, rounded=True, line_w=0.75,
         dash=None):
    shp = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE if rounded else MSO_SHAPE.RECTANGLE,
        Inches(l), Inches(t), Inches(w), Inches(h))
    if rounded:
        try:
            shp.adjustments[0] = 0.06
        except Exception:
            pass
    if fill is None:
        shp.fill.background()
    else:
        shp.fill.solid(); shp.fill.fore_color.rgb = fill
    if line is None:
        shp.line.fill.background()
    else:
        shp.line.color.rgb = line
        shp.line.width = Pt(line_w)
        if dash:
            shp.line.dash_style = dash
    shp.shadow.inherit = False
    shp.text_frame.word_wrap = True
    return shp


def card(slide, l, t, w, h, title, lines, accent=TEAL, fill=CARD,
         title_size=14, body_size=12.5, pad=0.16):
    """테두리 카드 + 제목 + 본문 줄들."""
    rect(slide, l, t, w, h, fill=fill)
    # 좌측 액센트 띠
    rect(slide, l, t + 0.10, 0.055, h - 0.20, fill=accent, line=None, rounded=False)
    tf = txt(slide, l + pad + 0.06, t + 0.07, w - 2 * pad - 0.06, h - 0.14)
    para(tf, True, title, size=title_size, bold=True, color=NAVY, space_after=3)
    for ln in lines:
        if isinstance(ln, tuple):
            _t, _b, _c = ln
            rich(tf, False, [(_t, _b, _c)], size=body_size)
        else:
            para(tf, False, ln, size=body_size, color=INK)
    return tf


def photo_slot(slide, l, t, w, h, title, bullets):
    """사진 자리(점선) + 어떤 그림이 필요한지."""
    shp = rect(slide, l, t, w, h, fill=PH_FIL, line=PH_EDG, line_w=1.0)
    try:
        from pptx.enum.dml import MSO_LINE_DASH_STYLE
        shp.line.dash_style = MSO_LINE_DASH_STYLE.DASH
    except Exception:
        pass
    tf = shp.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.TOP
    para(tf, True, "[ 사진 자리 ]  " + title, size=12, bold=True, color=RGBColor(0x47,0x55,0x69))
    for b in bullets:
        para(tf, False, "· " + b, size=10.5, color=MUTED, line=1.0)
    para(tf, False, "※ 이 칸에 사진/도면을 넣어 주세요", size=10, color=PH_EDG)
    return shp


# ── 헤더/푸터 ─────────────────────────────────────────────
COUNTER = {"n": 0}


def slide_new(title, subtitle=None, tag=None):
    s = prs.slides.add_slide(BLANK)
    COUNTER["n"] += 1
    # 배경
    rect(s, 0, 0, 13.3333, 7.5, fill=BG, line=None, rounded=False)
    # 상단 띠
    rect(s, 0, 0, 13.3333, 0.13, fill=NAVY, line=None, rounded=False)
    # 번호 배지
    badge = rect(s, 0.52, 0.42, 0.62, 0.62, fill=NAVY, line=None)
    bt = badge.text_frame
    bt.vertical_anchor = MSO_ANCHOR.MIDDLE
    para(bt, True, "%02d" % COUNTER["n"], size=17, bold=True, color=WHITE,
         align=PP_ALIGN.CENTER, space_before=0, space_after=0)
    # 제목 (길면 자동 축소해 1줄 유지)
    def _w(t, sz):
        return sum(1.0 if ord(c) > 0x1100 else 0.55 for c in t) * sz * 0.98
    tsz = 24
    while tsz > 17 and _w(title, tsz) > 545:
        tsz -= 1
    tf = txt(s, 1.32, 0.36, 8.05, 0.84, anchor=MSO_ANCHOR.MIDDLE)
    para(tf, True, title, size=tsz, bold=True, color=NAVY, space_after=0)
    if subtitle:
        para(tf, False, subtitle, size=12.5, color=MUTED, space_before=1)
    if tag:
        tt = txt(s, 9.6, 0.46, 3.2, 0.5, anchor=MSO_ANCHOR.MIDDLE)
        para(tt, True, tag, size=11, bold=True, color=TEAL, align=PP_ALIGN.RIGHT)
    return s


def footer(s, note):
    tf = txt(s, 0.55, 7.06, 12.3, 0.32)
    para(tf, True, note, size=9.5, color=MUTED)


# ══════════════════════════════════════════════════════════
# S1. 표지
# ══════════════════════════════════════════════════════════
s = prs.slides.add_slide(BLANK)
rect(s, 0, 0, 13.3333, 7.5, fill=NAVY, line=None, rounded=False)
rect(s, 0, 0, 13.3333, 0.16, fill=TEAL, line=None, rounded=False)
rect(s, 0.9, 2.15, 1.5, 0.075, fill=TEAL, line=None, rounded=False)
tf = txt(s, 0.9, 2.35, 11.5, 2.2)
para(tf, True, "수치를 넣으면 VLM 채점이 좋아지는가,", size=31, bold=True, color=WHITE, space_after=2)
para(tf, False, "아니면 나빠지는가", size=31, bold=True, color=WHITE, space_after=10)
para(tf, False, "— ARAT 두 항목에서 품질 기반 수치 선별의 효과 —", size=15, color=RGBColor(0xA8,0xC6,0xD8))
tf2 = txt(s, 0.9, 5.30, 11.5, 0.95)
para(tf2, True, "이재용  22000561  |  한동대학교 기계제어공학부", size=13, color=WHITE, space_after=4)
para(tf2, False, "연구계획 발표  ·  2026-09-28  ·  설계 정본 v6.3", size=11.5, color=RGBColor(0x8F,0xA8,0xBE))
tf3 = txt(s, 0.9, 6.42, 11.5, 0.42)
para(tf3, True, "※ 모든 수치는 계획값이며, 본평가 결과가 아니다 (실증 데이터 아직 수집 전).",
     size=10.5, color=RGBColor(0xD9,0xB0,0x6B))

# ══════════════════════════════════════════════════════════
# S2. 한 장 요약
# ══════════════════════════════════════════════════════════
s = slide_new("이 연구는 무엇을 하는가", "질문 · 개입 · 대상 · 결과를 한 장에", "SUMMARY")
card(s, 0.55, 1.32, 6.05, 2.55, "연구 질문",
     ["① 수치를 주면 VLM 채점이 좋아지는가, 나빠지는가?",
      "② 품질로 골라 주면 그 해로움이 줄어드는가?",
      "③ 그 대가는 '과잉 보류'인가?"], accent=TEAL)
card(s, 6.85, 1.32, 5.9, 2.55, "개입(intervention)",
     ["같은 영상 · 같은 사람 · 같은 시행에서",
      "VLM에 넣는 수치의 양과 품질만 바꾼다",
      "A1 없음 · A2 전체 · A3 품질선별 · R 무작위제외"], accent=AMBER)
card(s, 0.55, 4.02, 6.05, 2.85, "대상과 규모",
     ["뇌졸중 23명(개발 3 + 본평가 20)",
      "비장애인 22명(개발 6 + 검증 16)",
      "본평가: 20명 × 2과제 × 3시행 = 120영상 × 2모델",
      "독립 분석 단위 = 사람(20명)"], accent=TEAL)
card(s, 6.85, 4.02, 5.9, 2.85, "주 결과 3개 (확증, Holm k=3)",
     ["PR-1  수치 주입 효과    MAE(A2) − MAE(A1)",
      "PR-2  게이팅 효과        MAE(A2) − MAE(A3)",
      "PR-3  게이팅 고유가치  MAE(R) − MAE(A3)",
      "부호 + = 나쁜 방향. 보류율·Pareto도 1급 보고"], accent=NAVY)
footer(s, "정본: outputs/research-plan-v6.md (v6.3, 2026-09-28)")

# ══════════════════════════════════════════════════════════
# S3. 문제
# ══════════════════════════════════════════════════════════
s = slide_new("왜 필요한가 — 임상 평가의 한계와 VLM의 실패", "두 문제가 동시에 존재한다", "BACKGROUND")
card(s, 0.55, 1.32, 6.05, 4.15, "문제 ①  임상 평가(ARAT·FMA-UE)의 구조적 한계",
     ["평가자 주관성 — 항목 일치 >90%여도 갈리는 항목 4/33 (Hernández 2019)",
      "천장/바닥 효과 — ARAT 발병 3일 바닥 38%, 4주 천장 21.3% (Kristersson 2019)",
      "긴 소요 시간 — 전 항목 수행은 임상 현장에서 부담",
      "점수는 맞아도 수치는 틀릴 수 있음 — 손목 96 mm 오차인데 r=0.981 (Li 2022)",
      ("→ 점수로는 안 보이는 손가락 손상·보상 전략이 존재 (Padilla-Magaña 2022)", True, AMBER)],
     accent=AMBER, body_size=12)
card(s, 6.85, 1.32, 5.9, 4.15, "문제 ②  VLM 단독 채점의 실패",
     ["Li 2026 (PLOS Digit Health 5(7):e0001506, PMID 42406872)",
      "코호트: 비장애 20 + 뇌졸중 51",
      "Qwen2.5-VL-72B에 영상+지침만 입력",
      ("→ FMA 총점 예측이 중증도와 무관하게 '평탄'(essentially constant)", True, RED),
      ("→ '무조건 1점' 기준선과 오차가 비슷", True, RED),
      ("→ 정밀 운동 이해 부족. dose는 시각정보 제외 기준선과 유사", True, RED),
      "※ 우리 VLM = Li 2026과 같은 모델 → 직접 비교 가능"],
     accent=RED, body_size=12)
footer(s, "핵심: 점수로는 안 보이고, 영상만으로는 못 잡는다 → 그 사이에 '수치를 어떻게 넣을 것인가'가 있다")

# ══════════════════════════════════════════════════════════
# S4. 연구 질문과 2단 논리
# ══════════════════════════════════════════════════════════
s = slide_new("연구 질문 — 수치를 '다' 줄까, '골라서' 줄까", "정보를 더 주는 것이 항상 이롭지 않다는 근거에서 출발", "QUESTION")
card(s, 0.55, 1.35, 12.2, 1.5, "한 문장 질문",
     ["수치를 주면 채점이 좋아지는가, 나빠지는가 — 그리고 품질이 확인된 수치만 주면 그 나쁨이 줄어드는가, 그 대가는 과잉 보류인가?"],
     accent=TEAL, title_size=15, body_size=14)
card(s, 0.55, 3.02, 3.9, 3.4, "① 왜 '수치 주입'이 위험한가",
     ["Tang 2025: 예시 3개가 최적, 4개에서 0.42로 붕괴",
      "→ 정보를 더 주면 모델이 망가질 수 있다",
      "Li 2026은 영상만 줬음 → '수치를 줄 때의 위험'은 미측정"], accent=RED, body_size=11.5)
card(s, 4.68, 3.02, 3.9, 3.4, "② 왜 '품질 선별'이 필요한가",
     ["RGB-D는 가림·깊이 오류로 수치가 조용히 틀린다",
      "그 수치를 그대로 믿으면 오류가 채점으로 전파",
      "→ 관측 가능성 Q로 골라서 제공"], accent=TEAL, body_size=11.5)
card(s, 8.82, 3.02, 3.93, 3.4, "③ 왜 '무작위 제외'와 비교하나",
     ["선별이 좋아 보여도 '숫자를 덜 봐서'일 수 있다",
      "같은 양을 무작위로 빼는 R 조건 필요",
      "→ 품질 규칙 자체의 기여를 분리"], accent=NAVY, body_size=11.5)
footer(s, "탐색적(보정 없음): A0·A0-time·A4·오류주입(bias/burst) 기전 — 주 비교 아님")

# ══════════════════════════════════════════════════════════
# S5. ★ 실험 세팅 (피드백 ①)
# ══════════════════════════════════════════════════════════
s = slide_new("실험 세팅 — 환경과 기록", "피드백 반영 ① · 무엇을 어떤 환경에서 어떻게 기록하는가", "SETUP")
card(s, 0.55, 1.30, 4.0, 2.62, "장비",
     ["Intel RealSense D455 × 1대 (단일 RGB-D)",
      "RGB 1280×800 / depth 1280×720",
      "스펙 30 fps, 실측 16.9·24.6 fps (dt 불규칙)",
      ("→ 실제 프레임 타임스탬프로 dt 계산", True, AMBER),
      "삼각대 · 작업거리 0.65–0.85 m · 아래 30–45°"], accent=TEAL, body_size=11.5)
card(s, 4.68, 1.30, 4.0, 2.62, "환경 (ARAT 표준 배치)",
     ["테이블 높이 75 cm",
      "의자 좌면 46 cm · 팔걸이 없음 · 등받이 계속 접촉",
      "선반: 테이블면에서 37 cm",
      "물체 위치: 정중시상면과 액와선의 중간"], accent=TEAL, body_size=11.5)
card(s, 8.82, 1.30, 3.93, 2.62, "대상자",
     ["비장애인 22명 (개발 6 + 독립검증 16)",
      "뇌졸중 23명 (개발 3 + 본평가 20)",
      "성인 일측성 뇌졸중 · 임상적으로 안정",
      "점수를 보고 대상자를 빼거나 더하지 않음"], accent=TEAL, body_size=11.5)
card(s, 0.55, 4.05, 6.42, 2.82, "절차와 저장",
     ["연습 2회 → 본 시행(연습 제외 후 첫 3회를 사전 고정)",
      "T1 → 휴식 2분 → T2 · 시행마다 즉시 채점 (치료사 1인)",
      "독립 영상 평가자: 장애인당 12영상, 모델 출력에 눈가림",
      "저장 계층: L0 원본 RGB+원시 depth+타임스탬프 → L1 랜드마크 → L2 K1·K2 JSON → L3 VLM 프레임",
      ("→ 원시 depth는 반드시 보존 (PNG 수 == 프레임 수 검증)", True, AMBER)],
     accent=NAVY, body_size=11.5)
photo_slot(s, 7.20, 4.05, 5.55, 2.82, "실험 세팅 전경",
           ["카메라(D455)+삼각대 위치, 대상자 기준 작업거리 0.65–0.85 m",
            "테이블 75 cm + 선반 37 cm + 팔걸이 없는 의자",
            "환측 손과 블록/구슬/뚜껑이 함께 보이는 구도",
            "가능하면 측면 30–45° 시점 1장 + 위에서 본 배치 도면 1장"])
footer(s, "ARAT 표준 물성·배치: Yozbatiran et al. 2008 (doi 10.1177/1545968307305353), Lyle 1981 원형")

# ══════════════════════════════════════════════════════════
# S6. ★ 왜 2개 동작인가 (피드백 ②)
# ══════════════════════════════════════════════════════════
s = slide_new("왜 이 2개 동작인가", "피드백 반영 ② · \"가장 어려운 것 하나면 되지 않나?\" — ARAT 위계 질문에 대한 답", "RATIONALE")
card(s, 0.55, 1.30, 12.2, 1.06, "질문의 전제부터 확인",
     ["ARAT의 건너뛰기 규칙은 '가장 어려운 것을 통과하면 아래를 만점 처리'가 맞다 — 단, 그 규칙은 하위검사(subtest) 안에서만 적용된다."],
     accent=AMBER, title_size=13.5, body_size=13)
card(s, 0.55, 2.50, 3.95, 4.32, "① 규칙은 하위검사 내부 전용",
     ["Lyle 1981 / Yozbatiran 2008 / ARAT 채점지:",
      ("\"if the subject passes the first, no more need to be administered and he scores top marks for that subtest\"", False, MUTED),
      "Grasp·Grip·Pinch·Gross 각각 따로 적용",
      ("→ T1 = ARAT 3번 = Grasp 소척도", True, NAVY),
      ("→ T2 = ARAT 12번 = Pinch 소척도", True, NAVY),
      ("→ 서로 다른 하위검사이므로 중복이 아니다", True, GREEN)],
     accent=TEAL, body_size=11)
card(s, 4.63, 2.50, 3.95, 4.32, "② 위계 자체가 완전하지 않다",
     ["Koh 2006 (n=351, Mokken+Rasch)",
      ("19개 중 유일하게 위계를 깨는 항목 = \"pinch ball bearing 3rd finger and thumb\"", True, RED),
      "→ 위반이 하필 pinch 계열에서 나타난다",
      "van der Lee 2002 (n=63)",
      ("19개 중 15개만 불변 위계 · 소척도 구조는 경험적으로 지지 안 됨", True, RED),
      "→ '하나면 나머지 자동' 가정은 성립하지 않음"],
     accent=RED, body_size=11)
card(s, 8.71, 2.50, 4.04, 4.32, "③ 우리 목적은 '총점 추정'이 아니다",
     ["우리는 한 시행의 VLM 채점과 그때 넣는 수치의 의미를 본다",
      "Koh 2006: ARAT 원점수는 순서 정보만 줌 (정확한 기능 수준은 아님)",
      ("T2(구슬, 엄지+검지 패드 강제)", True, GREEN),
      "→ K1(엄지–검지 표면점 거리)의 의미가 정의상 성립 → 주 결과",
      ("T1(블록, opposition이면 어떤 파지든 허용)", True, AMBER),
      "→ K1 의미가 애매 → 참고용. 파지 유형이 바뀌어도 K1 해석이 버티는지 비교"],
     accent=NAVY, body_size=11)
footer(s, "Koh 2006: PMID 17067971 (doi 10.1080/16501970600803252) · van der Lee 2002: Clin Rehabil 16(6):646-653 (doi 10.1191/0269215502cr534oa)")

# ══════════════════════════════════════════════════════════
# S7. 두 과제 상세 + 사진 자리
# ══════════════════════════════════════════════════════════
s = slide_new("두 과제의 물성과 배치", "ARAT 표준 (Yozbatiran 2008)", "TASKS")
card(s, 0.55, 1.32, 4.0, 3.05, "T2 · 주 결과  (ARAT 12번)",
     ["소척도: Pinch",
      "물체: 구슬 지름 1.5 cm · 5.4 g",
      "요구: 엄지 + 검지 '패드' 맞섬 강제",
      "배치: 하부 뚜껑(근위연 5 cm) → 선반 위 상부 뚜껑",
      "3점: 5초 이내 + 엄지+검지 패드"], accent=GREEN, body_size=11.5)
card(s, 4.68, 1.32, 4.0, 3.05, "T1 · 참고  (ARAT 3번)",
     ["소척도: Grasp",
      "물체: 목재 블록 5 cm · 55 g",
      "요구: opposition이면 어떤 파지든 허용(손가락 쌍 미강제)",
      "배치: 테이블 → 선반 37 cm 위",
      "3점: 5초 이내 정상 수행"], accent=AMBER, body_size=11.5)
card(s, 8.82, 1.32, 3.93, 3.05, "채점 (공통)",
     ["0 = 60초 내 어떤 부분도 못함",
      "1 = 60초 내 부분 수행",
      "2 = 완료했으나 5–60초 또는 큰 어려움",
      "3 = 5초 이내 정상 수행",
      ("두 항목 합계 0–6점을 임상점수로 쓰지 않음", True, RED)],
     accent=NAVY, body_size=11.5)
photo_slot(s, 0.55, 4.50, 6.1, 2.37, "T1 · T2 물체와 배치",
           ["5 cm 목재 블록(55 g)과 구슬(1.5 cm, 5.4 g) 실물 비교 1장",
            "선반 37 cm 위 상부 뚜껑에 구슬을 놓는 장면",
            "테이블 위 배치 도면(물체 위치·뚜껑 2개·선반 높이)"])
card(s, 6.88, 4.50, 5.87, 2.37, "무게·크기 차이가 만드는 질문",
     ["블록 55 g vs 구슬 5.4 g → 무게 약 10배, 크기 약 3.3배",
      "구슬(12번)은 ARAT에서 두 번째로 어려운 난이도군",
      ("핵심 동작 = 37 cm 수직 들어올리기 → 카메라가 수직 시야를 확보해야 함", True, AMBER)],
     accent=TEAL, body_size=11.5)
footer(s, "출처: rgbd-grasp-vlm-protocol-analysis.md §0-1 (ARAT 19개 항목 물성표)")

# ══════════════════════════════════════════════════════════
# S8. K1 · K2
# ══════════════════════════════════════════════════════════
s = slide_new("VLM에 넣는 두 수치 — K1 · K2", "계산은 원본 프레임(L1)에서만. VLM 프레임에서 재계산하지 않는다", "FEATURES")
card(s, 0.55, 1.32, 6.05, 2.35, "K1 — 엄지–검지 표면점 거리 (mm)",
     ["MediaPipe 랜드마크 4번(엄지끝)·8번(검지끝)의 표면점 사이 3D 거리",
      "관찰 구간의 P95(95백분위수)로 요약",
      ("금지 해석: PAp · 실제 최대 벌림 · 관절 중심 거리 · 접촉 여부", True, RED)],
     accent=TEAL, body_size=11.5)
card(s, 6.83, 1.32, 5.92, 2.35, "K2 — 손목 표면점 속도 (mm/s)",
     ["MediaPipe 0번(손목) 표면점의 3D 이동 속도의 P95",
      "dt는 장치/프레임 타임스탬프에서만 (벽시계 금지), dt 하한 적용",
      ("금지 해석: 손가락 민첩성 · 신경 회복량", True, RED)],
     accent=TEAL, body_size=11.5)
card(s, 0.55, 3.85, 6.05, 3.0, "계산 6단계 (요약)",
     ["① 랜드마크 픽셀 중심 5×5 depth 중앙값, 유효비율 ≥50%",
      "② 역투영(intrinsics) → 3D 좌표",
      "③ 손-일관성 검사: 3D 거리(손목–손끝) ∈ [60, 230] mm 밖이면 무효",
      ("   → 가려진 손가락이 배경에 찍히는 오류를 잡는다 (검사 OFF면 오염 110배)", False, MUTED),
      "④ K1 = 4–8번 거리, 양쪽 유효 프레임만, P95",
      "⑤ K2 = 0번 속도, 연속 유효 쌍만, dt 하한 적용, P95",
      "⑥ 검출 실패 = 하드 결측 (보간 금지)"], accent=NAVY, body_size=11.5)
photo_slot(s, 6.83, 3.85, 5.92, 3.0, "K1·K2 개념도",
           ["MediaPipe 21점 랜드마크 위에 4번·8번(빨강), 0번(파랑) 표시",
            "K1 = 엄지–검지 표면점 거리 화살표, K2 = 손목 속도 벡터",
            "가림 상황에서 랜드마크가 배경에 찍힌 '오염' 예시 vs 정상 예시"])
footer(s, "P95 요약은 '표면점 대리값'이며 해부학적 관절 중심 거리가 아니다 (research-plan-v6.md §5)")

# ══════════════════════════════════════════════════════════
# S9. Q 규칙
# ══════════════════════════════════════════════════════════
s = slide_new("품질 선별 규칙 Q — '믿을 만한 수치인가'", "카메라 1대로는 정확도를 알 수 없다 → 관측 가능성(개연성·완전성)을 잰다", "QUALITY")
card(s, 0.55, 1.30, 7.4, 3.55, "규칙 5개 (본평가 전 동결)",
     ["Q1  깊이 유효 비율                 개발 자료에서 임계값 확정",
      "Q2  최장 연속 결측                 > 0.3초 → 보류",
      "Q3  유효 표본 수                    < 50개 → 보류",
      "Q4  깊이 경계 혼합 의심            해당 프레임 > 50% → 보류",
      "Q5  손가락·손목 가림               2인 판정, > 50% → 보류",
      ("걸린 K1 또는 K2는 null로 보류. 영상과 다른 유효 수치는 그대로 제공.", True, GREEN),
      ("치료사 점수를 보고 임계값을 정하지 않는다 → 개발 자료에서 정한 뒤 본평가 전 고정.", True, RED)],
     accent=TEAL, body_size=12)
photo_slot(s, 8.28, 1.30, 4.47, 3.55, "Q 판정 예시",
           ["정상 프레임 vs 가림 프레임 비교 (RGB)",
            "depth 유효 마스크가 뚫린 예시(결측 구간 표시)",
            "랜드마크가 물체 경계에 걸린 '경계 혼합' 예시"])
card(s, 0.55, 5.02, 12.2, 1.85, "R(무작위 제외) 조건과 한계",
     ["R = A3와 '같은 수'를 품질과 무관하게 무작위 제거 (지표별 제외 수 맞춤, 시드 3개)",
      "원래 계산 불가능한 하드 결측은 모든 조건에서 유지 (R에서도 복원 금지)",
      ("지표별 제외 비율이 50%를 넘으면 그 지표의 R 비교는 제한한다.", True, AMBER)],
     accent=NAVY, body_size=11.5)
footer(s, "Q는 '교정된 mm 오차 확률'이 아니며, 환자의 중증도가 아니다 (research-plan-v6.md §5.2·§12)")

# ══════════════════════════════════════════════════════════
# S10. 조건표
# ══════════════════════════════════════════════════════════
s = slide_new("실험 조건과 세 가지 비교", "같은 영상·같은 사람·같은 시행에서 수치의 양과 품질만 바꾼다", "DESIGN")
rows = [
    ("A1", "영상 기준", "K1·K2 제공하지 않음", "영상만 있을 때의 기준선"),
    ("A2", "전체 제공", "계산 가능한 수치 모두 제공", "A2 vs A1 → 수치 추가 효과 (PR-1)"),
    ("A3", "품질 선별", "Q 통과 수치만 제공", "A2 vs A3 → 게이팅 효과 (PR-2)"),
    ("R",  "무작위 제외", "A3와 같은 수를 무작위 제외", "R vs A3 → 선별 기준의 고유 가치 (PR-3)"),
]
tbl = s.shapes.add_table(5, 4, Inches(0.55), Inches(1.35), Inches(12.2), Inches(2.5)).table
tbl.columns[0].width = Inches(1.0)
tbl.columns[1].width = Inches(2.0)
tbl.columns[2].width = Inches(4.2)
tbl.columns[3].width = Inches(5.0)
hdr = ["조건", "이름", "VLM에 넣는 수치", "비교 목적"]
for j, h in enumerate(hdr):
    c = tbl.cell(0, j); c.text = ""
    p = c.text_frame.paragraphs[0]; r = p.add_run(); r.text = h
    r.font.size = Pt(13); r.font.bold = True; r.font.color.rgb = WHITE; r.font.name = FONT; _ea(r)
    c.fill.solid(); c.fill.fore_color.rgb = NAVY
    c.vertical_anchor = MSO_ANCHOR.MIDDLE
    c.margin_left = c.margin_right = Inches(0.1)
for i, row in enumerate(rows, 1):
    for j, v in enumerate(row):
        c = tbl.cell(i, j); c.text = ""
        p = c.text_frame.paragraphs[0]; r = p.add_run(); r.text = v
        r.font.size = Pt(12); r.font.name = FONT; _ea(r)
        r.font.bold = (j == 0)
        r.font.color.rgb = NAVY if j == 0 else INK
        c.fill.solid(); c.fill.fore_color.rgb = CARD if i % 2 else LIGHT
        c.vertical_anchor = MSO_ANCHOR.MIDDLE
        c.margin_left = c.margin_right = Inches(0.1)
card(s, 0.55, 4.08, 6.05, 2.79, "1급 기술 결과 (검정 아님, 반드시 보고)",
     ["보류율(A3) — Q가 수치를 버린 시행 비율 = 게이팅의 '대가'",
      "(보류율, MAE) Pareto 곡선 — Q1 임계값을 쓸어 얻는 트레이드오프",
      "보조 모델의 부호 일치 여부",
      ("→ 이득이 '좁은 구간에서만' 성립할 수 있음을 숨기지 않는다", True, AMBER)],
     accent=AMBER, body_size=11.5)
card(s, 6.83, 4.08, 5.92, 2.79, "탐색적 (보정 없음, CI·효과크기만)",
     ["A4 — 수치만 주고 RGB 제거 (영상의 추가 가치)",
      "A0 — 로지스틱 회귀 경량모형 대조 · A0-time — 시간 단서만",
      "오류 주입 — bias 1u/3u, burst 3u (기전 H5, A2·A3에만)",
      "큰 오차(≥2점) 비율 · 설명 평가 코드북",
      ("→ 주 비교(PR-1·PR-2·PR-3)와 섞지 않는다", True, MUTED)],
     accent=MUTED, body_size=11.5)
footer(s, "동결: 모델 버전·프롬프트·프레임 추출·Q 임계값·R 배정 방식은 본평가 전에 고정")

# ══════════════════════════════════════════════════════════
# S11. VLM 설정 + 프레임
# ══════════════════════════════════════════════════════════
s = slide_new("고정 VLM과 입력 프레임", "추가 학습 없이 동일 모델·동일 프롬프트 — 조건별로 달라지는 것은 수치뿐", "MODEL")
card(s, 0.55, 1.35, 4.0, 2.6, "주 모델",
     ["Qwen2.5-VL-72B-Instruct",
      "Li 2026과 동일 모델 → 직접 비교",
      "추가 학습 없음 · 예시 없는 0-shot · greedy",
      "확증 검정은 주 모델에서만"], accent=TEAL, body_size=11.5)
card(s, 4.68, 1.35, 4.0, 2.6, "보조 모델",
     ["동일 프롬프트 · 동일 프레임",
      "역할: 같은 방향의 부호가 나오는지 확인",
      "검정 아님 (다중비교 폭증 방지)",
      ("체크포인트는 동결 전 확정 (미확정)", True, AMBER)], accent=NAVY, body_size=11.5)
card(s, 8.82, 1.35, 3.93, 2.6, "출력과 실패 처리",
     ["시행별 ARAT 0–3점 한 줄 + 근거 ≤2문장",
      "출력 실패는 1회 재시도",
      "실패는 제거하지 않음",
      "손실 = 3 으로 대체 → 실패포함 손실 + 유효 MAE + 성공률 병기"], accent=RED, body_size=11.5)
photo_slot(s, 0.55, 4.12, 6.4, 2.75, "프레임 샘플링 타임라인",
           ["가로 타임라인: 0–5초 구간은 10 Hz(약 50프레임), 5초 이후는 2 Hz",
            "상한 64프레임 강조, 640×480 리사이즈 표시",
            "실측 fps가 16.9/24.6이면 10 Hz 목표가 실제로 ~8.5 Hz로 저하됨을 각주로 표시"])
card(s, 7.15, 4.12, 5.6, 2.75, "프레임 규칙 (동결)",
     ["앞 5.0초를 10 Hz로 샘플링 (목표 50프레임)",
      "5초 초과분은 2 Hz, 전체 상한 64프레임",
      "해상도 640×480",
      "사건 구간(접촉 순간 등)을 사람이 골라 넣지 않는다",
      ("→ 실제 fps를 읽어 프레임 인덱스를 계산 (30 fps 가정 금지)", True, AMBER)],
     accent=NAVY, body_size=11.5)
footer(s, "프롬프트는 모든 조건에 동일 템플릿. 조건명을 프롬프트에 쓰지 않는다.")

# ══════════════════════════════════════════════════════════
# S12. 분석과 판정
# ══════════════════════════════════════════════════════════
s = slide_new("분석 방법과 판정 기준", "사람 단위 짝지은 비교 · 사람 단위 bootstrap", "ANALYSIS")
card(s, 0.55, 1.32, 6.05, 2.4, "분석 설계",
     ["분석 단위 = 사람(20명). 120영상·주입본은 반복 관측",
      "PR-1 = MAE(A2) − MAE(A1)   수치 주입 효과",
      "PR-2 = MAE(A2) − MAE(A3)   게이팅 효과",
      "PR-3 = MAE(R) − MAE(A3)     게이팅의 고유 가치",
      "사람별 MAE를 짝지어 비교 · bootstrap 10,000회 · 95% CI · Holm k=3"], accent=TEAL, body_size=11.5)
card(s, 6.83, 1.32, 5.92, 2.4, "부호 읽는 법 (양수 = )",
     ["PR-1 양수 → 전체 제공이 악화 (수치 주입이 해로움)",
      "PR-2 양수 → 선별 제공이 개선 (게이팅이 도움)",
      "PR-3 양수 → Q가 무작위 제외보다 우수",
      ("유의성 하나로 결론을 만들지 않는다. CI가 0을 포함하면 '방향 확인 안 됨'.", True, AMBER)],
     accent=NAVY, body_size=11.5)
card(s, 0.55, 3.90, 12.2, 2.95, "예상 패턴과 해석 (사전 등록)",
     ["A2 악화 · A3 개선              → 일부 수치를 보류할 가치가 있다",
      "A3가 R보다 우수                → 단순 정보량 감소가 아니라 품질 규칙이 기여",
      "A2·A3 비슷하게 개선           → 수치 추가 효과는 있으나 선별 이득은 작다",
      "차이가 작거나 불명확          → 효과 크기와 신뢰구간으로 판단 (비유의 = 동등 아님)",
      ("보류율 높음 + PR-2 유의       → 이득이 좁은 구간에서만 (보류–정확도 절충)", True, AMBER),
      ("보류율 높음 + PR-2 비유의     → 과잉 보류가 대가만 남김", True, RED),
      ("보조 모델에서 부호가 반대     → 주 모델 결과를 모델 특이적으로 제한", True, MUTED)],
     accent=NAVY, body_size=11.5)
footer(s, "실패 출력은 유효 MAE에서 제외하고 '실패포함 손실(손실=3)'을 별도 열로 보고한다.")

# ══════════════════════════════════════════════════════════
# S13. 선행연구와 우리 위치
# ══════════════════════════════════════════════════════════
s = slide_new("선행연구가 이미 밝힌 것과 우리가 처음 재는 것", "주장은 '우리가 처음 제안'이 아니라 '우리가 처음 측정'", "EVIDENCE")
card(s, 0.55, 1.30, 4.0, 3.1, "VLM · 센서 채점",
     ["Li 2022 — 뇌졸중 20명, r=0.981, 항목평균 >80%, 그러나 손목 96 mm 오차 (PMID 36291314)",
      "Li 2026 — 비장애 20+뇌졸중 51, 영상만으로 FMA 총점 평탄 (PMID 42406872)",
      "Tang 2025 — 관절 특징을 LLM에 주입, 예시 3개 최적·4개에서 붕괴 (arXiv:2505.18412)"],
     accent=TEAL, body_size=10.5)
card(s, 4.68, 1.30, 4.0, 3.1, "ARAT 척도 구조",
     ["Koh 2006 — 19항목 단일 차원, H=0.95, 유일한 위계 위반 = pinch 항목 (PMID 17067971)",
      "van der Lee 2002 — 15/19만 불변 위계, 소척도 구조 미지지 (doi 10.1191/0269215502cr534oa)",
      "Rodgers 2022 — 5코호트 N=1425, 결정나무로 ARAT 단축 시도"],
     accent=AMBER, body_size=10.5)
card(s, 8.82, 1.30, 3.93, 3.1, "이미 선행된 것 (재주장 금지)",
     ["ARAT 손 과제 운동학 측정·비장애인 비교 (Padilla-Magaña 2022, SVM 97.8%)",
      "RGB-D로 FMA·ARAT 자동채점 (Brain Sci 2022, Clin Rehabil 2024 — 임상검증까지)",
      "JSON·특징 주입, 영상+수치 결합, 이미지 품질 게이트 → VLM 라우팅"],
     accent=RED, body_size=10.5)
card(s, 0.55, 4.60, 12.2, 2.25, "우리 자리 (빈칸)",
     ["Li 2026은 '영상만' 줬다 → 수치를 주면 좋아지는가/나빠지는가는 미측정",
      "게이팅(품질로 골라 주기)의 인과 효과와 그 대가(과잉 보류)는 임상 순서형 채점에서 측정된 적이 없다",
      ("→ 우리 기여는 새 아이디어가 아니라 '처음 재는 것': 같은 영상·같은 라벨에서 수치 집합만 바꾼 인과 비교", True, GREEN)],
     accent=GREEN, body_size=11.5)
footer(s, "참고: 게이트→VLM 라우팅·selective prediction은 이미 선행(Edges Before Embeddings 등) → 재주장하지 않음")

# ══════════════════════════════════════════════════════════
# S14. 한계와 다음 단계
# ══════════════════════════════════════════════════════════
s = slide_new("한계와 다음 단계", "정직하게: 아직 실증 0건", "LIMITS")
card(s, 0.55, 1.32, 6.05, 3.05, "한계 (지금 시점)",
     ["실증 데이터 0건 — 장애인 0명, 실제 프레임 0장. 모든 '검증'은 문헌+합성 오라클",
      "u(수치의 실제 오차) 미측정 — 치구 실측 또는 B안(비율) 필요",
      "n=20은 큰 효과의 방향 탐색만 가능 (dz 0.66). 소효과 검출 불가",
      "접촉 순간 랜드마크-물체 오류는 기하 검사로 검출 불가 → 검출률 병기"],
     accent=RED, body_size=11.5)
card(s, 6.83, 1.32, 5.92, 3.05, "본평가 전 반드시 처리할 것",
     ["파이프라인이 아직 K1/K2가 아니라 MGA·PV·SPARC·TAM을 넣고 과제도 free/cylinder (D-15)",
      "보조 모델 체크포인트 미확정 (Qwen2.5-VL-72B·InternVL 모두 미설치)",
      "컴퓨트: 2모델 3,216회 출력 필요, 서빙 경로 미설정",
      "치구 135기록 계측 검증 · IRB·동의"],
     accent=AMBER, body_size=11.5)
card(s, 0.55, 4.55, 12.2, 2.1, "요약",
     ["질문은 좁고 명확하다: 수치를 넣으면 좋아지는가, 품질로 골라서 넣으면 대가는 무엇인가",
      "두 과제는 난이도 커버리지가 아니라 '파지 구속이 다를 때 K1의 의미가 유지되는가'를 보기 위한 선택이다",
      ("결론은 아직 없다 — 이 발표는 설계 제안이며, 결과가 아니다.", True, NAVY)],
     accent=NAVY, body_size=12)

prs.save("capstone/손과제_VLM_연구계획_v2.pptx")
print("saved: capstone/손과제_VLM_연구계획_v2.pptx  slides =", len(prs.slides._sldIdLst))
