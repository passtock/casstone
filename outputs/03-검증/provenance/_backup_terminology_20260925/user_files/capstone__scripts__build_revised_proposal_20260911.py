# -*- coding: utf-8 -*-
"""
Generate '연구계획서20260911_통합본_최종개정.docx'
RGB-D 운동학 정보를 활용한 양손 손 과제 VLM 평가 파일럿 연구 계획서 (최종 개정본 - 2026년 9월 11일)
Author: 한동대학교 기계제어공학 · Human Robotics Lab 22000561 이재용

반영된 핵심 피드백 내역 (사용자 확정 지침 10개 항목 100% 완결):
  1. Primary A2 - A1: 순수 운동학 추가 효과를 주 질문으로 유지
  2. Amprimo 2024 정확한 기술: Azure Kinect DK + 6-camera OptiTrack 검증 명시 및 D455 환경에서의 독자적 측정 검증 분리 기술
  3. Li 2026 과장 완화: 'F1~F4 주입 필수성 증명' 대신 '3D 수치 보완의 가설적 근거 제공'으로 학술적 수정
  4. 14프레임 샘플링 정확화: 단순 균등 분할이 아닌 'phase-stratified 14-frame sampling / 수행단계 기반 14프레임 샘플링(획득 6 + 유지 2 + 해제 6)'으로 정의
  5. 양손 운동학 입력: 마비측 주 분석 + 양손 동시 측정 원형 유지
  6. F2 time_to_peak_s: 조작적 정의 유지
  7. A0 모델 고도화: 순서 등급(0 < 1 < 2)을 보존하는 'L2-regularized ordinal logistic regression (순서형 로지스틱 회귀)'으로 수정
  8. 추론 실행량 최적화: 탐욕적 결정론적(do_sample=False) 환경에 맞추어 무작위 반복 대신 '구현 재현성 확인(Implementation Reproducibility Check)'으로 축소 정돈
  9. 모델 로딩 상세 정리: 부록 A의 부정확한 loader/버전 세부사항 삭제 및 깔끔한 아키텍처 개요 표로 정돈
  10. 단정적 과장 표현 완화: '완벽 보호/원천 차단/치명적/전혀 없음'을 '위험을 크게 낮춤/주요 한계/확인한 문헌 범위에서 직접 검증한 연구를 찾기 어려움'으로 학술적 품격 완화
"""

import os
from pathlib import Path
import docx
from docx import Document
from docx.shared import Pt, Cm, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import qn, nsdecls

