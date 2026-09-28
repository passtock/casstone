# -*- coding: utf-8 -*-
"""손과제 VLM 연구계획 발표덱 v4 (2026-09-28).

v3 피드백 반영:
  ① 원본(0928) 덱의 레이아웃 언어를 그대로 사용
     - 흰 배경 + 상단 193A66 띠 + 우상단 페이지번호(9AA6B4)
     - 2x2 카드 격자(L 0.42/6.79, T 1.35/4.15, W 6.12 H 2.60) + 컬러 헤더 띠(H0.46, 18~19pt 흰 글씨)
     - 카드 좌측 본문 + 우측 사진 자리(W2.00 H1.74, 테두리 94A3B8)
     - 하단 193A66 결론 바
  ② 개조식 = 보고서체 명사 종결('~확인/~존재/~필요/~미측정/~아님/~제한/~고정' 등)
  ③ 핵심만 — 카드당 4~5줄, 줄당 ≤18자
출력: capstone/손과제_VLM_연구계획_v4.pptx
"""
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from pptx.oxml.ns import qn

NAVY  = RGBColor(0x19, 0x3A, 0x66)
TEAL  = RGBColor(0x08, 0x7F, 0x8C)
TEAL2 = RGBColor(0x16, 0xA7, 0xB8)
GREEN = RGBColor(0x17, 0x82, 0x68)
AMBER = RGBColor(0xB8, 0x6A, 0x00)
RED   = RGBColor(0xB3, 0x2D, 0x2D)
BORD  = RGBColor(0xCB, 0xD6, 0xE1)
PHB   = RGBColor(0x94, 0xA3, 0xB8)
PGN   = RGBColor(0x9A, 0xA6, 0xB4)
INK   = RGBColor(0x11, 0x11, 0x11)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
GRAY  = RGBColor(0x6B, 0x74, 0x82)
FONT  = "Malgun Gothic"

T_TITLE, T_SUB = 26, 16
T_HDR, T_BODY, T_PGN = 19, 14.5, 16
T_BAR = 15
prs = Presentation(); prs.slide_width = Inches(13.3333); prs.slide_height = Inches(7.5)
BLANK = prs.slide_layouts[6]


def _ea(run, name=FONT):
    rPr = run._r.get_or_add_rPr(); latin = rPr.find(qn("a:latin")); ea = rPr.find(qn("a:ea"))
    if ea is None:
        ea = rPr.makeelement(qn("a:ea"), {})
        (latin.addnext(ea) if latin is not None else rPr.append(ea))
    ea.set("typeface", name)


def tb(s, l, t, w, h, anchor=MSO_ANCHOR.TOP):
    x = s.shapes.add_textbox(Inches(l), Inches(t), Inches(w), Inches(h))
    tf = x.text_frame; tf.word_wrap = True; tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = Inches(0.03)
    tf.margin_top = tf.margin_bottom = Inches(0.01)
    return tf


def P(tf, first, text, sz=T_BODY, bold=False, color=INK, sa=3, sb=0, line=1.0, align=PP_ALIGN.LEFT):
    p = tf.paragraphs[0] if first else tf.add_paragraph()
    p.alignment = align; p.space_after = Pt(sa); p.space_before = Pt(sb); p.line_spacing = line
    r = p.add_run(); r.text = text
    r.font.size = Pt(sz); r.font.bold = bold; r.font.color.rgb = color; r.font.name = FONT; _ea(r)
    return p


def rrect(s, l, t, w, h, fill=None, line=BORD, lw=0.75, rounded=True):
    sh = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE if rounded else MSO_SHAPE.RECTANGLE,
                            Inches(l), Inches(t), Inches(w), Inches(h))
    if fill is None: sh.fill.background()
    else: sh.fill.solid(); sh.fill.fore_color.rgb = fill
    if line is None: sh.line.fill.background()
    else: sh.line.color.rgb = line; sh.line.width = Pt(lw)
    sh.shadow.inherit = False
    return sh


def page(s, num, title, sub=None):
    rrect(s, 0, 0, 13.3333, 0.14, fill=NAVY, line=NAVY, rounded=False)
    P(tb(s, 12.11, 0.36, 0.60, 0.30, MSO_ANCHOR.MIDDLE), True, "%02d" % num,
      sz=T_PGN, bold=True, color=PGN, align=PP_ALIGN.CENTER)
    P(tb(s, 0.62, 0.40, 11.30, 0.50, MSO_ANCHOR.MIDDLE), True, title, sz=T_TITLE, bold=True, color=INK)
    if sub:
        P(tb(s, 0.62, 0.90, 11.95, 0.34), True, sub, sz=T_SUB, color=INK)


