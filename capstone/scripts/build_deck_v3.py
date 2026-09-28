# -*- coding: utf-8 -*-
"""손과제 VLM 연구계획 발표덱 v3 (2026-09-28).

v2 대비 변경(요청 반영):
  ① 글씨 전체 대폭 확대 — 제목 30pt, 카드제목 17.5pt, 본문 15pt, 표 14pt
  ② 전면 개조식 — '~한다/~이다' 서술어 제거, 명사·화살표 중심
  ③ 글자가 커진 만큼 한 슬라이드당 항목 수·길이 축소, 카드 폭 확대(3열→2열)
유지: 피드백 ① 실험세팅 슬라이드, ② 왜 2개 동작 슬라이드, 사진 자리 + 필요그림 설명
정본: outputs/research-plan-v6.md (v6.3)
출력: capstone/손과제_VLM_연구계획_v3.pptx
"""
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from pptx.oxml.ns import qn

NAVY  = RGBColor(0x14, 0x2A, 0x4C)
INK   = RGBColor(0x1F, 0x2A, 0x37)
MUTED = RGBColor(0x5B, 0x6B, 0x80)
TEAL  = RGBColor(0x0E, 0x83, 0x8A)
AMBER = RGBColor(0xB8, 0x6A, 0x00)
RED   = RGBColor(0xB3, 0x2D, 0x2D)
GREEN = RGBColor(0x1E, 0x7A, 0x46)
BG    = RGBColor(0xF7, 0xF9, 0xFC)
CARD  = RGBColor(0xFF, 0xFF, 0xFF)
EDGE  = RGBColor(0xD3, 0xDC, 0xE6)
LIGHT = RGBColor(0xEC, 0xF2, 0xF7)
PH_F  = RGBColor(0xF1, 0xF4, 0xF8)
PH_E  = RGBColor(0xA9, 0xB6, 0xC6)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
FONT  = "Malgun Gothic"

# ── 글자 크기 (확대) ─────────────────────────────────
T_TITLE, T_SUB = 30, 13.5
T_CARD, T_BODY = 17.5, 15
T_FOOT, T_TAG, T_BADGE = 10.5, 12.5, 20
T_PHT, T_PHB = 12.5, 11
T_TBL = 14

prs = Presentation()
prs.slide_width = Inches(13.3333)
prs.slide_height = Inches(7.5)
BLANK = prs.slide_layouts[6]


def _ea(run, name=FONT):
    rPr = run._r.get_or_add_rPr()
    latin = rPr.find(qn("a:latin")); ea = rPr.find(qn("a:ea"))
    if ea is None:
        ea = rPr.makeelement(qn("a:ea"), {})
        (latin.addnext(ea) if latin is not None else rPr.append(ea))
    ea.set("typeface", name)


def txt(s, l, t, w, h, anchor=MSO_ANCHOR.TOP):
    tb = s.shapes.add_textbox(Inches(l), Inches(t), Inches(w), Inches(h))
    tf = tb.text_frame; tf.word_wrap = True; tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = Inches(0.04)
    tf.margin_top = tf.margin_bottom = Inches(0.02)
    return tf


def para(tf, first, text, size=15, bold=False, color=INK, sb=2, sa=2,
         align=PP_ALIGN.LEFT, line=0.98):
    p = tf.paragraphs[0] if first else tf.add_paragraph()
    p.alignment = align; p.space_before = Pt(sb); p.space_after = Pt(sa); p.line_spacing = line
    r = p.add_run(); r.text = text
    r.font.size = Pt(size); r.font.bold = bold; r.font.color.rgb = color
    r.font.name = FONT; _ea(r)
    return p


def rect(s, l, t, w, h, fill=CARD, line=EDGE, rounded=True, lw=0.75):
    shp = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE if rounded else MSO_SHAPE.RECTANGLE,
                             Inches(l), Inches(t), Inches(w), Inches(h))
    if rounded:
        try: shp.adjustments[0] = 0.05
        except Exception: pass
    if fill is None: shp.fill.background()
    else: shp.fill.solid(); shp.fill.fore_color.rgb = fill
    if line is None: shp.line.fill.background()
    else: shp.line.color.rgb = line; shp.line.width = Pt(lw)
    shp.shadow.inherit = False
    shp.text_frame.word_wrap = True
    return shp