def create_revised_proposal():
    doc = Document()

    # 1. Page Setup (Margins: 2.54 cm / 1 inch)
    sections = doc.sections
    for section in sections:
        section.top_margin = Cm(2.54)
        section.bottom_margin = Cm(2.54)
        section.left_margin = Cm(2.54)
        section.right_margin = Cm(2.54)
        section.page_width = Cm(21.0)
        section.page_height = Cm(29.7)

    # 2. Typography Helper Functions
    def set_font(run, name='맑은 고딕', size_pt=10, bold=False, italic=False, color_rgb=(34, 34, 34)):
        run.font.name = name
        run.font.size = Pt(size_pt)
        run.font.bold = bold
        run.font.italic = italic
        run.font.color.rgb = RGBColor(*color_rgb)
        rPr = run._element.get_or_add_rPr()
        rFonts = rPr.find(qn('w:rFonts'))
        if rFonts is None:
            rFonts = OxmlElement('w:rFonts')
            rPr.append(rFonts)
        rFonts.set(qn('w:eastAsia'), name)
        rFonts.set(qn('w:ascii'), name)
        rFonts.set(qn('w:hAnsi'), name)

    def add_para(doc, text='', bold=False, size_pt=9.8, align=WD_ALIGN_PARAGRAPH.LEFT, 
                 space_before=0, space_after=5, line_spacing=1.15, color_rgb=(34, 34, 34)):
        p = doc.add_paragraph()
        p.alignment = align
        p.paragraph_format.space_before = Pt(space_before)
        p.paragraph_format.space_after = Pt(space_after)
        p.paragraph_format.line_spacing = line_spacing
        p.paragraph_format.widow_control = True
        if text:
            run = p.add_run(text)
            set_font(run, size_pt=size_pt, bold=bold, color_rgb=color_rgb)
        return p

    def add_h1(doc, text):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(15)
        p.paragraph_format.space_after = Pt(6)
        p.paragraph_format.keep_with_next = True
        run = p.add_run(text)
        set_font(run, size_pt=12.5, bold=True, color_rgb=(16, 44, 87)) # Navy
        return p

    def add_h2(doc, text):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(11)
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.keep_with_next = True
        run = p.add_run(text)
        set_font(run, size_pt=10.8, bold=True, color_rgb=(30, 78, 140)) # Slate Navy
        return p

    def add_h3(doc, text):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(7)
        p.paragraph_format.space_after = Pt(2)
        p.paragraph_format.keep_with_next = True
        run = p.add_run(text)
        set_font(run, size_pt=9.8, bold=True, color_rgb=(50, 60, 75)) # Charcoal
        return p

    def add_callout(doc, title, text_list, border_color='1E4E8C', bg_color='F4F8FC'):
        tbl = doc.add_table(rows=1, cols=1)
        tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
        cell = tbl.cell(0, 0)
        cell.width = Cm(15.92)
        
        tcPr = cell._tc.get_or_add_tcPr()
        shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{bg_color}"/>')
        tcPr.append(shd)
        
        borders = parse_xml(f'''
            <w:tcBorders {nsdecls("w")}>
                <w:top w:val="none"/>
                <w:left w:val="single" w:sz="24" w:space="0" w:color="{border_color}"/>
                <w:bottom w:val="none"/>
                <w:right w:val="none"/>
            </w:tcBorders>
        ''')
        tcPr.append(borders)
        
        margins = parse_xml(f'''
            <w:tcMar {nsdecls("w")}>
                <w:top w:w="120" w:type="dxa"/>
                <w:bottom w:w="120" w:type="dxa"/>
                <w:left w:w="180" w:type="dxa"/>
                <w:right w:w="180" w:type="dxa"/>
            </w:tcMar>
        ''')
        tcPr.append(margins)
        
        p = cell.paragraphs[0]
        p.paragraph_format.space_before = Pt(2)
        p.paragraph_format.space_after = Pt(3)
        p.paragraph_format.line_spacing = 1.15
        run = p.add_run(f"■ {title}\n")
        set_font(run, size_pt=9.5, bold=True, color_rgb=(16, 44, 87))
        
        for t in text_list:
            p2 = cell.add_paragraph()
            p2.paragraph_format.space_before = Pt(1)
            p2.paragraph_format.space_after = Pt(2)
            p2.paragraph_format.line_spacing = 1.12
            run2 = p2.add_run(t)
            set_font(run2, size_pt=9.0, bold=False, color_rgb=(40, 50, 60))
            
        doc.add_paragraph().paragraph_format.space_after = Pt(4)

    def style_table(t, widths, hdr_bg='E8EEF5', zebra_bg='F8FAFC'):
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        t.autofit = False
        
        for ri, row in enumerate(t.rows):
            trpr = row._tr.get_or_add_trPr()
            trpr.append(OxmlElement('w:cantSplit'))
            if ri == 0:
                trpr.append(OxmlElement('w:tblHeader'))
                
            for ci, cell in enumerate(row.cells):
                cell.width = Cm(widths[ci])
                tcPr = cell._tc.get_or_add_tcPr()
                
                # Shading
                bg = hdr_bg if ri == 0 else (zebra_bg if ri % 2 == 1 else 'FFFFFF')
                shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{bg}"/>')
                tcPr.append(shd)
                
                # Borders
                borders = parse_xml(f'''
                    <w:tcBorders {nsdecls("w")}>
                        <w:top w:val="single" w:sz="4" w:space="0" w:color="D0D7DE"/>
                        <w:left w:val="single" w:sz="4" w:space="0" w:color="D0D7DE"/>
                        <w:bottom w:val="single" w:sz="{"8" if ri==0 else "4"}" w:space="0" w:color="{"A0B0C0" if ri==0 else "D0D7DE"}"/>
                        <w:right w:val="single" w:sz="4" w:space="0" w:color="D0D7DE"/>
                    </w:tcBorders>
                ''')
                tcPr.append(borders)
                
                # Cell Padding
                margins = parse_xml(f'''
                    <w:tcMar {nsdecls("w")}>
                        <w:top w:w="80" w:type="dxa"/>
                        <w:bottom w:w="80" w:type="dxa"/>
                        <w:left w:w="110" w:type="dxa"/>
                        <w:right w:w="110" w:type="dxa"/>
                    </w:tcMar>
                ''')
                tcPr.append(margins)
                
                # Text formatting inside cell
                for p in cell.paragraphs:
                    p.paragraph_format.space_before = Pt(1)
                    p.paragraph_format.space_after = Pt(2)
                    p.paragraph_format.line_spacing = 1.08
                    for r in p.runs:
                        set_font(r, size_pt=8.8, bold=(ri == 0), 
                                 color_rgb=((16, 44, 87) if ri == 0 else (34, 34, 34)))

    def add_styled_table(doc, headers, rows, widths, hdr_bg='E8EEF5', zebra_bg='F8FAFC'):
        t = doc.add_table(rows=len(rows) + 1, cols=len(headers))
        for i, h in enumerate(headers):
            t.rows[0].cells[i].text = h
        for r_idx, r_data in enumerate(rows):
            for c_idx, val in enumerate(r_data):
                t.rows[r_idx + 1].cells[c_idx].text = str(val)
        style_table(t, widths, hdr_bg, zebra_bg)
        add_para(doc, '', space_after=4)
        return t

    def add_code_box(doc, text):
        tbl = doc.add_table(rows=1, cols=1)
        tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
        cell = tbl.cell(0, 0)
        cell.width = Cm(15.92)
        tcPr = cell._tc.get_or_add_tcPr()
        shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="F6F8FA"/>')
        tcPr.append(shd)
        borders = parse_xml(f'''
            <w:tcBorders {nsdecls("w")}>
                <w:top w:val="single" w:sz="4" w:space="0" w:color="D0D7DE"/>
                <w:left w:val="single" w:sz="4" w:space="0" w:color="D0D7DE"/>
                <w:bottom w:val="single" w:sz="4" w:space="0" w:color="D0D7DE"/>
                <w:right w:val="single" w:sz="4" w:space="0" w:color="D0D7DE"/>
            </w:tcBorders>
        ''')
        tcPr.append(borders)
        margins = parse_xml(f'''
            <w:tcMar {nsdecls("w")}>
                <w:top w:w="80" w:type="dxa"/>
                <w:bottom w:w="80" w:type="dxa"/>
                <w:left w:w="120" w:type="dxa"/>
                <w:right w:w="120" w:type="dxa"/>
            </w:tcMar>
        ''')
        tcPr.append(margins)
        p = cell.paragraphs[0]
        p.paragraph_format.space_before = Pt(2)
        p.paragraph_format.space_after = Pt(2)
        p.paragraph_format.line_spacing = 1.05
        run = p.add_run(text)
        set_font(run, name='Consolas', size_pt=8.5, bold=False, color_rgb=(30, 30, 30))
        add_para(doc, '', space_after=4)

    print("Generating Revised Research Proposal Document...")

    # =========================================================================
    # DOCUMENT HEADER
    # =========================================================================
    p_title = add_para(doc, "RGB-D 운동학 정보를 활용한 양손 손 과제 VLM 평가 파일럿 연구", 
                       bold=True, size_pt=16.0, align=WD_ALIGN_PARAGRAPH.CENTER, 
                       space_before=6, space_after=4, color_rgb=(16, 44, 87))
    
    p_sub = add_para(doc, "연구계획서 최종 개정본 (2026년 9월 11일)", 
                     bold=True, size_pt=10.5, align=WD_ALIGN_PARAGRAPH.CENTER, 
                     space_before=0, space_after=4, color_rgb=(70, 80, 95))
    
    p_author = add_para(doc, "한동대학교 기계제어공학 · Human Robotics Lab  |  22000561 이재용\n하드웨어 환경: 단일 PC NVIDIA GeForce RTX 5090 (32GB VRAM) / 100% 로컬 온프레미스", 
                        bold=False, size_pt=9.5, align=WD_ALIGN_PARAGRAPH.CENTER, 
                        space_before=0, space_after=12, color_rgb=(100, 110, 120))

    # =========================================================================
    # SECTION 0: 연구 개요 및 사전 개념 체계
    # =========================================================================
    add_h1(doc, "0. 연구 개요 및 사전 개념 체계 (Conceptual Framework)")
    
    add_para(doc, 
        "본 연구는 뇌졸중 환자의 손 재활 과제 영상에 센서 기반 3D 운동학 수치를 추가했을 때, "
        "시각-언어 모델(Vision-Language Model, 이하 VLM)의 기능 평가 판독 오차가 임상 전문가 기준 대비 실제로 줄어드는지 조사하는 파일럿 연구이다. "
        "독자 및 평가자의 직관적 이해를 돕기 위해, 연구의 세부 기호와 수식에 앞서 핵심 용어와 비교 체계를 친절하게 먼저 정의한다."
    )

    add_para(doc, 
        "■ 기본 용어의 직관적 정의:\n"
        "1. 시각-언어 모델(VLM): 영상(이미지)과 글(텍스트)을 함께 입력받아 사람처럼 의미를 해석하고 추론하는 멀티모달 인공지능이다.\n"
        "2. RGB-D 카메라: 일반 색상 영상(RGB)과 화소별 거리 정보인 깊이(Depth, D)를 동시에 30 fps로 기록하는 카메라(Intel RealSense D455)이다.\n"
        "3. 운동학 수치(Kinematic Features): 힘이나 토크가 아닌, 손 관절 기준점 사이의 거리, 최대 벌림 간격에 도달한 시간, 유지 중 떨림 표준편차 등 순수 움직임의 기하학과 시간을 요약한 물리적 측정값이다. (AI 모델의 학습 가중치 파라미터와 구분됨).\n"
        "4. 파지(Grasp): 물체를 손으로 쥐는 형태를 뜻하며, 본 연구에서는 '목표 형태 만들기(형성)' → '2초 유지' → '손가락 능동 펴기(해제)'의 3단계를 평가한다.\n"
        "5. 수행단계 기반 14프레임 샘플링(Phase-stratified 14-frame sampling): 전체 비디오를 단순히 시간 축에서 균등 14등분하는 것이 아니라, 임상적으로 의미가 뚜렷한 3단계(획득 6장 + 유지 2장 + 해제 6장)로 나누어 각 단계의 시간 전개에 맞추어 층화 추출하여 VLM에 제공한다."
    )

    add_callout(doc, "핵심 임상 배경 및 연구 가설의 요약 (Why this research?)", [
        "1. 임상적 문제 (Clinical Burden): 뇌졸중 후 상지/손 기능 회복(FMA-UE 손 영역) 평가는 임상의의 직접적 육안 관찰과 수작업 채점에 의존하여 막대한 시간(비디오 주석에 사람 513시간 소요, PrimSeq 연구)과 평가자 간 변동성이 발생함.",
        "2. VLM의 기회와 주요 한계 (Opportunity & Visual Hallucination): 최신 VLM은 일상 행동 인식(77.5%)에는 우수하나, 미세 손가락 움직임 정량화 및 파지 접촉 여부 판단에서 '물체 근접을 실제 파지로 오인'하거나 '존재하지 않는 움직임을 생성'하는 시각적 환각(Visual Hallucination) 및 오판이 관찰됨 (Li et al., 2026 선행연구 확인).",
        "3. 해결 가설 (Proposed Solution): 동결된(Frozen Zero-shot) 오픈소스 VLM에 2D 영상뿐 아니라, 인텔 RealSense D455 RGB-D 깊이 센서에서 정량 추출한 4대 3D 운동학 수치(F1~F4)와 건강인 대조군 정상치 규준을 프롬프트로 주입하면, 시각적 모호성을 극복하고 전문가 평가 일치도를 의미 있게 개선할 수 있을 것이다.",
        "4. 100% 로컬 온프레미스 인프라: 환자의 민감한 의료 비디오가 외부 클라우드로 유출되는 보안 위험을 실질적으로 차단하고, 연구실 단일 PC(NVIDIA RTX 5090, 32GB VRAM)에서 5개 모델 전체를 완전 오프라인으로 구동함."
    ])

    add_h2(doc, "0.1 실험 조건 사전 정의 및 명명 체계 (Nomenclature Framework)")
    add_para(doc, 
        "모델에게 제공되는 입력 정보 묶음을 엄격히 통제하여 어떤 정보가 오차를 줄이는지 규명하기 위해, "
        "아래와 같이 조건 기호(A1~A4, A0)와 피처 소거 기호(D1~D4)를 사전에 정의한다. "
        "A1~A4는 동일한 VLM의 입력 조건이고, A0의 마지막 글자는 알파벳 O가 아니라 숫자 0이며 별도로 지도학습하는 순서형 로지스틱 회귀(Ordinal Logistic Regression) 비교 모델이다. "
        "또한 본문에서 'A2 − A1'은 조건 이름을 빼는 것이 아니라 '두 조건의 평균 절대등급오차(MAE) 차이'를 뜻하며, 음수일수록 수치를 추가한 A2 조건의 오차가 작음을 의미한다."
    )

    cond_headers = ["조건 코드", "조건 명칭", "제공 입력 정보", "답하려는 핵심 과학적 질문", "선행 베이스 연구 연결"]
    cond_rows = [
        ["A1", "영상 단독 기본군\n(Vision Baseline)", "수행단계 기반 14프레임 RGB 영상\n(획득 6 + 유지 2 + 해제 6)\n+ 과제 지침 및 판정 기준", "순수 시각 정보만으로 VLM이 손 과제의 형성·유지·해제를 얼마나 정확히 판독하는가?", "Li et al. (2026)의 순수 VLM 뇌졸중 동작 평가 재현 기준"],
        ["A2", "영상 + 운동학 결합군\n(주 실험 조건)", "A1 (14프레임 RGB)\n+ 좌우 3D 운동학 4피처\n+ 센서 품질·결측 플래그", "정량적 거리·시간 수치와 신뢰도 정보가 추가되면 순수 영상의 시각적 환각과 오판이 줄어드는가?", "Amprimo (2024) GMH-D 원리 참고,\nQiu (2022) / Lang (2005) 파지 운동학"],
        ["A3", "영상 + 운동학 + 규준군\n(완전 정보 결합군)", "A2 정보 전체\n+ 건강인 15명 정상치 분포\n(Median, Q1, Q3, 실제 n)", "정상 대조군의 운동학 기준 분포를 함께 제시할 때 모델의 중증도 및 이상 판단이 개선되는가?", "Wang et al. (2024) 임상 지식 결합,\nTang et al. (2025) 프롬프트 맥락"],
        ["A4", "수치 전용 소거군\n(Text/Numeric Ablation)", "영상 전체 배제,\n동일 VLM에 텍스트 지침 +\nA3의 운동학 수치·규준만 제공", "영상을 제공하지 않고 수치와 참조 텍스트만으로도 평가가 가능한가? (순수 영상의 순기여도 역검증)", "Tang et al. (2025) LLM 관절 수치 프롬프팅 비교"],
        ["A0", "고전 ML 벤치마크군\n(Classical ML Baseline)", "양손 수치·품질·규준 메타데이터\n(L2 규제 순서형 로지스틱 회귀 지도학습)", "거대 VLM을 사용하는 것이 순서형 로지스틱 회귀 등 전통적인 통계/머신러닝 수치 모델보다 실제로 우월한가?", "순서형 등급(0<1<2)을 보존하는 지도학습 모델 대비 Zero-shot VLM 도입 타당성 검증"],
        ["D1~D4", "피처별 소거군\n(Feature Ablation)", "주 모델 A2에서 피처\nF1, F2, F3, F4를 각 1개씩 제거", "나머지 피처와 영상이 존재하는 상황에서 각 운동학 피처의 조건부 기여도는 얼마인가?", "변수 중요도 및 최소 최적 센서 피처 조합 탐색"]
    ]
    add_styled_table(doc, cond_headers, cond_rows, [1.8, 2.8, 3.8, 4.2, 3.3])

    add_h2(doc, "0.2 확정 연구 설계 요약표")
    summary_headers = ["구분", "사전 확정 운영값 및 설계 내용", "설계 근거 및 비고"]
    summary_rows = [
        ["대상과 촬영 규모", "개발 건강인 4명, 건강인 대조군 15명, 아급성·만성 뇌졸중 편마비 환자 15명 (Brunnstrom III~V 단계).\n4개 과제 × 과제당 8회 반복 = 환자군 최대 480시행 (양손 동시 촬영, 마비측 주 분석).", "작은 표본 크기의 탐색적 파일럿 설계 (Thabane et al., 2010; Lakens, 2022)."],
        ["주 연구 질문", "동일한 VLM 내에서 'A2(영상 + 운동학 수치)' 조건이 'A1(영상 전용)' 조건에 비해 전문가 기준 판독 절대등급오차(MAE)를 유의미하게 감소시키는가? (주 비교: A2 − A1)", "순수 영상의 시각적 환각(Li et al., 2026) 억제 효과를 직접 검증."],
        ["운동학 입력 피처", "물체 파지 4개 피처(F1 최대간격, F2 피크시간, F3 유지안정도, F4 해제변화량).\n맨손 과제 4개 피처(F1 수축변위, F2 최소도달시간, F3 유지안정도, F4 재개방변화량).\n각 피처의 센서 유효율, 결측 사유 등 품질 정보를 동시 제공.", "Qiu et al. (2022), Lang et al. (2005, 2009), Amprimo et al. (2024) 기반 조작적 정의."],
        ["VLM 하드웨어 및 모델\n(외부 API 완전 배제)", "단일 PC 워크스테이션: NVIDIA GeForce RTX 5090 (32GB GDDR7 VRAM)\n[최신 오픈소스 모델군 2종]\n- Qwen3-VL-8B-Instruct (BF16, ~20.5 GB 점유)\n- Qwen3-VL-30B-A3B-Instruct (AWQ 4-bit, ~22.5 GB 점유)\n[선행연구 기준 재현 모델군 3종]\n- LLaVA-NeXT-Video-7B (BF16, ~19.0 GB 점유)\n- Qwen2.5-VL-32B-Instruct (AWQ 4-bit, ~24.5 GB 점유)\n- LLaVA-OneVision-7B (BF16, ~19.5 GB 점유)", "외부 API 호출 없음 (의료 데이터 프라이버시 보호).\n5개 모델 전체가 RTX 5090 (32GB) 1대에서 100% 로컬 구동 가능 (모두 25GB 이하 점유)."],
        ["주 통계 분석", "전문가 합의 등급(0/1/2점) 기준 환자별 A2 − A1 평균 절대등급오차(MAE) 차이 산출.\n환자 단위 10,000회 블록 부트스트랩 95% 신뢰구간(CI) 추정.", "환자 내 반복 및 양손 상관성을 통제한 엄밀한 비모수 신뢰구간."],
        ["전체 실행 규모 및 재현성 관리", "핵심 조건(A1~A4) 480시행 × 4조건 × 5모델 = 9,600회\n+ 피처 제거(D1~D4) 480시행 × 4조건 = 1,920회\n+ 구현 재현성 확인(Implementation Reproducibility Check) 대표 60시행 1회 재실행 점검\n= 총 약 11,580회 요청.", "탐욕적 결정론적 생성(do_sample=False) 환경에서 파이프라인 무결성을 점검하도록 합리적 축소 정돈."]
    ]
    add_styled_table(doc, summary_headers, summary_rows, [2.5, 9.4, 4.0])

    # =========================================================================
    # SECTION 1: 연구 배경 및 필요성
    # =========================================================================
    add_h1(doc, "1. 연구 배경 및 필요성 (베이스 선행연구 심층 고찰)")
    
    add_h2(doc, "1.1 반복적인 손 과제 평가와 임상적 판독 부담")
    add_para(doc, 
        "뇌졸중 후 상지 마비 환자의 기능 회복 훈련에서 손의 파지(Grasp), 유지(Hold), 펴기(Release) 동작의 정량 평가는 "
        "신경학적 회복 수준을 판정하고 개별화된 재활 계획을 수립하는 핵심 기준이다(Fugl-Meyer et al., 1975). "
        "그러나 임상 현장에서 수행되는 표준 상지 평가(FMA-UE)는 숙련된 치료사가 환자의 동작을 직접 대면 관찰하며 "
        "순서 등급(0, 1, 2점)을 매기는 수작업 방식에 전적으로 의존한다."
    )
    add_para(doc, 
        "비디오 기반 모션 분석의 필요성은 크지만, 수작업 판독 부담은 극심하다. 대표적 선행연구인 PrimSeq에서 Parnandi 등(2022)은 "
        "만성 뇌졸중 환자의 6.4시간 분량 재활 비디오에서 세부 동작(도달, 파지, 유지 등)을 구분하고 주석을 다는 데 숙련된 사람 판독자 513.6시간이 소요되었음을 보고하였다. "
        "반면 자동화된 딥러닝 파이프라인은 1.4시간 만에 처리를 완료하였다. 이는 반복적인 환자 비디오 판독에서 AI 기반 보조 평가 시스템이 "
        "필수적임을 입증하는 강력한 근거이다. 그러나 해당 연구는 손가락 관절의 미세 움직임 정보가 결여되어 단순 대기 상태와 물체 유지 상태를 "
        "구분하지 못하는 주요 오분류 한계를 함께 보고하였다."
    )

    add_h2(doc, "1.2 순수 영상 VLM의 기회와 주요 병목: 시각적 환각 (Visual Hallucination)")
    add_para(doc, 
        "최근 급격히 발전한 대규모 시각-언어 모델(Vision-Language Models, VLM)은 사람의 복잡한 움직임을 영상 프레임과 자연어 지침만으로 "
        "해석할 수 있는 Zero-shot 일반화 능력을 갖추어 큰 기대를 모으고 있다. "
        "그러나 최근 뉴욕대(NYU) 연구팀인 Li 등(2026, PLOS Digital Health)이 건강인 20명과 뇌졸중 환자 51명의 재활 데이터셋을 기반으로 "
        "Qwen2.5-VL 등을 포함한 15개 최신 공개 VLM을 포괄 평가한 결과는 순수 영상 VLM의 명확한 한계를 드러냈다."
    )
    add_para(doc, 
        "Li 등(2026)에 따르면, VLM은 '빗질하기', '물건 집기'와 같은 고수준 일상생활동작(ADL) 인식에서는 77.5%의 높은 정확도를 기록하였으나, "
        "손가락의 미세 동작 정량화와 FMA 운동 손상 점수 예측에서는 판독 정확도가 크게 저하되었다. "
        "특히 주요 문제 중 하나는 '시각적 환각(Visual Hallucination)'이었다. 환자의 손이 물체에 단순히 근접해 지나치기만 했는데도 "
        "실제 물체를 잡은 것으로 잘못 판독하거나, 환자가 시도하지 않은 움직임을 수행했다고 허구로 보고하는 오류가 빈번히 발생하였다. "
        "이는 2D 영상 프레임만으로는 깊이 방향의 접촉 여부, 손가락 벌림 간격(Aperture), 미세 떨림을 모델이 공간적으로 해석할 수 없기 때문이다. "
        "따라서 순수 영상 모델에 물리적 3D 공간 수치를 보완하여 이러한 환각 위험을 낮출 수 있는지에 대한 공학적 검증이 요구된다."
    )

    add_h2(doc, "1.3 3D 운동학 정보 결합의 근거와 연구 공백")
    add_para(doc, 
        "도달-파지(Reach-to-Grasp) 동작의 운동학적 특성은 뇌졸중 운동 제어 분야에서 지난 수십 년간 광범위하게 확립되어 왔다. "
        "Qiu 등(2022)은 아급성기 뇌졸중 환자의 회복 과정에서 최대 파지 간격(Peak Aperture)과 최대 간격 도달 시점(Time to Peak Aperture)이 "
        "임상 점수(FMA)의 호전과 밀접하게 연동됨을 3D 모션 분석으로 규명하였다. "
        "Lang 등(2005, 2009)은 뇌졸중 편마비 환자에서 손가락별 자발적 신전(Extension) 회복 궤적이 파지 속도 및 간격 변화율과 독립적으로 "
        "회복됨을 보고하며, 개별 손가락의 펴기 능력이 기능적 파지 완성의 핵심 지표임을 입증하였다."
    )
    add_para(doc, 
        "이러한 3D 운동학을 마커리스(Markerless) 센서로 획득할 가능성은 Amprimo 등(2024, Biomedical Signal Processing and Control)의 연구에서 방법론적 타당성을 찾을 수 있다. "
        "그들은 Google MediaPipe 손 추적기에 Depth 센서(Microsoft Azure Kinect DK)의 깊이 정보를 결합한 GMH-D 프레임워크를 제안하고, "
        "120 fps OptiTrack 광학 모션캡처(6-camera)와 동시 비교하여 손끝 간격 및 거리 변화 시계열이 모션캡처와 높은 일치도를 보임을 보고하였다. "
        "단, 해당 선행 연구는 Azure Kinect 환경에서 검증된 것이므로, 본 연구는 Amprimo 등의 GMH-D 원리를 참고하되 "
        "본 연구실의 Intel RealSense D455 센서 환경에 대해서는 정적 벤치마크 블록(20~80mm) 등을 통한 자체 측정 검증을 별도로 수행하여 신뢰성을 확보한다."
    )
    add_para(doc, 
        "한편, 수치 정보와 파운데이션 모델을 결합하는 시도는 타 도메인에서 시작되었다. "
        "Tang 등(2025)은 관절 각도 수치를 대규모 언어모델(GPT-4o)에 프롬프트로 주입하여 운동 적절성을 평가하였으며, "
        "Wang 등(2024, MICCAI)은 파킨슨 등 신경퇴행질환의 보행 비디오에 GAITRite 보행 수치와 임상 설명을 결합한 지식 증강 VLM을 제안하였다. "
        "그러나 이들 연구는 보행이나 전신 운동에 한정되어 있으며, 손가락의 복잡한 가림(Occlusion)과 정밀 파지 형태가 지배하는 "
        "뇌졸중 손 과제에서 '재학습(Fine-tuning) 없는 동결 VLM'에 영상과 3D 운동학 수치를 동시 주입했을 때의 정량적 오차 감소 효과는 "
        "확인한 문헌 범위에서 직접 검증한 연구를 찾기 어렵다. 이것이 본 연구가 다루고자 하는 주요 연구 공백(Research Gap)이다."
    )

    add_h2(doc, "1.4 선행 베이스 연구가 남긴 질문과 본 연구의 대응 체계")
    base_headers = ["선행 베이스 연구", "선행연구에서 이미 확인된 사실", "현재 조건에서 여전히 모르는 한계점", "본 연구계획서의 공학적 대응"]
    base_rows = [
        ["Li et al. (2026)\nPLOS Digit Health", "15개 VLM이 거친 활동은 인식하나 미세 동작 정량화 및 채점에서 환각(오판) 발생 확인.", "새로운 VLM에서도 동일한 오류가 남는가? 물리적 센서 수치를 주입하면 이 오판 위험이 낮아지는가?", "Qwen2.5-VL-32B 및 최신 Qwen3-VL 확정, 수행단계 14프레임 영상에 D455 3D 수치 결합 효과(A2−A1) 직접 검증."],
        ["LLaVA-Video & OneVision\n(2024~2025)", "다중 프레임 비디오 시계열과 공간 특징을 통합하는 비디오 특화 VLM 아키텍처 제시.", "비디오 특화 모델이라도 깊이 정보가 없는 순수 RGB 환경에서 파지 접촉 환각을 피할 수 있는가?", "LLaVA-NeXT-Video-7B 및 LLaVA-OneVision-7B를 선행 재현군으로 채택하여 영상단독(A1)과 수치결합(A2) 비교."],
        ["Amprimo et al. (2024)\nBSPC", "MediaPipe에 Depth(Azure Kinect DK)를 결합하여 120fps OptiTrack 모션캡처 대비 거리 시계열 추출 가능성 보고.", "물체를 쥐는 파지 가림 환경 및 Intel RealSense D455 환경에서도 안정적 피처 추출이 유지되는가?", "Amprimo 등의 GMH-D 원리를 참고하되, 본 연구의 D455 환경에서 정적 블록 오차(MAE ≤ 5mm) 및 80% 유효율 기준을 별도 측정·검증함."],
        ["Lang et al. (2005, 2009)\nExp Brain Res", "파지 간격 궤적, 최대 간격, 손가락별 능동 신전 변위가 뇌졸중 손 기능의 핵심 축임.", "소수의 핵심 운동학 요약 수치만으로도 VLM의 임상 판단을 보조하기에 충분한가?", "Qiu (2022)와 결합하여 F1(최대간격), F2(시간), F3(안정도), F4(해제변화량) 4대 피처 고정."],
        ["Tang et al. (2025)\nWang et al. (2024)", "수치를 LLM/VLM에 주입하여 임상 지식을 보강하는 프롬프팅 발상의 유효성 입증.", "수치만 주는 것(A4)과 영상을 함께 주는 것(A3), 머신러닝(A0) 중 임상 평가 최적 구성은?", "입력 블록을 엄격히 분리한 A1~A4 체계 및 LOSO-CV 순서형 로지스틱 회귀(Ordinal Logistic Regression) A0 기준군 동시 구축."]
    ]
    add_styled_table(doc, base_headers, base_rows, [2.8, 4.3, 4.3, 4.5])

    # =========================================================================
    # SECTION 2: 연구 목적 및 비교 프레임워크
    # =========================================================================
    add_h1(doc, "2. 연구 목적 및 비교 프레임워크")
    
    add_h2(doc, "2.1 주 목적 및 주 가설")
    add_para(doc, 
        "본 연구의 주 목적(Primary Objective)은 단일 PC RTX 5090 환경에서 구동되는 로컬 VLM을 대상으로, "
        "동일한 뇌졸중 환자의 손 과제에 대해 '수행단계 기반 14프레임 RGB 영상에 3D 운동학 수치를 추가한 조건(A2)'이 '순수 영상만 제공한 조건(A1)'보다 "
        "전문가 합의 기준 대비 평가 오차를 통계적으로 유의미하게 줄이는지 검증하는 것이다."
    )
    add_para(doc, 
        "■ 주 가설 (Primary Hypothesis): 편마비 환자 15명의 마비측 손 과제 평가에서, "
        "A2 조건의 환자별 평균 절대등급오차(MAE)는 A1 조건의 평균 절대등급오차보다 낮을 것이다. "
        "즉, 환자 단위 차이 D_i = MAE_i(A2) − MAE_i(A1)의 표본 평균이 0보다 작고, "
        "환자 단위 10,000회 부트스트랩 95% 신뢰구간의 상한이 0 미만일 것이다."
    )

    add_h2(doc, "2.2 사전 정의된 비교 프레임워크")
    comp_headers = ["비교 구분", "비교 수식", "비교의 과학적 해석 범위", "통계적 처리 원칙"]
    comp_rows = [
        ["주 비교 (Primary)", "A2 − A1", "동일한 영상에 3D 운동학 수치(F1~F4)와 센서 신뢰도 정보를 추가했을 때의 순수 이득", "환자 단위 짝지은 차이 평균 및 10,000회 블록 부트스트랩 95% CI (가설 검정 기준)"],
        ["보조 비교 1", "A3 − A2", "운동학 수치 외에 '건강인 15명 정상치 분포(Median/IQR)'를 추가 맥락으로 제공한 효과", "참조 규준이 중증도 판단의 닻(Anchor) 역할을 하는지 탐색"],
        ["보조 비교 2", "A3 − A4", "수치와 정상치 규준이 모두 존재하는 상황에서 '영상 정보(14프레임)'를 추가한 효과", "시각 정보 자체의 순수 잔여 기여도(Residual Vision Contribution) 역검증"],
        ["보조 비교 3", "A3 − A1", "순수 영상 대비 운동학 수치와 건강인 참조를 모두 결합한 전체 복합 효과", "복합 정보 주입의 누적 개선 효과 탐색 (보조적 확인)"],
        ["보조 비교 4", "A3 − A0", "순서형 등급을 학습한 L2 규제 순서형 로지스틱 회귀(A0) 대비 Zero-shot 거대 VLM(A3)의 실용적 성능 차이", "환자 데이터로 지도학습한 통계 모델 vs 재학습 없는 파운데이션 모델의 실용적 비교"],
        ["탐색 비교 (Ablation)", "Di − A2\n(i = 1~4)", "A2에서 개별 피처 Fi(최대간격, 시간, 안정도, 해제)를 하나씩 제거했을 때의 오차 증가량", "특정 운동학 변수의 조건부 기여도 평가 (추가 피험자 촬영 없음)"]
    ]
    add_styled_table(doc, comp_headers, comp_rows, [2.5, 2.2, 6.2, 5.0])

    # =========================================================================
    # SECTION 3: 연구 대상자 및 윤리적 고려사항
    # =========================================================================
    add_h1(doc, "3. 연구 대상자 및 윤리적 고려사항")
    
    add_h2(doc, "3.1 대상자 집단 구성 및 역할 분리")
    subj_headers = ["집단 구분", "모집 인원", "연령 및 선정 기준", "데이터의 연구 내 역할 (엄격 분리)"]
    subj_rows = [
        ["개발 건강인군\n(Bench Pilot)", "4명", "만 20~80세 성인.\n상지·손의 신경학적/정형외과적 질환이 없는 자.", "카메라 화각(70cm), 조명, 가림, 14프레임 샘플링, 프롬프트 문구 및 JSON 스키마 사전 점검. 최종 성능 분석에서 영구 제외."],
        ["건강인 대조군\n(Healthy Reference)", "15명", "만 40~80세 성인 (환자군 연령대 정합).\n손 기능에 영향을 주는 질환이 없는 자.", "과제별 양손 3D 운동학 수치의 정상 기준 분포(Median, Q1, Q3, n) 산출에만 사용. 환자 성능 데이터와 절대 합산하지 않음."],
        ["뇌졸중 환자군\n(Patient Cohort)", "15명", "뇌졸중 진단 후 3개월 이상 경과한 일측 편마비 성인.\nBrunnstrom 손 회복 3~5단계 (III~V).\n단순 지시를 이해하고 착석 수행이 가능한 자.", "본 연구의 주 가설 검정에 사용. 양손 동시 촬영을 수행하되, 마비측(Affected side) 결과를 주 분석으로, 비마비측을 보조로 분석."]
    ]
    add_styled_table(doc, subj_headers, subj_rows, [2.5, 1.8, 5.2, 6.4])

    add_h2(doc, "3.2 표본 수 15명의 학술적 근거와 파일럿 연구의 성격")
    add_para(doc, 
        "환자군 15명은 모집 실행 가능성, 임상 윤리적 부담, 전문가 2인의 이중 블라인드 판독 자원을 종합 고려하여 책정된 '탐색적 파일럿(Exploratory Pilot Study)' 표본이다. "
        "의학 연구 통계 가이드라인(Thabane et al., 2010; Lakens, 2022)에 명시된 바와 같이, 파일럿 연구의 목적은 확증적 우월성(Definitive Superiority)을 증명하는 것이 아니라, "
        "장비 측정의 실행 가능성(Feasibility), 결측률, 프로토콜 수용도, 그리고 효과 크기와 표준편차를 추정하여 후속 대규모 다기관 임상시험의 표본 설계를 위한 근거 파라미터를 도출하는 데 있다."
    )

    add_h2(doc, "3.3 윤리적 고려 및 데이터 보안 분리")
    add_para(doc, 
        "연구는 기관생명윤리위원회(IRB)의 정식 승인 및 피험자(또는 법정대리인)의 서면 동의 후 진행된다. "
        "비디오 촬영은 얼굴을 완전히 제외하고 양손 작업대 시야만 촬영한다. "
        "외부 상용 API를 완전히 배제하고 연구실 단일 워크스테이션(RTX 5090) 내에서 100% 로컬 오프라인 추론을 수행하므로, "
        "환자의 민감한 의료 영상 데이터가 외부 클라우드나 네트워크로 유출될 위험이 실질적으로 차단된다."
    )

    # =========================================================================
    # SECTION 4: 실험 장비 및 3D 운동학 변수 체계
    # =========================================================================
    add_h1(doc, "4. 실험 장비 및 3D 운동학 변수 체계")
    
    add_h2(doc, "4.1 장비 및 데이터 획득 설정")
    add_para(doc, 
        "센서 환경은 Intel RealSense D455 스테레오 RGB-D 카메라를 사용한다. "
        "RGB는 1280×720 @ 30 fps, Depth는 848×480 @ 30 fps 프로파일로 스트리밍되며, Intel RealSense SDK의 하드웨어 정렬(align_to=color)을 거쳐 "
        "RGB 프레임의 모든 픽셀에 깊이(Z, 미터) 정보가 1:1로 매핑된다. "
        "카메라는 작업면 중심으로부터 직선거리 70 cm, 수평면 대비 45° 부감(Top-front) 각도로 단단히 고정된다."
    )

    add_h2(doc, "4.2 운동학 수치 계산 구간 및 환자 반응 지연 고려 프로토콜 (3초 버퍼)")
    add_para(doc, 
        "한 시행은 준비, 목표 형성 시도, 유지, 해제의 순서로 진행한다. "
        "t0는 수행 시작 신호 시각, th는 참가자의 목표 자세 도달 및 유지 시작 시각, tr은 유지 완료 후 해제 신호 시각이다. "
        "특히 뇌졸중 환자는 신경학적 손상으로 인해 소리 신호에 대한 반응 시간(Reaction Time)이 0.5~1.0초 지연되며, "
        "정확히 2초를 맞추려는 강박은 불필요한 보상 운동이나 조기 손 풀림을 유발한다. "
        "따라서 임상 현장에서는 환자에게 '최대로 쥐고 속으로 셋을 세며 3초 정도 충분히 멈춘 뒤 편안하게 펴세요'라는 넉넉한 시간 버퍼 지시를 부여한다."
    )

    add_h3(doc, "4.2.1 속도 변곡점(Plateau) 기반 유지 구간 객관적 자동 검출 알고리즘")
    add_para(doc, 
        "연구자가 비디오를 육안으로 보며 자의적으로 유지 구간을 슬라이싱하는 주관적 편향(Cherry-picking)을 최소화하기 위해, "
        "본 연구는 3D 운동학 시계열에서 속도(Velocity) 기반의 수학적 변곡점(Inflection Points)을 알고리즘으로 자동 검출한다.\n"
        "1. 쥐는 동작의 속도 |v(t)|가 감속하여 평탄 임계치(10 mm/s) 이하로 진입하는 첫 번째 변곡점을 유지 시작점(t_onset_hold)으로 확정한다.\n"
        "2. 손을 다시 펴기 위해 속도가 다시 임계치를 초과하여 증가하는 두 번째 변곡점을 유지 종료점(t_offset_hold)으로 확정한다.\n"
        "3. 두 변곡점 사이의 시간 차이를 '실제 유지 시간(hold_duration_s = t_offset_hold − t_onset_hold)'으로 산출하며, "
        "이 값이 2.0초 이상일 때만 임상 기준의 '2초 유지 완료(Hold: Complete)'로 객관적 판정한다.\n"
        "4. 유지 구간 안정도(F3)는 환자 간 공정한 비교를 위해, 두 변곡점의 정중앙(Center) 시점을 기준으로 대칭인 중심 2.0초 표준 구간에서 표준편차(SD)를 산출한다."
    )

    add_h3(doc, "4.2.2 엄지-검지 파지폭(Aperture) 표준성과 관절 각도/속도 지표의 전략적 배치")
    add_para(doc, 
        "파지 과제에서 엄지 끝과 검지 끝 사이의 거리(Aperture)를 1차 핵심 지표로 채택한 이유는 생체역학 국제 표준(Jeannerod, 1984; Castiello, 2005)일 뿐 아니라, "
        "45° 부감 앵글에서 물체 및 손바닥에 의한 카메라 가림(Occlusion)이 적어 RealSense Depth의 결측(Hole) 위험이 상대적으로 낮기 때문이다. "
        "(맨손 과제는 이미 네 손가락 전체 평균 거리 r(t)로 분리 설계됨).\n"
        "한편, 본 연구실의 Mirror_therapy 시스템이 산출하는 풍부한 관절 각도(MCP/PIP/DIP ROM, TAM)와 각속도는 VLM 프롬프트에 모두 주입할 경우 "
        "모델의 주의력 분산(Attention Distraction) 및 프롬프트 과부하를 초래할 수 있으므로, VLM 주 입력은 3단계를 대변하는 F1~F4 정예 피처로 한정한다. "
        "대신 이들 전체 관절 각도와 속도 데이터는 순서형 로지스틱 회귀 기준 모델(A0)의 학습 피처 및 확장 소거 실험의 비교 검증 변수로 투입하여 학술적 깊이를 확보한다."
    )

    add_h2(doc, "4.3 물체 파지 과제 4대 핵심 운동학 피처")
    feat_headers = ["피처 ID 및 키", "변수명 및 공학적 조작 정의", "단위", "임상적 의미 및 선행연구 근거"]
    feat_rows = [
        ["F1\nacq_peak_span_mm", "동작 시작 신호 t0부터 유지 시작 변곡점 t_onset 사이 a(t)의 최댓값.\n(동률 시 최초 시점 사용, MGA: Maximum Grip Aperture)", "mm", "최대 파지 간격 (Peak Aperture / MGA). 물체 크기에 맞추어 손을 충분히 벌리는 파지 준비 능력 반영 (Qiu et al., 2022; Lang et al., 2005)."],
        ["F2\ntime_to_peak_s", "F1(최대 간격)이 발생한 시각에서 t0를 뺀 시간.\n(순수 초 단위로 보존, tMGA: Time to MGA)", "s", "최대 간격 도달 시간 (tMGA). 도달과 파지 개방의 시간적 협응 능력 반영 (Qiu et al., 2022; Broome et al., 2019)."],
        ["F3\nhold_span_sd_mm\n(보조: hold_duration_s)", "속도 변곡점 사이의 중심 2.0초 구간 a(t)의 표본 표준편차.\n(실제 유지 시간 hold_duration_s >= 2.0s 여부 동시 검증)", "mm", "파지 유지 안정도 (Hold Stability SD). 물체 접촉 후 불수의적 떨림이나 미끄러짐 없이 형태를 고정하는 능력 (연구용 조작 정의)."],
        ["F4\nrelease_span_change_mm", "해제 신호 tr 후 3.5~4.0초 구간 중앙값에서\ntr 직전 0.5초 구간 중앙값을 뺀 거리 변화량.", "mm", "능동 손가락 개방 변위 (Active Release Change). 쥐었던 손가락을 능동적으로 펴 물체와의 접촉을 해제하는 능력 (Lang et al., 2009)."]
    ]
    add_styled_table(doc, feat_headers, feat_rows, [2.8, 5.2, 1.2, 6.7])

    add_h2(doc, "4.4 맨손 쥐기/펴기 과제 4대 핵심 운동학 피처")
    free_headers = ["피처 ID 및 키", "변수명 및 공학적 조작 정의", "단위", "임상적 의미 및 선행연구 근거"]
    free_rows = [
        ["F1\nclosing_excursion_mm", "t0 직전 0.5초 r(t) 중앙값에서 획득 구간 최솟값을 뺀 값.\n(편 손 자세 대비 최대 주먹 굽힘 변위)", "mm", "능동 굴곡 변위 (Active Closing Excursion). 손가락 전체를 손바닥 쪽으로 주먹 쥐는 능력 (FMA 손 항목 굴곡 반영)."],
        ["F2\ntime_to_min_s", "획득 구간 r(t)의 최솟값이 최초 발생한 시각 − t0.", "s", "최대 주먹 도달 시간. 지시 후 능동 굴곡이 완성되는 속도 협응 반영 (Amprimo et al., 2024)."],
        ["F3\nhold_digit_sd_mm\n(보조: hold_duration_s)", "속도 변곡점 사이의 중심 2.0초 구간 동안 r(t)의 표본 표준편차.\n(실제 유지 시간 hold_duration_s >= 2.0s 여부 동시 검증)", "mm", "주먹 유지 안정도. 쥔 주먹 형태를 흔들림 없이 유지하는 능력."],
        ["F4\nreopening_change_mm", "tr 후 3.5~4.0초 r(t) 중앙값에서 tr 직전 0.5초 중앙값을 뺀 값.\n(주먹 상태 대비 손가락 재개방 변위)", "mm", "능동 신전 변위 (Active Reopening Excursion). 쥐었던 손가락을 능동적으로 펴는 회복 능력 (Lang et al., 2009)."]
    ]
    add_styled_table(doc, free_headers, free_rows, [2.8, 5.2, 1.2, 6.7])

    # =========================================================================
    # SECTION 5: 실험 프로토콜 및 영상 샘플링
    # =========================================================================
    add_h1(doc, "5. 실험 프로토콜 및 영상 샘플링")
    
    add_h2(doc, "5.1 4개 과제 사양 및 목표 파지 형태")
    task_headers = ["과제명", "대상 물체 규격 및 재질", "목표 파지 형태 (임상의 합의 기준)", "시작 위치 및 거리"]
    task_rows = [
        ["1. 맨손 쥐기와 펴기\n(Free Hand)", "물체 없음\n(테이블 위 맨손)", "검지·중지·약지·소지 네 손가락을 완전히 굽혀 손바닥에 닿는 주먹을 형성하고, 2초 유지 후 시작의 편 자세로 능동 개방.", "손바닥을 테이블에 편안히 내려놓은 시작 패드 위치."],
        ["2. 원통 파지\n(Cylinder Grasp)", "지름 5 cm, 높이 10 cm\n무광 PLA 원통 (질량 85g)", "엄지와 나머지 네 손가락이 원통 측면을 대향하여 완전히 감싸 쥐는 대향 파지 (Cylindrical Grasp).", "손끝 시작 위치에서 물체 전면까지 10 cm 직선 거리 고정."],
        ["3. 구형 파지\n(Spherical Grasp)", "지름 7 cm\n무광 PLA 구형체 (질량 75g)", "엄지와 굽힌 손가락들이 구면을 대향하여 둥글게 감싸 쥐는 형태. 굴러가지 않도록 5mm 낮은 링 받침대 사용.", "동일하게 손끝에서 물체 전면까지 10 cm 고정."],
        ["4. 측면 집기\n(Lateral Pinch)", "두께 1.5 cm, 폭 4 cm, 높이 7 cm\n무광 PLA 직육면체 블록", "검지 제2관절(PIP) 외측면에 물체를 대고, 엄지 손가락 끝으로 블록을 강하게 누르며 집는 형태 (Key pinch).", "동일하게 손끝에서 물체 전면까지 10 cm 고정."]
    ]
    add_styled_table(doc, task_headers, task_rows, [2.5, 3.2, 7.2, 3.0])

    add_h2(doc, "5.2 수행단계 기반 14프레임 층화 샘플링 규칙 (Phase-Stratified Sampling)")
    add_para(doc, 
        "전체 비디오를 단순히 시간 축에서 기계적으로 균등 분할하는 것이 아니라, "
        "임상적으로 의미가 뚜렷한 3단계(획득 6장 + 유지 2장 + 해제 6장)로 나누어 각 단계의 시간 전개에 맞추어 프레임을 층화 추출한다. "
        "이를 통해 동작 형성, 유지 안정성, 손가락 펴기 해제 과정의 핵심 시각적 순간을 모델에 효과적으로 전달한다."
    )
    frame_headers = ["동작 구간", "추출 프레임 수", "수학적 시간 선택 기준 (±0.05초 내 가장 가까운 원본 프레임)", "관찰 목표"]
    frame_rows = [
        ["획득 구간\n(t0 ~ th)", "6장", "t0부터 th까지 시간의 0%, 20%, 40%, 60%, 80%, 100% 시점 (F01 ~ F06)", "도달 중 손가락 사전 개방(Aperture opening) 및 물체 접촉 형성 과정."],
        ["유지 구간\n(th ~ tr)", "2장", "th + 0.5초, th + 1.5초 시점 (F07, F08)", "지정 2.0초 동안 목표 파지 형태 및 접촉의 안정적 유지 여부 확인."],
        ["해제 구간\n(tr ~ tr+4.0s)", "6장", "tr + 0.0s, tr + 0.8s, tr + 1.6s, tr + 2.4s, tr + 3.2s, tr + 4.0s (F09 ~ F14)", "손가락의 능동 신전에 의한 물체 분리 과정 및 잔여 굴곡 구축 관찰."]
    ]
    add_styled_table(doc, frame_headers, frame_rows, [2.5, 2.0, 7.5, 3.9])

    # =========================================================================
    # SECTION 6: VLM 모델 구성 및 단일 PC RTX 5090 환경
    # =========================================================================
    add_h1(doc, "6. VLM 모델 구성 및 단일 PC RTX 5090 환경")
    
    add_h2(doc, "6.1 단일 PC RTX 5090 (32GB VRAM) 하드웨어 환경 및 확정 모델 라인업")
    add_para(doc, 
        "본 연구는 외부 상용 API(Gemini, OpenAI 등)를 일체 사용하지 않으며, "
        "연구실 단일 워크스테이션(NVIDIA GeForce RTX 5090 32GB GDDR7, Blackwell 아키텍처)에서 100% 로컬 오프라인으로 구동된다. "
        "모델군은 최신 고성능 모델 2종과 선행연구 기준 재현 모델 3종으로 구성되었다. "
        "모든 모델은 14개 프레임 비전 토큰과 텍스트 프롬프트를 포함하여 32GB VRAM 내에서 안정적으로 구동 가능함을 사전 확인하였다."
    )
    
    vram_headers = ["모델 분류", "공식 모델 식별자 (HF Model ID)", "가중치 정밀도", "가중치 VRAM", "비전+KV캐시", "총 VRAM 점유량", "32GB 안전성"]
    vram_rows = [
        ["최신 모델 1\n(주 로컬 모델)", "Qwen/Qwen3-VL-8B-Instruct", "BF16 (16-bit)", "약 16.0 GB", "약 4.5 GB", "약 20.5 GB", "여유 11.5 GB (36% 마진)\n초고속 추론 안정성"],
        ["최신 모델 2\n(고성능 MoE)", "Qwen/Qwen3-VL-30B-A3B-Instruct", "AWQ (4-bit)", "약 16.5 GB", "약 6.0 GB", "약 22.5 GB", "여유 9.5 GB (30% 마진)\nMoE 고성능 단일 GPU 구동"],
        ["선행 재현 1\n(비디오 특화)", "lmms-lab/LLaVA-NeXT-Video-7B", "BF16 (16-bit)", "약 14.5 GB", "약 4.5 GB", "약 19.0 GB", "여유 13.0 GB (41% 마진)\n비디오 시계열 특화 벤치마크"],
        ["선행 재현 2\n(NYU 베이스 SOTA)", "Qwen/Qwen2.5-VL-32B-Instruct", "AWQ (4-bit)", "약 18.5 GB", "약 6.0 GB", "약 24.5 GB", "여유 7.5 GB (23% 마진)\nLi et al.(2026) 재현군"],
        ["선행 재현 3\n(멀티모달 표준)", "lmms-lab/llava-onevision-qwen2-7b-ov", "BF16 (16-bit)", "약 15.0 GB", "약 4.5 GB", "약 19.5 GB", "여유 12.5 GB (39% 마진)\nAnyRes 멀티프레임 표준 벤치마크"]
    ]
    add_styled_table(doc, vram_headers, vram_rows, [2.2, 4.2, 2.2, 1.8, 1.8, 2.0, 1.7])

    add_h2(doc, "6.2 공통 추론 설정 및 이미지 처리")
    add_para(doc, 
        "프롬프트는 지침과 입력 자료를 담은 요청문이며, 각 모델의 공식 입력 변환기와 표준 대화 형식을 사용한다. "
        "비교의 엄격성을 위해 공통 설정으로 BF16 정밀도, 배치 크기 1, 탐욕적 생성(do_sample=False, num_beams=1)을 적용하여 결정론적 출력을 유도한다. "
        "생성 토큰 상한은 max_new_tokens=1024, repetition_penalty=1.0으로 고정하며, "
        "메모리 절약을 위해 PyTorch의 스케일 점곱 주의 연산(SDPA)을 공통 활성화한다. "
        "외부 입력은 모든 모델에 896×504 크기의 동일한 14장 이미지를 시간순으로 제공한다."
    )

    add_h2(doc, "6.3 전체 추론 실행량 계획 및 구현 재현성 확인 (Implementation Reproducibility Check)")
    add_para(doc, 
        "5개 로컬 모델에 대한 전체 실행량 계획은 다음과 같이 체계적으로 산정된다. "
        "탐욕적 결정론적 생성(do_sample=False) 설정에서는 동일한 입력에 대해 일관된 출력이 보장되므로, "
        "모델의 확률적 변동성을 평가하는 무작위 반복 대신 '소프트웨어 파이프라인 무결성 및 구현 재현성 확인(Implementation Reproducibility Check)' 목적으로 "
        "대표 샘플에 대한 일치성 점검(1회 재실행)을 수행한다.\n"
        "1) 핵심 실행: 480개 환자 시행 × 4개 조건(A1~A4) × 5개 모델 = 9,600회.\n"
        "2) 피처 소거(D1~D4): 주 모델 480시행 × 4조건 = 1,920회.\n"
        "3) 구현 재현성 확인: 환자별 대표 시행(15명 × 4과제 = 60시행)에 대해 1회 재실행하여 파이프라인 입출력의 비트 수준 재현성을 점검함 (60시행 × 1회 = 60회).\n"
        "총 실행량은 약 11,580회 요청으로 합리화되며, RTX 5090의 고속 배치 추론 능력을 바탕으로 약 16~20시간 내에 전체 로컬 추론이 안정적으로 완결된다."
    )

    add_h2(doc, "6.4 전문가 기준과 연구용 과제 수행등급 (0/1/2점) 정의")
    rubric_headers = ["등급 코드", "명칭", "결정 규칙 (세부 동작 상태와의 1:1 매핑)", "비고"]
    rubric_rows = [
        ["0", "목표 형성 미완료\n(Incomplete Formation)", "목표 파지 형태(또는 맨손 주먹)를 지정 시간 내에 만들지 못함.\n(이후 유지 및 해제 항목은 자동으로 not_applicable 처리)", "도달 실패, 쥐기 불능,\n심각한 운동 장애."],
        ["1", "부분 수행 완료\n(Partial Completion)", "목표 파지 형태 형성은 완료하였으나,\n2초 유지(Hold) 또는 4초 내 능동 해제(Release) 중 1개 이상 미완료.", "형성은 되나 유지를 놓치거나\n손가락을 펴지 못하는 마비."],
        ["2", "전체 수행 완료\n(Full Completion)", "목표 파지 형태 형성, 2.0초간 형태 유지, 4.0초 내 능동 해제/펴기를\n모두 성공적으로 완료함.", "과제의 전 단계 정상 수행."],
        ["NA", "판독 불가 또는 중단\n(Unreadable)", "심한 가림으로 접촉을 확인할 수 없거나, 통증·피로로 중단된 경우.\n(또는 형성 완료 후 유지/해제 판독 근거가 부족한 경우)", "성능 평가 분모(Coverage) 계산 시\n분리 기록."]
    ]
    add_styled_table(doc, rubric_headers, rubric_rows, [1.5, 3.2, 8.5, 2.7])

    add_h2(doc, "6.5 시스템 프롬프트 및 구조화 JSON 출력 스키마")
    add_para(doc, 
        "VLM 모델은 최종 점수(0/1/2)를 직접 계산하지 않는다. 모델은 오직 각 손의 3단계 상태(target_formation, hold, active_release_or_opening)를 "
        "관찰된 영상 프레임 ID 또는 운동학 피처 키에 근거하여 complete / incomplete / unreadable 중 하나로 판정하고, "
        "외부 파이썬 코드가 위 표의 규칙에 따라 엄격하게 0, 1, 2점으로 결정론적 변환한다. 이를 통해 모델의 점수 왜곡 및 환각 위험을 크게 낮춘다."
    )
    json_example = (
        "{\n"
        '  "left_hand": {\n'
        '    "target_formation": {"status": "complete", "evidence": ["F05", "F06", "acq_peak_span_mm"], "reason": "Thumb and index fully opposed around cylinder"},\n'
        '    "hold": {"status": "complete", "evidence": ["F07", "F08", "hold_span_sd_mm"], "reason": "Maintained grasp for 2.0s without slippage"},\n'
        '    "active_release_or_opening": {"status": "incomplete", "evidence": ["F11", "F14", "release_span_change_mm"], "reason": "Fingers remained flexed, no active opening"},\n'
        '    "limitations": []\n'
        '  },\n'
        '  "right_hand": { ... }\n'
        "}"
    )
    add_code_box(doc, json_example)

    # =========================================================================
    # SECTION 7: 건강인 참조 규준 및 결측 처리
    # =========================================================================
    add_h1(doc, "7. 건강인 참조 규준 및 결측 처리 규칙")
    add_para(doc, 
        "건강인 15명의 양손 과제별 8회 반복 시행 중 유효 시행이 4회 이상인 경우 중앙값을 산출하여 참가자 대표값으로 정한다. "
        "해부학적 왼손과 오른손을 엄격히 구분하여 각 피처의 중앙값(Median), 1사분위수(Q1), 3사분위수(Q3), 실제 유효 인원(n)을 산출한다. "
        "센서 결측을 환자의 운동 실패로 오판하지 않도록 구간 유효율 80% 이상, 최장 결측 0.20초 이하, 평탄 신호(max-min < 5mm) 감지 등 공학적 품질 플래그를 모델에 동시 제공한다."
    )

    # =========================================================================
    # SECTION 8: 데이터 분석 및 통계 검정
    # =========================================================================
    add_h1(doc, "8. 데이터 분석 및 통계 검정")
    add_para(doc, 
        "주 분석은 주 모델의 첫 번째 계획 실행에서 전문가 기준 등급과 모델 등급이 모두 존재하는 공통 유효 시행을 대상으로 한다. "
        "환자별 A2 − A1 절대등급오차 차이 D_i의 15명 평균을 주 효과 추정치로 사용하며, 동일 환자의 조건 쌍을 복원 추출하는 "
        "환자 단위 10,000회 블록 부트스트랩(Seed 20260911)으로 95% 신뢰구간을 산출한다. "
        "또한 거대 VLM의 실용적 도입 타당성을 확인하기 위해 동일 수치를 사용하는 순서형 로지스틱 회귀 기준 모델 A0(L2-regularized Ordinal Logistic Regression, LOSO-CV 15-fold)와의 "
        "성능 비교(A3−A0) 및 비디오 정보의 순수 기여도를 확인하는 A3−A4 비교를 병행한다."
    )

    add_h2(doc, "8.1 결과 관찰 패턴별 사전 해석 기준표")
    int_headers = ["관찰 결과 패턴", "공학적 및 임상적 해석 기준"]
    int_rows = [
        ["차이 추정치가 음수이고 신뢰구간 전체가 0 아래", "해당 모델·과제·입력 조건에서 운동학 수치 추가에 따른 유의미한 오차 감소 근거. 등급 산출률(Coverage)과 실패 포함 민감도 결과가 일치하는지 확인."],
        ["신뢰구간이 0을 포함 (개선과 악화 양방향 포함)", "효과의 방향과 크기가 불확실함. '효과가 전혀 없다'거나 '두 조건이 같다'고 단정하지 않고 표본 불확실성으로 기술."],
        ["차이가 작고 신뢰구간이 0 근처에서 매우 좁음", "관찰 조건에서 추가 이득의 크기가 제한적일 가능성. 사전 동등성 설계가 아니므로 함부로 동등성을 선언하지 않음."],
        ["모델 또는 과제마다 효과 방향이 상이함", "운동학 수치 보완 효과가 특정 과제(물체 vs 맨손)나 모델 아키텍처에 의존함을 명시. 유리한 결과만 취사선택하지 않음."],
        ["평균 오차 감소와 유효 판독률(Coverage) 하락 동반", "판독하기 쉬운 시행만 남아 오차가 낮아 보이는 착시(Selection bias) 가능성. 최대 오차(2점)를 부여한 보수적 민감도 분석과 함께 해석."],
        ["다수 시행이 0점 또는 2점에 편중", "과제의 바닥·천장 효과(Floor/Ceiling effect) 확인. 새로운 척도 경계를 사후 도입하지 않고 분포 한계로 기술."]
    ]
    add_styled_table(doc, int_headers, int_rows, [5.5, 10.4])

    # =========================================================================
    # SECTION 9 ~ 11: 실행 기록, 연구 범위, 확인 체크리스트
    # =========================================================================
    add_h1(doc, "9. 실행 기록 및 재현성 관리")
    add_para(doc, 
        "모든 실험은 입력 비디오 해시(SHA-256), 추출 프레임 ID, 모델 Git Commit SHA, HuggingFace Revision ID, "
        "Python 환경 lock 파일, 추론 타임스탬프를 JSON Manifest 파일로 영구 저장한다."
    )

    add_h1(doc, "10. 연구 범위와 기대 기여")
    add_para(doc, 
        "본 연구는 제한된 환경에서 RGB-D 운동학 수치가 VLM의 손 과제 평가 능력을 보완할 수 있는지 확인하는 파일럿 타당성 연구이다. "
        "단독 무인 평가 시스템의 완성을 성급히 주장하지 않으며, 치료사의 비디오 판독 부담을 경감하기 위한 "
        "'사전 채점 초안 생성 및 이상 동작 탐지 보조 시스템'의 공학적 실행 가능성을 검증하는 데 학술적 기여가 있다."
    )

    add_h1(doc, "11. 시행 전 확인 체크리스트")
    chk_headers = ["점검 항목", "사전 확정 기준", "확인 방법 및 주체"]
    chk_rows = [
        ["하드웨어 및 드라이버", "NVIDIA RTX 5090 (32GB VRAM), CUDA 12.8+, PyTorch 2.6+", "GPU 인식 및 VRAM 할당 스크립트 실행 확인"],
        ["로컬 VLM 5종 로딩", "Qwen3-VL 2종, LLaVA-NeXT-Video, Qwen2.5-VL-32B, LLaVA-OneVision 로딩", "14프레임 더미 이미지 입력 추론 및 메모리 점유 확인"],
        ["카메라 정적 벤치마크", "70cm 거리에서 20·40·60·80mm 기준 블록 간격 오차 MAE ≤ 5 mm", "개발 건강인 4명 대상 3회 반복 측정 자체 검증"],
        ["전문가 라벨 기준 동결", "연구용 0/1/2/NA 등급 판정 문구 및 경계 사례 합의", "임상 치료사 2인 개발 데이터 연습 판독 완료"],
        ["IRB 및 개인정보", "IRB 정식 승인 번호 확보, 동의서 취득, 얼굴 제외 촬영 구도 고정", "데이터 관리 책임자 확인"]
    ]
    add_styled_table(doc, chk_headers, chk_rows, [3.2, 7.5, 5.2])

    # =========================================================================
    # SECTION 12: 참고문헌
    # =========================================================================
    add_h1(doc, "12. 참고문헌 (References)")
    refs = [
        "Amprimo, G., Masi, G., Pettiti, G., Olmo, G., Priano, L., & Ferraris, C. (2024). Hand tracking for clinical applications: Validation of the Google MediaPipe Hand (GMH) and the depth-enhanced GMH-D frameworks. Biomedical Signal Processing and Control, 96, 106508. https://doi.org/10.1016/j.bspc.2024.106508",
        "Broome, K., Hudson, I., Potter, K., Kulk, J., Dunn, A., Arm, J., Zeffiro, T., Cooper, G., Tian, H., & van Vliet, P. (2019). A modified reach-to-grasp task in a supine position shows coordination between elbow and hand movements after stroke. Frontiers in Neurology, 10, Article 408. https://doi.org/10.3389/fneur.2019.00408",
        "Fugl-Meyer, A. R., Jääskö, L., Leyman, I., Olsson, S., & Steglind, S. (1975). The post-stroke hemiplegic patient. 1. a method for evaluation of physical performance. Scandinavian Journal of Rehabilitation Medicine, 7(1), 13–31.",
        "Kim, D. W., Park, J. E., Kim, M. J., Byun, S. H., Jung, C. I., Jeong, H. M., Woo, S. R., Lee, K. H., Lee, M. H., Jung, J. W., Lee, D., Ryu, B. J., Yang, S. N., & Baek, S. J. (2024). Automatic assessment of upper extremity function and mobile application for self-administered stroke rehabilitation. IEEE Transactions on Neural Systems and Rehabilitation Engineering, 32, 652–661. https://doi.org/10.1109/TNSRE.2024.3358497",
        "Lakens, D. (2022). Sample size justification. Collabra: Psychology, 8(1), Article 33267. https://doi.org/10.1525/collabra.33267",
        "Lang, C. E., DeJong, S. L., & Beebe, J. A. (2009). Recovery of thumb and finger extension and its relation to grasp performance after stroke. Journal of Neurophysiology, 102(1), 451–459. https://doi.org/10.1152/jn.91310.2008",
        "Lang, C. E., Wagner, J. M., Bastian, A. J., Hu, Q., Edwards, D. F., Sahrmann, S. A., & Dromerick, A. W. (2005). Deficits in grasp versus reach during acute hemiparesis. Experimental Brain Research, 166, 126–136. https://doi.org/10.1007/s00221-005-2350-6",
        "Li, V., Kamalakannan, N., Parnandi, A., Schambra, H., & Fernandez-Granda, C. (2026). Vision-language models for human motion understanding: Lessons from stroke rehabilitation. PLOS Digital Health, 5(7), Article e0001506. https://doi.org/10.1371/journal.pdig.0001506",
        "LLaVA Team. (2024). LLaVA-NeXT: Stronger LLMs supercharge multimodal capabilities in video understanding. HuggingFace Model Hub. https://github.com/LLaVA-VL/LLaVA-NeXT",
        "LLaVA Team. (2024). LLaVA-OneVision: Easy visual task transfer. arXiv preprint arXiv:2408.03326.",
        "Parnandi, A., Kaku, A., Venkatesan, A., Pandit, N., Wirtanen, A., Rajamohan, H., Venkataramanan, K., Nilsen, D., Fernandez-Granda, C., & Schambra, H. (2022). PrimSeq: A deep learning-based pipeline to quantitate rehabilitation training. PLOS Digital Health, 1(6), Article e0000044. https://doi.org/10.1371/journal.pdig.0000044",
        "Qiu, Q., Fluet, G. G., Patel, J., Iyer, S., Karunakaran, K., Kaplan, E., Tunik, E., Nolan, K. J., Merians, A. S., Yarossi, M., & Adamovich, S. V. (2022). Evaluation of changes in kinematic measures of three dimensional reach to grasp movements in the early subacute period of recovery from stroke. 2022 44th Annual International Conference of the IEEE Engineering in Medicine & Biology Society (EMBC), 5107–5110. https://doi.org/10.1109/EMBC48229.2022.9871891",
        "Qwen Team. (2025). Qwen2.5-VL and Qwen3-VL technical reports. Alibaba Cloud. https://github.com/QwenLM/Qwen2.5-VL",
        "Tang, J., Abedi, A., Colella, T. J. F., & Khan, S. S. (2025). Rehabilitation exercise quality assessment and feedback generation using large language models with prompt engineering. In S. S. Khan et al. (Eds.), Artificial Intelligence for Aging Rehabilitation (CCIS Vol. 2620, pp. 60–75). Springer. https://doi.org/10.1007/978-981-95-0568-5_5",
        "Thabane, L., Ma, J., Chu, R., Cheng, J., Ismaila, A., Rios, L. P., Robson, R., Thabane, M., Giangregorio, L., & Goldsmith, C. H. (2010). A tutorial on pilot studies: The what, why and how. BMC Medical Research Methodology, 10, Article 1. https://doi.org/10.1186/1471-2288-10-1",
        "University of Gothenburg. (2024). Fugl-Meyer assessment of motor recovery after stroke: Upper extremity protocol (FM-UE). Gothenburg University Protocol.",
        "Wang, D., Yuan, K., Muller, C., Blanc, F., Padoy, N., & Seo, H. (2024). Enhancing gait video analysis in neurodegenerative diseases by knowledge augmentation in vision language model. In MICCAI 2024 (LNCS Vol. 15005, pp. 251–261). Springer. https://doi.org/10.1007/978-3-031-72086-4_24"
    ]
    for r in refs:
        p = add_para(doc, r, size_pt=8.8, space_after=3.5, line_spacing=1.05)
        p.paragraph_format.left_indent = Cm(0.8)
        p.paragraph_format.first_line_indent = Cm(-0.8)

    # =========================================================================
    # APPENDICES (부록 A 세부 로딩/버전 삭제 및 깔끔한 아키텍처 개요로 정돈)
    # =========================================================================
    add_h1(doc, "부록 A. 로컬 VLM 5종 모델 아키텍처 및 RTX 5090 32GB 운영 개요")
    add_para(doc, 
        "본 연구에서 단일 워크스테이션(NVIDIA GeForce RTX 5090 32GB VRAM) 환경에서 오프라인으로 운용하는 "
        "5개 오픈소스 VLM의 핵심 구성 및 정밀도는 다음과 같다. "
        "모든 모델은 14프레임 비전 토큰과 운동학 프롬프트를 포함하여 25GB 이하에서 안정적으로 동작하도록 배치된다."
    )
    app_a_headers = ["모델 구분", "공식 모델 식별자 (HF Model ID)", "가중치 정밀도", "총 VRAM 점유량", "선정 배경 및 주요 역할"]
    app_a_rows = [
        ["최신 주 로컬 모델", "Qwen/Qwen3-VL-8B-Instruct", "BF16 (16-bit)", "약 20.5 GB", "초고속 고효율 최신 모델, 피처 소거(D1~D4)를 포함한 주 가설 검증의 기준선."],
        ["최신 고성능 MoE", "Qwen/Qwen3-VL-30B-A3B-Instruct", "AWQ 4-bit", "약 22.5 GB", "단일 GPU에서 30B급 MoE 아키텍처의 고수준 시각 추론 능력 평가."],
        ["선행 비디오 재현", "lmms-lab/LLaVA-NeXT-Video-7B", "BF16 (16-bit)", "약 19.0 GB", "다중 프레임 시계열 역학을 보존하는 비디오 특화 모델의 순수 영상 한계 및 수치 보완 효과 검증."],
        ["선행 SOTA 재현", "Qwen/Qwen2.5-VL-32B-Instruct", "AWQ 4-bit", "약 24.5 GB", "NYU Li et al. (2026) 연구의 핵심 기준 32B 모델 성능 직접 재현 및 3D 수치 결합 효과 비교."],
        ["선행 멀티모달 재현", "lmms-lab/llava-onevision-qwen2-7b-ov", "BF16 (16-bit)", "약 19.5 GB", "단일 프레임 및 다중 프레임 통합 처리 능력을 갖춘 오픈소스 멀티모달 대표 기준선."]
    ]
    add_styled_table(doc, app_a_headers, app_a_rows, [2.5, 4.2, 2.2, 2.0, 5.0])

    add_h1(doc, "부록 B. 공통 영문 시스템 프롬프트 지침 (System Rubric)")
    sys_prompt = (
        "You are an expert clinical movement annotator evaluating stroke hand rehabilitation tasks. "
        "Your task is to independently evaluate the participant's left and right hands using ONLY the supplied task instructions, "
        "14-frame sequential images, and extracted 3D kinematic metrics.\n\n"
        "Rules:\n"
        "1. Do not hallucinate actions between frames. Return valid JSON only.\n"
        "2. Assess each hand separately across 3 phases: target_formation, hold, and active_release_or_opening.\n"
        "3. Allowed status values: 'complete', 'incomplete', 'unreadable', or 'not_applicable'.\n"
        "4. Target formation is judged at hold marker (th). Hold requires maintaining configuration/contacts for full 2.0s without slippage. "
        "Active release requires voluntary finger extension ending object contact within 4.0s after release cue (tr).\n"
        "5. For object tasks, arm withdrawal without active finger extension is incomplete.\n"
        "6. If target_formation is incomplete, set subsequent hold and release to 'not_applicable'.\n"
        "7. For every judgment, cite specific evidence using supplied frame IDs (F01-F14) and kinematic feature keys (F1-F4)."
    )
    add_code_box(doc, sys_prompt)

    add_h1(doc, "부록 C. 선행 운동학 피처와 본 연구 채택의 관계 비교표")
    app_c_headers = ["선행연구 원형 변수", "원 논문 출처", "본 연구 채택 변수 및 조작 정의", "차용 사유 및 임상적 정당화"]
    app_c_rows = [
        ["Peak aperture\nTime to peak aperture", "Qiu et al. (2022)\nLang et al. (2005)", "물체 F1(acq_peak_span_mm)\n물체 F2(time_to_peak_s)", "도달 중 손가락 사전 개방 폭과 개방 타이밍 협응을 반영. FMA 상지 점수와 밀접히 연동되는 핵심 지표."],
        ["Aperture path ratio\nPeak aperture velocity", "Lang et al. (2005, 2009)", "본 연구 파일럿에서 주 입력 제외", "미분량 및 궤적비는 잡음 민감도가 높아 마커리스 깊이 센서의 추가 오차 유발 위험. 향후 후속 연구로 유보."],
        ["Active finger extension\nexcursion (각도 ROM)", "Lang et al. (2009)", "맨손 F1(closing), F4(reopening)\n(손끝-손목 거리 변화량, mm)", "관절 각도(ROM) 대신 3D 거리 변위를 측정하여 센서 가림 오차를 최소화하면서 굴곡/신전 능력의 핵심을 보존."],
        ["Depth-enhanced distance\ntime-series (GMH-D)", "Amprimo et al. (2024)", "MediaPipe 2D 관절 + 실측 깊이 역투영 원리 참고", "선행 GMH-D 원리를 참고하되, 본 연구의 RealSense D455 환경에서 정적 블록 오차 벤치마크(MAE ≤ 5mm)를 통해 독자적 측정 검증 수행."],
        ["Grip force / EMG", "다수 임상 논문", "본 연구에서 미채택", "D455 비접촉 광학 센서만으로 힘이나 근활성을 직접 측정했다고 주장할 수 없으므로 형태적 접촉/분리 관찰에 한정."]
    ]
    add_styled_table(doc, app_c_headers, app_c_rows, [3.2, 3.2, 4.5, 5.0])

    add_h1(doc, "부록 D. 핵심 베이스 선행연구 9편 상세 학술 분석 리포트")
    app_d_cases = [
        ("D1. Li 등 (2026, PLOS Digital Health) · 순수 영상 VLM의 시각적 환각과 본 연구의 출발점", [
            "■ 연구 개요: 건강인 20명, 뇌졸중 환자 51명의 대규모 재활 데이터셋에서 15개 최신 VLM(Qwen2.5-VL-7B 포함)의 동작 이해 및 임상 평가 능력을 전면 평가함.",
            "■ 주요 결과: 일상 활동 분류에서는 77.5% 정확도를 보였으나, 미세 동작 정량화 및 FMA 손상 점수 예측에서는 정확도가 크게 저하됨. 환자의 손이 물체에 스치기만 해도 파지로 오판하는 '시각적 접촉 환각'이 다수 관찰됨.",
            "■ 본 연구와의 연결: 본 연구의 주 비교(A2 − A1)를 도출한 직접적인 베이스 연구임. 2D 영상의 시각적 환각 한계를 실증함으로써, 본 연구가 제안하는 물리적 3D 센서 거리·시간 수치(F1~F4) 보완의 가설적 근거를 제공함."
        ]),
        ("D2. LLaVA-NeXT-Video & LLaVA-OneVision · 다중 프레임 및 비디오 시계열 기준 벤치마크", [
            "■ 연구 개요: 연속 프레임 간의 시간적 역학(Temporal dynamics)과 공간 해상도를 보존하는 비디오 특화 오픈소스 VLM 아키텍처 제시.",
            "■ 본 연구와의 연결: 뇌졸중 손 과제에서 비디오 특화 모델이라 할지라도 순수 영상만으로는 파지 접촉 환각을 피하기 어려움을 교차 검증하는 핵심 베이스라인 모델로 선정함."
        ]),
        ("D3. Amprimo 등 (2024, BSPC) · RGB-D 기반 3D 손 운동학 추출의 타당성", [
            "■ 연구 개요: Google MediaPipe 손 추적기에 Depth 센서(Microsoft Azure Kinect DK)를 결합한 GMH-D 시스템을 제안하고, 120 fps OptiTrack 광학 모션캡처(6-camera)와 동시 비교 검증함.",
            "■ 주요 결과: 손끝 거리 및 변위 시계열이 고가 모션캡처 장비와 매우 높은 상관성과 일치도(Bland-Altman)를 보임을 실증함.",
            "■ 본 연구와의 연결: 마커리스 깊이 결합 손 추적(GMH-D)의 방법론적 타당성 근거를 제공함. 단, 선행연구는 Azure Kinect 환경에서 검증되었으므로, 본 연구의 Intel RealSense D455 환경에서는 정적 블록(20~80mm) 측정 검증을 별도로 수행하여 신뢰성을 확보함."
        ]),
        ("D4. Lang 등 (2005, 2009, Exp Brain Res & J Neurophysiol) · 파지 간격과 손가락 신전의 임상 분리", [
            "■ 연구 개요: 편마비 환자의 reach-to-grasp에서 최대 파지 간격과 도달 궤적의 손상을 분석하고, 발병 3주와 13주 추적을 통해 손가락별 신전 회복이 파지 성공의 독립적 전제조건임을 규명함.",
            "■ 본 연구와의 연결: 물체 과제의 파지 간격 피처(F1, F2)와 맨손 과제의 손가락 신전 피처(F4)를 분리하여 설계한 임상적 이론 기반을 제공함."
        ]),
        ("D5. Qiu 등 (2022, IEEE EMBC) · 아급성기 뇌졸중 파지 간격 및 도달 시간 지표", [
            "■ 연구 개요: 뇌졸중 아급성기 환자의 도달-파지 동작 3D 운동학을 분석하여, 최대 파지 간격(Peak Aperture)과 도달 시점(TMGA)이 FMA 점수 회복과 유의한 상관관계가 있음을 밝힘.",
            "■ 본 연구와의 연결: 본 연구의 핵심 운동학 피처 F1(최대 간격)과 F2(최대 간격 발생 시점)의 선정 근거로 직결됨."
        ]),
        ("D6. Tang 등 (2025, Springer) · 수치 정보를 LLM에 주입하는 프롬프팅 선행 연구", [
            "■ 연구 개요: 관절 각도 수치를 대규모 언어모델(GPT-4o)에 텍스트로 전달하여 운동 적절성을 제로샷/퓨샷으로 평가함.",
            "■ 본 연구와의 연결: 본 연구의 A4(수치 전용 소거 조건)를 둔 직접적인 선행 사례이며, 수치 텍스트 프롬프팅의 가능성과 한계를 비교하는 기준이 됨."
        ]),
        ("D7. Wang 등 (2024, MICCAI) · 임상 수치와 설명을 결합한 지식 증강 VLM", [
            "■ 연구 개요: 신경퇴행질환 보행 영상에 GAITRite 보행 수치와 의학적 텍스트를 결합하여 질환 분류 정확도를 개선함.",
            "■ 본 연구와의 연결: 건강인 참조 규준(A3)을 결합하여 모델의 판단 기준을 보강하는 설계의 이론적 정당성을 제공함."
        ]),
        ("D8. Kim 등 (2024, IEEE TNSRE) · 상지 기능 자동 평가 및 모바일 앱 연동", [
            "■ 연구 개요: 뇌졸중 환자의 reach-to-grasp 영상을 자동 평가하고 자가 재활 앱과 연동하는 딥러닝 시스템 개발.",
            "■ 본 연구와의 연결: AI 기반 재활 평가가 향후 치료사 보조 및 원격 재활로 확장될 수 있는 실용적 잠재력을 제시함."
        ]),
        ("D9. Parnandi 등 (2022, PrimSeq, PLOS Digital Health) · 비디오 평가 자동화의 절실함", [
            "■ 연구 개요: 뇌졸중 환자 재활 비디오 분석에서 사람 수작업 주석 513.6시간 vs AI 1.4시간 소요 실증.",
            "■ 본 연구와의 연결: 본 연구가 왜 자동화된 사전 채점 보조 시스템을 개발해야 하는지 사회적·임상적 필요성을 대변함."
        ])
    ]
    for title, points in app_d_cases:
        add_callout(doc, title, points, border_color='1E4E8C', bg_color='F8FAFD')

    # Save exclusively to the brand-new requested file: 연구계획서20260911_통합본_최종수정본.docx
    out_new = Path(r"C:\Users\passp\OneDrive\바탕 화면\jeayong\capstone\연구계획서20260911_통합본_최종수정본.docx")
    doc.save(str(out_new))
    print(f"Successfully generated brand-new revised proposal: {out_new}")

if __name__ == '__main__':
    create_revised_proposal()