def card(s, l, t, w, h, title, lines, accent=NAVY, hs=0.46, body_w=None,
         sz=T_BODY, photo=None, ct=T_HDR):
    rrect(s, l, t, w, h, fill=WHITE, line=BORD)
    rrect(s, l, t, w, hs, fill=accent, line=accent)
    P(tb(s, l + 0.14, t + 0.07, w - 0.28, hs - 0.10, MSO_ANCHOR.MIDDLE), True, title,
      sz=ct, bold=True, color=WHITE)
    bw = body_w if body_w else (w - 0.28)
    if photo and body_w is None:
        bw = w - 2.42
    if lines:
        tf = tb(s, l + 0.14, t + hs + 0.10, bw, max(0.30, h - hs - 0.20))
        for i, ln in enumerate(lines):
            if isinstance(ln, tuple):
                P(tf, i == 0, ln[0], sz=sz, bold=ln[1], color=ln[2])
            else:
                P(tf, i == 0, ln, sz=sz, color=INK)
    if photo:
        ph = rrect(s, l + w - 2.14, t + hs + 0.20, 2.00, h - hs - 0.40, fill=None, line=PHB, lw=1.0, rounded=False)
        ptf = ph.text_frame; ptf.word_wrap = True; ptf.vertical_anchor = MSO_ANCHOR.MIDDLE
        P(ptf, True, "[사진 자리]", sz=11, bold=True, color=PHB, align=PP_ALIGN.CENTER, sa=2)
        P(ptf, False, photo, sz=10.5, color=PHB, align=PP_ALIGN.CENTER, line=1.02)


def bar(s, t, text, fill=NAVY, sz=T_BAR, h=0.57, color=WHITE):
    rrect(s, 0.62, t, 12.08, h, fill=fill, line=fill, rounded=False)
    P(tb(s, 0.81, t + 0.08, 11.71, h - 0.14, MSO_ANCHOR.MIDDLE), True, text, sz=sz, bold=False, color=color)


def table(s, l, t, w, h, data, widths, sz=15):
    n_r, n_c = len(data), len(data[0])
    gt = s.shapes.add_table(n_r, n_c, Inches(l), Inches(t), Inches(w), Inches(h)).table
    for j, wd in enumerate(widths): gt.columns[j].width = Inches(wd)
    for i, row in enumerate(data):
        for j, v in enumerate(row):
            c = gt.cell(i, j); c.text = ""
            para = c.text_frame.paragraphs[0]
            r = para.add_run(); r.text = v
            r.font.size = Pt(sz); r.font.name = FONT; _ea(r)
            r.font.bold = (i == 0)
            r.font.color.rgb = WHITE if i == 0 else INK
            c.fill.solid(); c.fill.fore_color.rgb = NAVY if i == 0 else WHITE
            c.vertical_anchor = MSO_ANCHOR.MIDDLE
            c.margin_left = c.margin_right = Inches(0.09)
            c.margin_top = c.margin_bottom = Inches(0.02)
    return gt


X1, X2 = 0.42, 6.79           # 좌/우 카드 L
R1, R2, CH = 1.35, 4.15, 2.60  # 카드 행 T, 카드 높이
CW = 6.12                      # 카드 폭

# ══════════════════ S1 표지 (원본 분할 레이아웃) ══════════════════
s = prs.slides.add_slide(BLANK)
rrect(s, 0, 0, 13.3333, 7.5, fill=WHITE, line=WHITE, rounded=False)
rrect(s, 0, 0, 13.3333, 0.14, fill=NAVY, line=NAVY, rounded=False)
rrect(s, 0, 0, 3.00, 7.5, fill=NAVY, line=NAVY, rounded=False)
rrect(s, 3.00, 0, 0.12, 7.5, fill=TEAL2, line=TEAL2, rounded=False)
P(tb(s, 12.15, 0.38, 0.55, 0.28), True, "01", sz=T_PGN, bold=True, color=PGN, align=PP_ALIGN.CENTER)
P(tb(s, 3.54, 1.40, 9.20, 1.45), True,
  "수치 추가와 선별 제공이\n손 기능 VLM 채점에 미치는 영향", sz=33, bold=True, color=INK, line=1.08)
P(tb(s, 3.57, 3.02, 8.90, 0.52), True,
  "ARAT 두 항목 · 품질 기반 수치 선별 연구계획", sz=18, color=INK, sa=6)
P(tb(s, 3.57, 3.66, 8.90, 0.90), True,
  "설계 정본 v6.3 (2026-09-28) · 모든 수치는 계획값\n본평가 결과 아님 (실증 데이터 수집 전)", sz=12.5, color=GRAY, line=1.15)
P(tb(s, 3.58, 6.25, 9.0, 0.30), True,
  "연구계획 발표  |  이재용 22000561  |  한동대학교 기계제어공학부", sz=13, color=INK)

# ══════════════════ S2 목차 ══════════════════
s = prs.slides.add_slide(BLANK)
rrect(s, 0, 0, 13.3333, 7.5, fill=WHITE, line=WHITE, rounded=False)
page(s, 2, "목차")
items = ["1. 기존 자동채점 접근과 남는 문제",
         "2. 선행연구 근거와 연구 공백",
         "3. 실험 세팅 — 환경·대상·절차",
         "4. 두 과제 선정 근거 (ARAT 위계 질문)",
         "5. 수치 K1·K2와 품질 선별 규칙 Q",
         "6. 조건 설계와 VLM 모델 로스터",
         "7. 분석 계획과 한계"]