def card(s, l, t, w, h, title, lines, accent=TEAL, fill=CARD,
         ct=T_CARD, bs=T_BODY, pad=0.15):
    rect(s, l, t, w, h, fill=fill)
    rect(s, l, t + 0.09, 0.055, h - 0.18, fill=accent, line=None, rounded=False)
    tf = txt(s, l + pad + 0.05, t + 0.06, w - 2 * pad - 0.05, h - 0.12)
    para(tf, True, title, size=ct, bold=True, color=NAVY, sa=4, line=1.0)
    for ln in lines:
        if isinstance(ln, tuple):
            para(tf, False, ln[0], size=bs, bold=ln[1], color=ln[2])
        else:
            para(tf, False, ln, size=bs, color=INK)
    return tf


def photo(s, l, t, w, h, title, bullets):
    shp = rect(s, l, t, w, h, fill=PH_F, line=PH_E, lw=1.0)
    try:
        from pptx.enum.dml import MSO_LINE_DASH_STYLE
        shp.line.dash_style = MSO_LINE_DASH_STYLE.DASH
    except Exception:
        pass
    tf = shp.text_frame; tf.word_wrap = True; tf.vertical_anchor = MSO_ANCHOR.TOP
    para(tf, True, "[ 사진 자리 ]  " + title, size=T_PHT, bold=True,
         color=RGBColor(0x47, 0x55, 0x69), sa=3)
    for b in bullets:
        para(tf, False, "· " + b, size=T_PHB, color=MUTED, line=1.02)
    para(tf, False, "※ 이 칸에 사진/도면 넣기", size=T_PHB - 0.5, color=PH_E)
    return shp


N = {"i": 0}


def new(title, subtitle=None, tag=None):
    s = prs.slides.add_slide(BLANK); N["i"] += 1
    rect(s, 0, 0, 13.3333, 7.5, fill=BG, line=None, rounded=False)
    rect(s, 0, 0, 13.3333, 0.14, fill=NAVY, line=None, rounded=False)
    b = rect(s, 0.5, 0.40, 0.66, 0.66, fill=NAVY, line=None)
    bt = b.text_frame; bt.vertical_anchor = MSO_ANCHOR.MIDDLE
    para(bt, True, "%02d" % N["i"], size=T_BADGE, bold=True, color=WHITE,
         align=PP_ALIGN.CENTER, sb=0, sa=0)
    def _w(t, sz): return sum(1.0 if ord(c) > 0x1100 else 0.55 for c in t) * sz * 0.98
    tsz = T_TITLE
    while tsz > 20 and _w(title, tsz) > 540: tsz -= 1
    tf = txt(s, 1.30, 0.30, 8.05, 0.97, anchor=MSO_ANCHOR.MIDDLE)
    para(tf, True, title, size=tsz, bold=True, color=NAVY, sa=0, line=1.0)
    if subtitle:
        para(tf, False, subtitle, size=T_SUB, color=MUTED, sb=2)
    if tag:
        tt = txt(s, 9.5, 0.42, 3.35, 0.6, anchor=MSO_ANCHOR.MIDDLE)
        para(tt, True, tag, size=T_TAG, bold=True, color=TEAL, align=PP_ALIGN.RIGHT)
    return s


def foot(s, note):
    para(txt(s, 0.52, 6.98, 12.3, 0.40), True, note, size=T_FOOT, color=MUTED)


# ══════════ S1 표지 ══════════
s = prs.slides.add_slide(BLANK)
rect(s, 0, 0, 13.3333, 7.5, fill=NAVY, line=None, rounded=False)
rect(s, 0, 0, 13.3333, 0.18, fill=TEAL, line=None, rounded=False)
rect(s, 0.9, 2.00, 1.6, 0.09, fill=TEAL, line=None, rounded=False)
tf = txt(s, 0.9, 2.22, 11.6, 2.4)
para(tf, True, "수치를 넣으면 VLM 채점이 좋아지는가,", size=36, bold=True, color=WHITE, sa=3, line=1.0)
para(tf, False, "아니면 나빠지는가", size=36, bold=True, color=WHITE, sa=14, line=1.0)
para(tf, False, "ARAT 두 항목 · 품질 기반 수치 선별의 효과", size=17, color=RGBColor(0xA8,0xC6,0xD8))
tf2 = txt(s, 0.9, 5.25, 11.6, 1.0)
para(tf2, True, "이재용  22000561  |  한동대학교 기계제어공학부", size=15, color=WHITE, sa=5)
para(tf2, False, "연구계획 발표 · 2026-09-28 · 설계 정본 v6.3", size=13.5, color=RGBColor(0x8F,0xA8,0xBE))
para(txt(s, 0.9, 6.42, 11.6, 0.5), True,
     "※ 모든 수치 = 계획값. 본평가 결과 아님 (실증 데이터 수집 전).",
     size=12, color=RGBColor(0xD9,0xB0,0x6B))