tf = tb(s, 1.30, 1.80, 10.5, 4.6)
for i, it in enumerate(items):
    P(tf, i == 0, it, sz=21, color=INK, sa=13)

# ══════════════════ S3 기존 접근과 남는 문제 ══════════════════
s = prs.slides.add_slide(BLANK)
rrect(s, 0, 0, 13.3333, 7.5, fill=WHITE, line=WHITE, rounded=False)
page(s, 3, "기존 자동채점 접근과 남는 문제", "손 기능 채점 = 어떤 데이터를 어떻게 가공해 점수로 바꾸는가")
for k, (ac, hd, ln) in enumerate([
    (NAVY, "치료사 평가", ["동작 직접·영상 관찰", "지침 따라 점수 부여", "기준점수 생성"]),
    (TEAL, "수치 기반 평가", ["센서로 관절 위치 측정", "각도·거리 특징 계산", "규칙·학습모형 채점"]),
    (GREEN, "VLM 기반 평가", ["영상 + 지침 입력", "영상·글 동시 해석", "점수 + 근거 출력"])]):
    l = 0.42 + k * 4.32
    card(s, l, 1.35, 4.02, 2.44, hd, ln, accent=ac, hs=0.44, sz=14)
bar(s, 4.02, "남는 문제 — 평가자 주관성 · 천장/바닥 · 시간 과다  |  수치 오류 미검출(손목 96 mm)  |  VLM 총점 평탄",
    fill=NAVY, sz=14.5, h=0.50)
bar(s, 4.66, "연구 질문 — 계산한 수치를 전량 제공할 것인가, 품질로 선별 제공할 것인가",
    fill=TEAL2, sz=16, h=0.52)
for k, lab in enumerate(["영상 촬영 예시", "라벨링 예시", "기존 연구 성능 비교 예시"]):
    ph = rrect(s, 0.42 + k * 4.32, 5.42, 4.02, 1.72, fill=None, line=PHB, lw=1.0, rounded=False)
    t2 = ph.text_frame; t2.vertical_anchor = MSO_ANCHOR.MIDDLE
    P(t2, True, "[사진 자리]  " + lab, sz=12, bold=True, color=PHB, align=PP_ALIGN.CENTER)

# ══════════════════ S4 선행연구 근거와 공백 ══════════════════
s = prs.slides.add_slide(BLANK)
rrect(s, 0, 0, 13.3333, 7.5, fill=WHITE, line=WHITE, rounded=False)
page(s, 4, "선행연구가 밝힌 것과 남는 공백", "입력·처리·검증을 구분해 확인")
card(s, X1, R1, CW, CH, "Li 2026 · 영상 VLM", [
    "비장애 20 + 뇌졸중 51", "영상 + 지침만 입력", "총점 평탄 → 1점 기준선", "PMID 42406872"],
    accent=NAVY, photo="영상만 입력 예시")
card(s, X2, R1, CW, CH, "Li 2022 · 센서 채점", [
    "뇌졸중 20명 · r=.981", "손목 오차 96 mm", "점수 정확·수치 부정확", "PMID 36291314"],
    accent=TEAL, photo="센서 채점 예시")
card(s, X1, R2, CW, CH, "Tang 2025 · 특징 주입", [
    "특징 시계열 → LLM", "예시 3개 최적", "4개에서 붕괴(0.42)", "arXiv:2505.18412"],
    accent=TEAL, photo="특징 주입 구조")
card(s, X2, R2, CW, CH, "남는 공백", [
    "수치 주입 효과 미측정", "게이팅 인과효과 미측정", "과잉 보류 대가 미측정", "→ 본 연구 측정 대상"],
    accent=NAVY, photo="연구 공백 도식")

# ══════════════════ S5 실험 세팅 (피드백 ①) ══════════════════
s = prs.slides.add_slide(BLANK)
rrect(s, 0, 0, 13.3333, 7.5, fill=WHITE, line=WHITE, rounded=False)
page(s, 5, "실험 세팅 — 환경·대상·절차", "피드백 반영 ①")
for k, (ac, hd, ln) in enumerate([
    (NAVY, "입력 · 수치", ["D455 1대 (단일 RGB-D)", "RGB 1280×800 · depth 1280×720",
                        "실측 16.9 · 24.6 fps", "작업거리 0.65–0.85 m", "K1·K2 산출 (원본 depth)"]),
    (TEAL, "VLM · 조건", ["Qwen2.5-VL-72B 고정", "0-shot · greedy · 무학습",
                       "A1 없음 / A2 전체", "A3 Q 선별 / R 무작위", "조건 간 수치만 변경"]),
    (NAVY, "대상 · 절차", ["뇌졸중 23명 (개발 3 + 본 20)", "비장애인 22명 (개발 6 + 검증 16)",
                         "연습 2 → 본 첫 3회", "T1 → 휴식 → T2", "120영상 × 2모델"])]):
    l = 0.62 + k * 4.30
    card(s, l, 1.40, 3.80, 3.30, hd, ln, accent=ac, hs=0.50, sz=14)
for k, lab in enumerate([
        "실험 세팅 전경 — 카메라(D455)+삼각대, 작업거리 0.65–0.85 m, 테이블 75 cm + 선반 37 cm, 팔걸이 없는 의자",
        "배치 도면 — 선반 37 cm · 물체 위치(중심시상면-액와선 중간) · 뚜껑 2개",
        "환측 손 파지 장면 — 블록/구슬/뚜껑이 함께 보이는 구도"]):
    ph = rrect(s, 0.62 + k * 4.30, 4.82, 3.80, 1.62, fill=None, line=PHB, lw=1.0, rounded=False)
    ptf = ph.text_frame; ptf.word_wrap = True; ptf.vertical_anchor = MSO_ANCHOR.MIDDLE
    P(ptf, True, "[사진 자리]", sz=11.5, bold=True, color=PHB, align=PP_ALIGN.CENTER, sa=2)
    P(ptf, False, lab, sz=10.5, color=PHB, align=PP_ALIGN.CENTER, line=1.02)
bar(s, 6.58, "환경 = 테이블 75 · 의자 46(팔걸이 없음) · 선반 37 cm  |  저장 = L0 원본 RGB·원시 depth·타임스탬프 필수",
    fill=NAVY, sz=14.5, h=0.55)

# ══════════════════ S6 왜 2개 동작 (피드백 ②) ══════════════════
s = prs.slides.add_slide(BLANK)
rrect(s, 0, 0, 13.3333, 7.5, fill=WHITE, line=WHITE, rounded=False)
page(s, 6, "두 과제 선정 근거 — ARAT 위계 질문", "피드백 반영 ② — '가장 어려운 것 하나면 되지 않나?'")
card(s, X1, 1.28, 12.33, 0.80, "전제 — 건너뛰기 규칙은 '하위검사(subtest) 내부' 전용  (Lyle 1981)", [],
     accent=TEAL2, hs=0.68, ct=16.5)
card(s, X1, 2.20, CW, 2.20, "① 다른 하위검사", [
    "T1 = ARAT 3번 = Grasp", "T2 = ARAT 12번 = Pinch",
    "\"top marks for that subtest\"", "→ 중복 아님"], accent=TEAL, sz=14.5)
card(s, X2, 2.20, CW, 2.20, "② 위계 자체가 불완전", [
    "Koh 2006 — 위반 = pinch", "van der Lee — 15/19만",
    "소척도 구조 미지지", "→ '하나면 자동' 불성립"], accent=NAVY, sz=14.5, photo="ARAT 위계 도식")
card(s, X1, 4.52, CW, 2.12, "③ 목적 = 총점 추정 아님", [
    "ARAT 원점수 = 순서 정보만", "T2 → K1 의미 성립 (주 결과)",
    "T1 → K1 해석 범위 비교"], accent=NAVY, sz=14.5)
card(s, X2, 4.52, CW, 2.12, "④ 2개 선택의 성격", [
    "난이도 커버리지 아님", "파지 구속(grasp constraint) 대비",
    "엄지+검지 강제 vs 파지 자유"], accent=GREEN, sz=14.5)

# ══════════════════ S7 두 과제 물성 ══════════════════
s = prs.slides.add_slide(BLANK)
rrect(s, 0, 0, 13.3333, 7.5, fill=WHITE, line=WHITE, rounded=False)
page(s, 7, "두 과제의 물성과 배치", "ARAT 표준 — Yozbatiran 2008 / Lyle 1981")
card(s, X1, R1, CW, CH, "T2 · 주 결과 (ARAT 12번 · Pinch)", [
    "구슬 ⌀1.5 cm · 5.4 g", "엄지 + 검지 패드 강제",
    "3점 = 5초 이내 + 패드"], accent=GREEN, photo="구슬 집기 장면")
card(s, X2, R1, CW, CH, "T1 · 참고 (ARAT 3번 · Grasp)", [
    "블록 5 cm · 55 g", "opposition이면 파지 자유",
    "3점 = 5초 이내 정상"], accent=NAVY, photo="블록 옮기기 장면")
card(s, X1, R2, CW, CH, "배치 (표준)", [
    "테이블 → 선반 37 cm", "하부 뚜껑 → 상부 뚜껑",
    "물체 = 정중시상면-액와선 중간", "37 cm 수직 들어올리기"],
    accent=NAVY, photo="배치 도면")
card(s, X2, R2, CW, CH, "채점 · 주의", [
    "0/1/2/3 = 60초·5초 기준", "합계 0–6점 = 임상점수 아님",
    "무게 약 10배 · 크기 3.3배", "실패 영상 삭제 금지"], accent=NAVY, sz=14.5)