# ══════════ S2 한 장 요약 ══════════
s = new("이 연구는 무엇을 하는가", "질문 · 개입 · 대상 · 결과 한 장 요약", "SUMMARY")
card(s, 0.5, 1.30, 6.05, 2.55, "연구 질문",
     ["① 수치 주입 → 채점 개선? 악화?",
      "② 품질 선별 → 악화 완화?",
      "③ 대가 = 과잉 보류?"], accent=TEAL)
card(s, 6.78, 1.30, 6.05, 2.55, "개입",
     ["같은 영상 · 같은 사람 · 같은 시행",
      "바꾸는 것 = 수치의 양 · 품질",
      "A1 없음 · A2 전체 · A3 선별 · R 무작위"], accent=AMBER)
card(s, 0.5, 4.00, 6.05, 2.90, "대상 · 규모",
     ["뇌졸중 23명 (개발 3 + 본 20)",
      "비장애인 22명 (개발 6 + 검증 16)",
      "20명 × 2과제 × 3시행 = 120영상",
      "독립 분석 단위 = 사람 20명"], accent=TEAL)
card(s, 6.78, 4.00, 6.05, 2.90, "주 결과 3개 (Holm k=3)",
     ["PR-1  MAE(A2)−MAE(A1)  수치 주입",
      "PR-2  MAE(A2)−MAE(A3)  게이팅",
      "PR-3  MAE(R)−MAE(A3)   고유 가치",
      ("부호 + = 나쁜 방향", True, AMBER)], accent=NAVY)
foot(s, "정본: outputs/research-plan-v6.md (v6.3, 2026-09-28)")

# ══════════ S3 문제 ══════════
s = new("왜 필요한가 — 임상 평가 한계 + VLM 실패", "두 문제의 동시 존재", "BACKGROUND")
card(s, 0.5, 1.30, 6.05, 5.55, "문제 ①  임상 평가 한계",
     ["평가자 주관성 — 갈리는 항목 4/33",
      "천장·바닥 — 바닥 38% · 천장 21%",
      "긴 소요 시간",
      "점수는 정확 · 수치는 오류 (손목 96 mm)",
      ("→ 점수로 안 보이는 보상 전략 존재", True, AMBER),
      "",
      "근거: Hernández 2019 · Kristersson 2019",
      "Li 2022 · Padilla-Magaña 2022"],
     accent=AMBER)
card(s, 6.78, 1.30, 6.05, 5.55, "문제 ②  VLM 단독 채점 실패",
     ["Li 2026 — 비장애 20 + 뇌졸중 51",
      "Qwen2.5-VL-72B · 영상 + 지침만",
      ("→ FMA 총점 = 중증도 무관 '평탄'", True, RED),
      ("→ '무조건 1점' 기준선과 유사", True, RED),
      "정밀 운동 이해 부족",
      "",
      "우리 VLM = Li 2026과 동일 모델",
      "PMID 42406872 · PLOS Digit Health"],
     accent=RED)
foot(s, "핵심: 점수로는 안 보이고, 영상만으로는 못 잡는다 → '수치를 어떻게 넣을 것인가'가 남는다")

# ══════════ S4 연구 질문 ══════════
s = new("연구 질문 — '다' 줄까, '골라서' 줄까", "정보를 더 주는 것이 항상 이롭지 않다는 근거에서 출발", "QUESTION")
card(s, 0.5, 1.30, 12.33, 1.55, "한 문장 질문",
     [("수치를 주면 채점이 좋아지는가, 나빠지는가 —품질로 골라 주면 줄어드는가, 대가는 과잉 보류인가?",
       True, INK)], accent=TEAL, ct=16, bs=16)
card(s, 0.5, 3.00, 3.95, 3.85, "① 수치 주입 위험",
     ["Tang 2025 — 예시 3개 최적",
      "4개에서 붕괴 (0.42)",
      "→ 정보 ↑ = 모델 악화 가능",
      "Li 2026은 영상만 = 미측정"], accent=RED, ct=16, bs=14)
card(s, 4.68, 3.00, 3.95, 3.85, "② 품질 선별 필요",
     ["RGB-D — 가림·깊이 오류",
      "틀린 수치 → 조용히 전파",
      "→ 관측 가능성 Q로 선별",
      "보류한 수치는 null 처리"], accent=TEAL, ct=16, bs=14)
card(s, 8.87, 3.00, 3.96, 3.85, "③ 무작위 제외 비교",
     ["선별 이득 = '덜 봐서'?",
      "같은 양 무작위 제거 R",
      "→ 품질 규칙 고유 기여 분리",
      "정보량 교란 통제"], accent=NAVY, ct=16, bs=14)
foot(s, "탐색적(보정 없음): A0 · A0-time · A4 · 오류주입(bias/burst) 기전 — 주 비교 아님")

# ══════════ S5 실험 세팅 (피드백 ①) ══════════
s = new("실험 세팅 — 환경과 기록", "피드백 반영 ①", "SETUP")
card(s, 0.5, 1.30, 6.05, 2.75, "장비 · 저장",
     ["D455 1대 (단일 RGB-D)",
      "RGB 1280×800 · depth 1280×720",
      "실측 16.9 · 24.6 fps (dt 불규칙)",
      "작업거리 0.65–0.85 m · 아래 30–45°",
      "저장 L0→L3 · 원시 depth 필수"], accent=TEAL)
card(s, 6.78, 1.30, 6.05, 2.75, "환경 · 대상 · 절차",
     ["테이블 75 · 의자 46(팔걸이 없음) · 선반 37 cm",
      "뇌졸중 23(3+20) · 비장애인 22(6+16)",
      "연습 2회 → 본 첫 3회 고정",
      "T1 → 휴식 → T2 · 시행 즉시 채점"], accent=TEAL)
photo(s, 0.5, 4.20, 12.33, 2.65, "실험 세팅 전경",
      ["카메라(D455)+삼각대 위치 · 작업거리 0.65–0.85 m",
       "테이블 75 cm + 선반 37 cm + 팔걸이 없는 의자",
       "환측 손 + 블록/구슬/뚜껑이 함께 보이는 구도",
       "측면 30–45° 시점 1장 + 위에서 본 배치 도면 1장"])
foot(s, "ARAT 표준 물성·배치: Yozbatiran et al. 2008 (doi 10.1177/1545968307305353) · Lyle 1981 원형")

# ══════════ S6 왜 2개 동작 (피드백 ②) ══════════
s = new("왜 이 2개 동작인가", "피드백 반영 ② — '가장 어려운 것 하나면 되지 않나?'", "RATIONALE")
card(s, 0.5, 1.28, 12.33, 0.90, "전제",
     [("ARAT 건너뛰기 규칙 = '가장 어려운 것 통과 → 아래 만점' —단, 하위검사(subtest) 내부 전용 (Lyle 1981)",
       True, INK)], accent=AMBER, ct=15, bs=15)
card(s, 0.5, 2.30, 6.05, 2.45, "① 규칙은 하위검사 내부 전용",
     ["Grasp·Grip·Pinch·Gross 각각 별도",
      "\"top marks for that subtest\"",
      "T1 = ARAT 3번 = Grasp",
      "T2 = ARAT 12번 = Pinch",
      ("→ 다른 하위검사 = 중복 아님", True, GREEN)],
     accent=TEAL, ct=16.5, bs=14)
card(s, 6.78, 2.30, 6.05, 2.45, "② 위계 자체가 불완전",
     ["Koh 2006 (n=351) — 유일한 위계 위반",
      ("   = pinch 항목", True, RED),
      "van der Lee 2002 — 15/19만 위계",
      "소척도 구조 = 경험적 지지 없음",
      ("→ '하나면 나머지 자동' 불성립", True, RED)],
     accent=RED, ct=16.5, bs=14)