# ══════════════════ S8 K1·K2 · Q ══════════════════
s = prs.slides.add_slide(BLANK)
rrect(s, 0, 0, 13.3333, 7.5, fill=WHITE, line=WHITE, rounded=False)
page(s, 8, "VLM에 넣는 수치 K1·K2와 선별 규칙 Q", "K1·K2 = 무조건 포함 · 추가 지표(SPARC 등)는 편입 조건 통과 시에만 — 계산은 원본 프레임에서만")
card(s, X1, R1, CW, CH, "K1 — 엄지–검지 표면점 거리", [
    "MediaPipe 4번·8번 표면점", "관찰 구간 P95 (mm)",
    "금지 = PAp · 최대벌림 · 관절중심"], accent=TEAL, photo="K1 개념도")
card(s, X2, R1, CW, CH, "K2 — 손목 표면점 속도", [
    "MediaPipe 0번 표면점 3D 속도", "관찰 구간 P95 (mm/s)",
    "dt = 장치 타임스탬프만", "금지 = 민첩성 · 신경회복"],
    accent=TEAL, photo="K2 개념도")
card(s, X1, R2, CW, CH, "Q 규칙 5개 (사전 동결)", [
    "Q1 깊이 유효 비율", "Q2 최장 결측 > 0.3초", "Q3 유효 표본 < 50",
    "Q4 경계 혼합 > 50%", "Q5 가림 > 50% (2인)"], accent=NAVY, sz=14, photo="Q 판정 예시")
card(s, X2, R2, CW, CH, "적용 · R 조건", [
    "걸린 수치 = null 보류", "임계값은 치료사 점수 무관",
    "R = 같은 수 무작위 제거", "제외율 > 50% → 비교 제한"], accent=NAVY, sz=14.5)


# ══════════════════ S12 조건 설계 ══════════════════
s = prs.slides.add_slide(BLANK)
rrect(s, 0, 0, 13.3333, 7.5, fill=WHITE, line=WHITE, rounded=False)
page(s, 9, "추가 지표 편입 조건 — 임계값과 근거",
     "K1·K2 = 무조건 포함 · 추가 지표 = 4개 조건을 모두 통과할 때만 편입")
cdata = [
    ["조건", "임계값", "근거"],
    ["C1 계산 가능성", "결측률 ≤ 20%", "EMA 결측 지침: 10–20% 초과 시 민감도 분석 필요 (보편 규칙은 없음)"],
    ["C2 반복성", "MDC95 / |mean| ≤ 50%", "Wagner 2008(계획서 §3-7): 취약 지표는 50% 이상 변해야 '진짜 변화'. MDC 범위 7.4–98.9%"],
    ["C3 물리 타당성", "위반 ≤ 5%", "정의 기반 — 아래 카드의 값을 벗어나면 파이프라인 오류"],
    ["C4 개입 민감도", "주입이 P95를 ≥ 10% 이동  (보류)", "계획서 §3-16: burst는 ≤+2.6%라 '실험 무효'. 단 u 미측정 → 보류"],
]
table(s, 0.50, 1.28, 12.33, 2.15, cdata, [2.10, 3.55, 6.68], sz=13)
card(s, X1, 3.60, 12.33, 2.55, "C3 — '물리적 불가능/오류 값'의 정의", [
    "SPARC > 0  —  SPARC = −∫(…) 이므로 정의상 ≤ 0 (Balasubramanian 2015). 양수면 오류",
    "개별 관절 ROM > 180°  —  정상 MCP ≈ 90° · PIP ≈ 100° · DIP ≈ 90° (AAOS)",
    "손가락별 TAM > 360°  —  정상 TAM 260–270°(excellent), 최대 ≈ 330°",
    "TAM_total(5지 합) > 1500°  —  4지×270° + 엄지 ≈ 130° → 정상 ≈ 1210°",
    "손가락 각속도 > 2000°/s  —  주먹 쥐기 0.5–1.0초에 ≈ 250–300° → 평균 300–600°/s",
    "MGA ≤ 0 또는 > 250 mm  ·  시행 시간 > 120초  —  ARAT 항목 60초 제한 + 여유"],
    accent=NAVY, hs=0.40, sz=12.5, ct=15)
bar(s, 6.35, "⚠️ 구판 C2(CV ≤ 25%)는 폐기 — CV는 피험자 간 변동을 섞어 반복성 지표로 부적합. C4는 u 미측정으로 보류",
    fill=RGBColor(0xB8, 0x6A, 0x00), sz=13, h=0.55)