card(s, 0.5, 4.90, 12.33, 1.95, "③ 목적은 '총점 추정'이 아니다",
     ["Koh 2006 — ARAT 원점수 = 순서 정보만 제공",
      "T2(구슬 · 엄지+검지 패드 강제) → K1 의미 성립 = 주 결과",
      "T1(블록 · 파지 자유) → K1 의미 애매 = 참고용",
      ("→ 2개 = 난이도 커버리지가 아니라 '파지 구속(grasp constraint) 대비'", True, GREEN)],
     accent=NAVY, ct=16.5, bs=14.5)
foot(s, "Koh 2006: PMID 17067971 · van der Lee 2002: Clin Rehabil 16(6):646-653 (doi 10.1191/0269215502cr534oa)")

# ══════════ S7 두 과제 ══════════
s = new("두 과제의 물성과 배치", "ARAT 표준 (Yozbatiran 2008)", "TASKS")
card(s, 0.5, 1.30, 6.05, 2.75, "T2 · 주 결과  (ARAT 12번)",
     ["소척도 = Pinch",
      "구슬 1.5 cm · 5.4 g",
      "엄지 + 검지 '패드' 강제",
      "하부 뚜껑 → 선반 상부 뚜껑",
      "3점 = 5초 이내 + 패드"], accent=GREEN)
card(s, 6.78, 1.30, 6.05, 2.75, "T1 · 참고  (ARAT 3번)",
     ["소척도 = Grasp",
      "블록 5 cm · 55 g",
      "opposition이면 파지 자유",
      "테이블 → 선반 37 cm",
      "3점 = 5초 이내 정상"], accent=AMBER)
photo(s, 0.5, 4.20, 6.05, 2.65, "T1 · T2 물체와 배치",
      ["5 cm 블록(55 g) vs 구슬(1.5 cm, 5.4 g) 실물 비교",
       "선반 37 cm 위 뚜껑에 구슬 놓는 장면",
       "배치 도면: 물체 위치 · 뚜껑 2개 · 선반 높이"])
card(s, 6.78, 4.20, 6.05, 2.65, "채점 · 차이",
     ["0 못함 / 1 부분 / 2 완료 / 3 정상",
      "무게 10배 · 크기 3.3배 차이",
      "구슬(12번) = 두 번째 난이도군",
      ("핵심 = 37 cm 수직 들어올리기", True, AMBER),
      ("→ 카메라 수직 시야 필요", True, AMBER),
      ("합계 0–6점 = 임상점수 아님", True, RED)], accent=NAVY, ct=16, bs=14.5)
foot(s, "출처: rgbd-grasp-vlm-protocol-analysis.md §0-1 (ARAT 19개 항목 물성표)")

# ══════════ S8 K1 · K2 ══════════
s = new("VLM에 넣는 두 수치 — K1 · K2", "계산은 원본 프레임(L1)에서만 · VLM 프레임에서 재계산 금지", "FEATURES")
card(s, 0.5, 1.30, 6.05, 2.35, "K1 — 엄지–검지 표면점 거리 (mm)",
     ["MediaPipe 4번(엄지끝) · 8번(검지끝) 표면점 3D 거리",
      "관찰 구간 P95 (95백분위수)",
      ("금지: PAp · 최대 벌림 · 관절 중심 거리", True, RED)], accent=TEAL)
card(s, 6.78, 1.30, 6.05, 2.35, "K2 — 손목 표면점 속도 (mm/s)",
     ["MediaPipe 0번(손목) 표면점 3D 속도 P95",
      "dt = 장치/프레임 타임스탬프만 (벽시계 금지)",
      ("금지: 손가락 민첩성 · 신경 회복량", True, RED)], accent=TEAL)
card(s, 0.5, 3.80, 6.05, 3.05, "계산 6단계",
     ["① 5×5 depth 중앙값 · 유효 ≥50%",
      "② 역투영 → 3D 좌표",
      "③ 손-일관성 3D 거리 ∈ [60, 230] mm",
      "④ K1 = 4–8번 거리 P95",
      "⑤ K2 = 0번 속도 P95 · dt 하한",
      "⑥ 검출 실패 = 하드 결측 (보간 금지)"], accent=NAVY, bs=14.5)