# ══════════════════ S10 파일럿 검정 결과 (신규) ══════════════════
s = prs.slides.add_slide(BLANK)
rrect(s, 0, 0, 13.3333, 7.5, fill=WHITE, line=WHITE, rounded=False)
page(s, 10, "파일럿 통계 검정 결과 — MDC 기준", "비장애인 2명 · 18시행 · 반복성은 MDC95/|mean| (Wagner 2008)")
pdata = [
    ["지표", "결측%", "MDC95/mean%", "물리위반%", "판정"],
    ["SPARC (smoothness)", "0", "102.0", "0", "✗ C2 실패"],
    ["Flex_Speed_deg_s (속도)", "0", "393.4", "89", "✗ C2·C3 실패"],
    ["Ext_Speed_deg_s (속도)", "0", "—", "89", "✗ C3 실패"],
    ["MGA_mm_3D_cal (코드의 K1 대리)", "100", "—", "—", "✗ C1 실패"],
    ["RS_MGA_p95_mm (depth 기반)", "33", "56.5", "0", "✗ C1·C2 실패"],
    ["Thumb_PalmarAbd_ROM_deg", "0", "125.8", "0", "✗ C2 실패"],
    ["ROM_Thumb_MCP_deg", "0", "61.1", "0", "✗ C2 실패"],
    ["Thumb_CMC_ROM_deg", "0", "53.6", "0", "✗ C2 실패 (구판 CV는 통과)"],
    ["ROM_Index_MCP_deg", "0", "39.6", "0", "✓ 편입가능"],
    ["MP_MGA_raw_mm", "0", "22.0", "0", "✓ 편입가능"],
]
table(s, 0.50, 1.28, 12.33, 4.15, pdata, [4.63, 1.30, 1.85, 1.85, 2.70], sz=13)
card(s, X1, 5.58, 12.33, 1.10, "결론", [
    "SPARC = MDC 102% (측정 불가). 속도 계열 = 물리위반 89%. 엄지 CMC·중수 MCP도 MDC 50% 초과로 탈락.",
    "통과 = MP_MGA_raw_mm(22%) · ROM_Index_MCP(40%) · Index_ROM(17%). CV 기준과 결과가 다르다(Thumb_CMC 뒤바뀜)."],
    accent=NAVY, hs=0.38, sz=12.5, ct=15)
P(tb(s, 0.62, 6.78, 12.08, 0.40), True,
  "⚠️ 소표본(2명) → 확정 아님 · 데이터: capstone/호진파일 ... trials_summary.csv · 스크립트: experiments/analysis/metric_portfolio_check_v2.py",
  sz=10, color=GRAY)

# ══════════════════ S11 핵심 수치 근거 대장 (신규) ══════════════════
s = prs.slides.add_slide(BLANK)
rrect(s, 0, 0, 13.3333, 7.5, fill=WHITE, line=WHITE, rounded=False)
page(s, 11, "핵심 수치의 근거 대장 — '왜 이 값이어야 하는가'",
     "A=1차 원문 확인 · B=2차 자료 · C=자체 계산·합성 · D=미검증  (정본 §3.1)")
ndata = [
    ["수치", "값", "출처", "등급"],
    ["ARAT 물성·배치", "블록 5 cm 55 g · 구슬 ⌀1.5 cm 5.4 g · 선반 37 cm", "Yozbatiran 2008 · Lyle 1981", "A"],
    ["건너뛰기 규칙", "하위검사(subtest) 내부 전용", "Lyle 1981 채점지", "A"],
    ["시행 수 — 수집", "연습 2 + 본 5~15", "SRRR2 Kwakkel 2019: ≥15 trials", "A"],
    ["시행 수 — 모델 입력", "과제당 본 1~3회 (첫 3회 사전 고정)", "Frykberg 2021: 2–3회 안정·3–5회 충분", "A"],
    ["반복성 임계 (C2)", "MDC95 / |mean| ≤ 50%", "Wagner 2008: MDC 7.4–98.9%", "A"],
    ["결측률 상한 (C1)", "≤ 20%", "EMA 결측 지침 (보편 규칙 없음)", "B"],
    ["Q2 최장 결측", "> 0.3초 → 보류", "Jeannerod 1984: 닫힘 ≈25% MT", "B"],
    ["Q3 유효 표본", "< 50 → 보류", "자체 시뮬: K2 CV 4.0%@50", "C"],
    ["프레임 샘플링", "5초 10 Hz · 상한 64 · 640×480", "자체 산술 (14프레임=0.47초)", "C"],
    ["표본 크기", "장애인 23(3+20) · 비장애인 22(6+16)", "sample_size_analysis.py", "C"],
    ["카메라 배치", "0.65–0.85 m · 아래 30–45°", "미검증 후보값 — 본 촬영에서 확정", "D"],
]
table(s, 0.50, 1.28, 12.33, 4.50, ndata, [2.30, 4.35, 4.28, 1.40], sz=12)
card(s, X1, 5.95, 12.33, 0.95, "왜 이 행동이며, 몇 회 하는가", [
    "왜 = 파지 구속 대비 (T2 엄지+검지 강제 vs T1 파지 자유) + ARAT 위계(서로 다른 하위검사)",
    "몇 회 = 훈련 2회 + 수집 5~15회(SRRR2) → 모델 입력은 첫 3회(Frykberg)로 사전 고정"],
    accent=NAVY, hs=0.38, sz=12.5, ct=15)
P(tb(s, 0.62, 6.98, 12.08, 0.40), True,
  "미검증(D)으로 남은 수치는 카메라 배치 하나. 나머지는 A~C 등급 (C = 자체 계산·합성, 재현 가능하나 실증 아님)",
  sz=10, color=GRAY)