photo(s, 6.78, 3.80, 6.05, 3.05, "K1·K2 개념도",
      ["MediaPipe 21점에 4·8번(빨강) · 0번(파랑) 표시",
       "K1 = 엄지–검지 거리 화살표 · K2 = 손목 속도 벡터",
       "가림 시 랜드마크가 배경에 찍힌 '오염' vs 정상 예시",
       "③ 손-일관성 검사 OFF면 K1 오염 110배 — 대비 그림"])
foot(s, "P95는 '표면점 대리값' · 해부학적 관절 중심 거리 아님 (research-plan-v6.md §5)")

# ══════════ S9 Q 규칙 ══════════
s = new("품질 선별 규칙 Q — '믿을 만한 수치인가'", "카메라 1대로 정확도는 알 수 없다 → 관측 가능성을 잰다", "QUALITY")
card(s, 0.5, 1.30, 7.55, 3.30, "규칙 5개 (본평가 전 동결)",
     ["Q1  깊이 유효 비율        — 개발 자료에서 확정",
      "Q2  최장 연속 결측        — > 0.3초",
      "Q3  유효 표본 수          — < 50",
      "Q4  깊이 경계 혼합        — > 50%",
      "Q5  손가락·손목 가림      — 2인 판정, > 50%",
      ("걸린 K1·K2 = null 보류 · 다른 유효 수치는 그대로", True, GREEN),
      ("임계값은 치료사 점수 보지 않고 고정", True, RED)],
     accent=TEAL, bs=14.5)
photo(s, 8.33, 1.30, 4.50, 3.30, "Q 판정 예시",
      ["정상 프레임 vs 가림 프레임 (RGB)",
       "depth 유효 마스크가 뚫린(결측) 예시",
       "랜드마크가 물체 경계에 걸린 '경계 혼합' 예시"])
card(s, 0.5, 4.75, 12.33, 2.05, "R (무작위 제외) 조건 · 한계",
     ["R = A3와 '같은 수'를 품질 무관하게 무작위 제거 (지표별 매칭 · 시드 3개)",
      "원래 불가능한 하드 결측 = 모든 조건 유지 (R에서도 복원 금지)",
      ("지표별 제외율 > 50% → 그 지표의 R 비교 제한", True, AMBER)],
     accent=NAVY, bs=15)
foot(s, "Q는 '교정된 mm 오차 확률'도, 환자의 중증도도 아니다 (research-plan-v6.md §5.2 · §12)")

# ══════════ S10 조건표 ══════════
s = new("실험 조건과 세 가지 비교", "같은 영상·사람·시행에서 수치의 양과 품질만 변경", "DESIGN")
rows = [("A1", "영상 기준", "K1·K2 미제공", "영상만 기준선"),
        ("A2", "전체 제공", "계산 가능 수치 전부", "A2 vs A1 → 수치 주입 (PR-1)"),
        ("A3", "품질 선별", "Q 통과 수치만", "A2 vs A3 → 게이팅 (PR-2)"),
        ("R", "무작위 제외", "A3와 같은 수 무작위", "R vs A3 → 고유 가치 (PR-3)")]
tb = s.shapes.add_table(5, 4, Inches(0.5), Inches(1.32), Inches(12.33), Inches(2.55)).table
for j, wd in enumerate([Inches(1.0), Inches(2.1), Inches(4.03), Inches(5.2)]):
    tb.columns[j].width = wd
for j, h in enumerate(["조건", "이름", "VLM에 넣는 수치", "비교 목적"]):
    c = tb.cell(0, j); c.text = ""
    r = c.text_frame.paragraphs[0].add_run(); r.text = h
    r.font.size = Pt(T_TBL); r.font.bold = True; r.font.color.rgb = WHITE
    r.font.name = FONT; _ea(r)
    c.fill.solid(); c.fill.fore_color.rgb = NAVY
    c.vertical_anchor = MSO_ANCHOR.MIDDLE
for i, row in enumerate(rows, 1):
    for j, v in enumerate(row):
        c = tb.cell(i, j); c.text = ""
        r = c.text_frame.paragraphs[0].add_run(); r.text = v
        r.font.size = Pt(T_TBL); r.font.name = FONT; _ea(r)
        r.font.bold = (j == 0); r.font.color.rgb = NAVY if j == 0 else INK
        c.fill.solid(); c.fill.fore_color.rgb = CARD if i % 2 else LIGHT
        c.vertical_anchor = MSO_ANCHOR.MIDDLE