# ══════════════════ S10 조건 설계 ══════════════════
s = prs.slides.add_slide(BLANK)
rrect(s, 0, 0, 13.3333, 7.5, fill=WHITE, line=WHITE, rounded=False)
page(s, 12, "실험 조건과 세 가지 비교", "같은 영상·사람·시행에서 수치의 양과 품질만 변경")
data = [["조건", "K1·K2 제공 방식", "비교 목적"],
        ["A1 영상 기준", "제공하지 않음", "영상만 있을 때의 기준선"],
        ["A2 전체 제공", "계산 가능한 수치 모두", "A2 vs A1 → 수치 주입 (PR-1)"],
        ["A3 선별 제공", "Q 통과 수치만", "A2 vs A3 → 게이팅 (PR-2)"],
        ["R 무작위 제외", "A3와 같은 수 무작위 제거", "A3 vs R → 고유 가치 (PR-3)"]]
table(s, 0.62, 1.42, 12.08, 2.55, data, [2.6, 4.6, 4.88], sz=15.5)
card(s, X1, 4.22, CW, 2.30, "1급 기술 결과 (검정 아님)", [
    "보류율(A3) = 게이팅의 대가", "(보류율, MAE) Pareto 곡선",
    "보조 모델 부호 일치"], accent=TEAL2, sz=14.5, photo="조건 구조 도식")
card(s, X2, 4.22, CW, 2.30, "탐색적 (보정 없음)", [
    "A4 영상 제거 · A0 경량모형", "오류 주입 bias/burst (기전)",
    "큰 오차(≥2점) 비율 · 설명 평가"], accent=GRAY, sz=14.5, photo="게이팅 개념 도식")


# ══════════════════ S10 모델 로스터 (신규) ══════════════════
s = prs.slides.add_slide(BLANK)
rrect(s, 0, 0, 13.3333, 7.5, fill=WHITE, line=WHITE, rounded=False)
page(s, 13, "VLM 모델 로스터 — 로컬 실측 + 최신 + 5090 적합성",
     "주 모델 1개 = 확증 검정 · 나머지 = 부호 일치 · 민감도 (다중비교 폭증 방지)")
mdata = [
    ["역할", "모델", "상태 (2026-09-28 실측)"],
    ["주 모델 (확증 검정)", "Qwen2.5-VL-72B-Instruct", "미설치 · Li 2026 직접 비교용 → 5090 불가, 클라우드 권장"],
    ["로컬 실행 가능", "Qwen2.5-VL-32B-Instruct", "설치 완료 64 GB · 5090은 Q4(~20 GB) 필요"],
    ["로컬 실행 가능", "Qwen2.5-VL-3B-Instruct", "설치 완료 7.1 GB · 5090 즉시 실행"],
    ["로컬 실행 가능", "LLaVA-OneVision-Qwen2-7B-OV", "설치 완료 19 GB · 5090 즉시 실행"],
    ["로컬 실행 가능", "LLaVA-NeXT-Video-7B", "설치 완료 14 GB · 5090 즉시 실행 (영상 특화)"],
    ["로컬 미완", "Qwen3-VL-8B / LLaVA-1.5-7B", "가중치 미완 → 다운로드만 하면 5090 즉시 실행"],
    ["최신 후보 (검토)", "Qwen3-VL-32B · 235B-A22B", "32B = 5090 Q4 가능 / 235B = 클라우드"],
    ["최신 후보 (검토)", "InternVL3.5-38B · 78B", "38B = 5090 Q4 빠듯 / 78B = 클라우드"],
    ["최신 후보 (검토)", "GLM-4.6V-Flash 9B · 4.6V 106B", "9B = 5090 즉시 실행 / 106B = 클라우드"],
]
table(s, 0.50, 1.30, 12.33, 4.05, mdata, [2.45, 4.30, 5.58], sz=13.5)
card(s, X1, 5.50, 12.33, 1.30, "컴퓨트 = 1,608출력 × 모델 수 (비용 통제 필요)", [
    "2모델 = 3,216 · 4모델 = 6,432 · 6모델 = 9,648",
    "확증 검정(PR-1~3)은 주 모델에서만 · 나머지는 부호 일치·민감도만 보고",
    ("모델 수를 늘리면 '모델 특이적'이라는 반박은 줄지만 출력 비용이 비례 증가", True, AMBER)],
    accent=NAVY, hs=0.40, sz=13.5)

# ══════════════════ S11 VLM · 프레임 ══════════════════
s = prs.slides.add_slide(BLANK)
rrect(s, 0, 0, 13.3333, 7.5, fill=WHITE, line=WHITE, rounded=False)
page(s, 14, "고정 VLM과 입력 프레임", "추가 학습 없이 동일 모델·프롬프트 · 조건별 차이는 수치뿐")
card(s, X1, R1, CW, CH, "모델", [
    "주 = Qwen2.5-VL-72B", "Li 2026과 동일 → 직접 비교",
    "보조 = 부호 일치 확인", "보조 체크포인트 미확정"],
    accent=NAVY, photo="모델 비교 구조")