card(s, 0.5, 4.05, 6.05, 2.75, "1급 기술 결과 (검정 아님 · 반드시 보고)",
     ["보류율(A3) = Q가 버린 시행 비율",
      "(보류율, MAE) Pareto 곡선 (Q1 sweep)",
      "보조 모델 부호 일치 여부",
      ("→ 이득이 '좁은 구간'일 수 있음을 숨기지 않음", True, AMBER)],
     accent=AMBER, ct=16, bs=14)
card(s, 6.78, 4.05, 6.05, 2.75, "탐색적 (보정 없음 · CI·효과크기만)",
     ["A4 — 수치만 주고 RGB 제거",
      "A0 · A0-time — 경량모형 · 시간 단서",
      "오류 주입 bias 1u/3u · burst 3u (H5)",
      "큰 오차(≥2점) 비율 · 설명 평가"],
     accent=MUTED, ct=16, bs=14)
foot(s, "동결: 모델 버전 · 프롬프트 · 프레임 추출 · Q 임계값 · R 배정 방식 — 본평가 전 고정")

# ══════════ S11 VLM · 프레임 ══════════
s = new("고정 VLM과 입력 프레임", "추가 학습 없이 동일 모델·동일 프롬프트 · 조건별 차이는 수치뿐", "MODEL")
card(s, 0.5, 1.30, 6.05, 2.55, "주 모델 · 보조 모델",
     ["주 = Qwen2.5-VL-72B-Instruct",
      "Li 2026과 동일 → 직접 비교",
      "보조 = 부호 일치 확인 (검정 아님)",
      ("보조 체크포인트 미확정", True, AMBER)], accent=TEAL, bs=14.5)
card(s, 6.78, 1.30, 6.05, 2.55, "출력 · 실패 처리",
     ["0-shot · greedy · 추가학습 없음",
      "출력 = 0–3점 한 줄 + 근거 ≤2문장",
      "실패 1회 재시도 · 실패 제거 안 함",
      "손실 = 3 대체 → 실패포함 손실 + 성공률"], accent=RED, bs=14.5)
photo(s, 0.5, 4.00, 6.05, 2.85, "프레임 샘플링 타임라인",
      ["타임라인: 0–5초 = 10 Hz (약 50프레임)",
       "5초 이후 = 2 Hz · 전체 상한 64프레임",
       "640×480 리사이즈 표시",
       "실측 fps 16.9/24.6 → 10 Hz 목표가 ~8.5 Hz로 저하 (각주)"])
card(s, 6.78, 4.00, 6.05, 2.85, "프레임 규칙 (동결)",
     ["앞 5.0초 = 10 Hz 목표 (약 50프레임)",
      "5초 초과분 = 2 Hz · 상한 64",
      "해상도 640×480",
      "사건 구간 사람이 고르지 않음",
      ("실제 fps로 인덱스 계산 (30 fps 가정 금지)", True, AMBER)],
     accent=NAVY, ct=16, bs=14)
foot(s, "프롬프트 = 모든 조건 동일 템플릿 · 조건명을 프롬프트에 쓰지 않음")

# ══════════ S12 분석 · 판정 ══════════
s = new("분석 방법과 판정 기준", "사람 단위 짝지은 비교 · 사람 단위 bootstrap", "ANALYSIS")
card(s, 0.5, 1.30, 6.05, 2.45, "분석 설계",
     ["분석 단위 = 사람 20명 (반복 관측)",
      "PR-1 = MAE(A2) − MAE(A1)",
      "PR-2 = MAE(A2) − MAE(A3)",
      "PR-3 = MAE(R) − MAE(A3)",
      "bootstrap 10,000 · 95% CI · Holm k=3"], accent=TEAL, bs=14.5)
card(s, 6.78, 1.30, 6.05, 2.45, "부호 읽기 (양수 = )",
     ["PR-1 + → 전체 제공 악화",
      "PR-2 + → 선별 제공 개선",
      "PR-3 + → Q가 무작위보다 우수",
      ("유의성 하나로 결론 금지", True, AMBER),
      ("CI 0 포함 = 방향 미확인 (동등 아님)", True, AMBER)], accent=NAVY, bs=14.5)