card(s, X2, R1, CW, CH, "출력 · 실패", [
    "0-shot · greedy · 무학습", "출력 = 0–3점 + 근거 ≤2문장",
    "실패 1회 재시도", "손실 = 3 대체 → 성공률 병기"],
    accent=NAVY, photo="출력 예시")
card(s, X1, R2, CW, CH, "프레임 규칙 (동결)", [
    "앞 5.0초 = 10 Hz", "5초 초과분 = 2 Hz",
    "상한 64 · 해상도 640×480", "사건 구간 임의 선택 금지",
    "실제 fps로 인덱스 계산"], accent=TEAL, sz=14)
card(s, X2, R2, CW, CH, "주의", [
    "실측 16.9 fps → 10 Hz 저하", "30 fps 가정 금지",
    "조건명 프롬프트 기재 금지", "프롬프트 템플릿 동일 고정"], accent=NAVY, sz=14.5)

# ══════════════════ S11 분석 · 판정 ══════════════════
s = prs.slides.add_slide(BLANK)
rrect(s, 0, 0, 13.3333, 7.5, fill=WHITE, line=WHITE, rounded=False)
page(s, 15, "분석 방법과 예상 결과", "사람 단위 짝지은 비교 · 사람 단위 bootstrap")
P(tb(s, 0.62, 1.30, 5.73, 0.40, MSO_ANCHOR.MIDDLE), True, "주 비교 — 양수일 때의 의미",
  sz=18, bold=True, color=NAVY)
P(tb(s, 6.88, 1.30, 5.83, 0.40, MSO_ANCHOR.MIDDLE), True, "관찰 가능한 결과와 해석",
  sz=18, bold=True, color=NAVY)
table(s, 0.62, 1.85, 5.94, 3.26,
      [["비교", "차이 정의", "양수의 의미"],
       ["수치 주입", "MAE(A2) − MAE(A1)", "전체 제공이 악화"],
       ["수치 선별", "MAE(A2) − MAE(A3)", "선별 제공이 개선"],
       ["선별 기준", "MAE(R) − MAE(A3)", "Q가 무작위보다 개선"]],
      [1.38, 2.30, 2.26], sz=14.5)
table(s, 6.88, 1.85, 5.83, 3.29,
      [["예상 패턴", "해석"],
       ["A2 악화 · A3 개선", "일부 수치 보류 가치"],
       ["A3 > R", "품질 규칙 자체 기여"],
       ["A2·A3 비슷", "수치 주입 효과 · 선별 이득 작음"],
       ["보류율 ↑ · PR-2 유의", "이득이 좁은 구간 (절충)"],
       ["보류율 ↑ · PR-2 비유의", "과잉 보류가 대가만 남김"]],
      [2.40, 3.43], sz=14)
P(tb(s, 0.62, 5.30, 5.83, 1.20), True,
  "사람별 MAE 짝지어 비교\nbootstrap 10,000회 · 95% CI\n세 가지 주 비교에 Holm(k=3)", sz=14.5, sa=3, line=1.02)
P(tb(s, 6.88, 5.30, 5.83, 1.20), True,
  "유의성 하나로 결론 금지\nCI가 0 포함 = 방향 미확인\n비유의 = 동등 아님", sz=14.5, sa=3, line=1.02)
bar(s, 6.60, "결론: 어떤 수치를 제공하거나 보류할 때 VLM 채점오차가 달라지는가  |  실패 출력 = 손실 3 별도 보고", sz=14.5, h=0.55)

# ══════════════════ S12 한계 · 다음 ══════════════════
s = prs.slides.add_slide(BLANK)
rrect(s, 0, 0, 13.3333, 7.5, fill=WHITE, line=WHITE, rounded=False)
page(s, 16, "한계와 다음 단계", "정직하게 — 아직 실증 0건")
card(s, X1, R1, CW, CH, "한계 (현재)", [
    "실증 데이터 0건", "u(수치 실제 오차) 미측정",
    "n=20 → 큰 효과 방향만", "접촉 순간 오류 = 검출 불가"], accent=NAVY, sz=14.5)
card(s, X2, R1, CW, CH, "본평가 전 처리", [
    "수치 정의·파이프라인 동결", "모델 로스터 확정 (주+로컬+최신)",
    "치구 135기록 · IRB", "컴퓨트 = 1,608 × 모델 수"], accent=NAVY, sz=14.5, photo="일정 로드맵")
card(s, X1, R2, CW, CH, "이 연구의 위치", [
    "기여 = '처음 제안' 아님", "= '처음 측정'",
    "같은 영상·라벨에서 수치만 변경"], accent=TEAL, sz=14.5)
card(s, X2, R2, CW, CH, "다음 단계", [
    "치구 135기록 → u 확정", "모델 로스터 확정 후 촬영",
    "동결 해시 + 사전등록"], accent=NAVY, sz=14.5)

prs.save("capstone/손과제_VLM_연구계획_v6.pptx")
print("saved v6, slides =", len(prs.slides._sldIdLst))