card(s, 0.5, 3.92, 12.33, 2.90, "예상 패턴과 해석 (사전 등록)",
     ["A2 악화 · A3 개선            → 일부 수치 보류 가치",
      "A3 > R                        → 품질 규칙 자체가 기여",
      "A2·A3 비슷하게 개선          → 수치 주입 효과 · 선별 이득 작음",
      "차이 작거나 불명확            → 효과크기·CI로 판단",
      ("보류율 ↑ + PR-2 유의          → 이득이 좁은 구간 (보류–정확도 절충)", True, AMBER),
      ("보류율 ↑ + PR-2 비유의        → 과잉 보류가 대가만 남김", True, RED)],
     accent=NAVY, ct=16, bs=14)
foot(s, "실패 출력 = 유효 MAE에서 제외 · '실패포함 손실(손실=3)' 별도 열 보고")

# ══════════ S13 선행연구 · 우리 자리 ══════════
s = new("선행연구가 밝힌 것 vs 우리가 처음 재는 것", "주장 = '처음 제안'이 아니라 '처음 측정'", "EVIDENCE")
card(s, 0.5, 1.30, 6.05, 2.65, "VLM · 센서 채점",
     ["Li 2022 — 20명 · r=.981 · 손목 96 mm 오차",
      "Li 2026 — 51명 · 영상만 → 총점 평탄",
      "Tang 2025 — 특징 주입 · 3개 최적"], accent=TEAL, ct=16, bs=14)
card(s, 6.78, 1.30, 6.05, 2.65, "ARAT 척도 구조",
     ["Koh 2006 — 유일 위계 위반 = pinch",
      "van der Lee 2002 — 15/19만 위계",
      "Rodgers 2022 — N=1425 · 단축 시도"], accent=AMBER, ct=16, bs=14)
card(s, 0.5, 4.10, 6.05, 2.70, "이미 선행 (재주장 금지)",
     ["ARAT 손 운동학 측정 (Padilla-Magaña 2022)",
      "RGB-D 자동채점 — 임상검증까지 완료",
      "JSON·특징 주입 · 품질 게이트 → 라우팅",
      ("→ '새롭다'고 주장하지 않음", True, RED)], accent=RED, ct=16, bs=14)
card(s, 6.78, 4.10, 6.05, 2.70, "우리 자리 (빈칸)",
     ["Li 2026 = 영상만 → 수치 주입 미측정",
      "게이팅 인과효과 · 대가 미측정",
      ("→ 기여 = 같은 영상·라벨에서 수치 집합만 바꾼 인과 비교", True, GREEN)],
     accent=GREEN, ct=16, bs=14)
foot(s, "게이트→VLM 라우팅 · selective prediction은 이미 선행 → 재주장하지 않음")

# ══════════ S14 한계 · 다음 ══════════
s = new("한계와 다음 단계", "정직하게 — 아직 실증 0건", "LIMITS")
card(s, 0.5, 1.30, 6.05, 2.85, "한계 (현재)",
     ["실증 데이터 0건 (장애인 0명 · 프레임 0장)",
      "u(수치 실제 오차) 미측정",
      "n=20 → 큰 효과 방향만 (dz 0.66)",
      "접촉 순간 랜드마크-물체 오류 = 기하 검출 불가"],
     accent=RED, ct=16, bs=14)
card(s, 6.78, 1.30, 6.05, 2.85, "본평가 전 처리",
     ["파이프라인 D-15 정렬 (K1/K2 vs MGA·PV)",
      "보조 모델 체크포인트 확정",
      "컴퓨트 3,216회 출력 · 서빙 미설정",
      "치구 135기록 · IRB"],
     accent=AMBER, ct=16, bs=14)
card(s, 0.5, 4.30, 12.33, 2.50, "요약",
     ["질문 = 수치 주입 효과 + 품질 선별의 대가",
      "두 항목 = 난이도가 아니라 '파지 구속 대비'",
      ("결론 없음 — 이 발표는 설계 제안이며 결과가 아니다", True, NAVY)],
     accent=NAVY, ct=16, bs=15.5)

prs.save("capstone/손과제_VLM_연구계획_v3.pptx")
print("saved v3, slides =", len(prs.slides._sldIdLst))
