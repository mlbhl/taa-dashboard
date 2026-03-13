"""
taa_portfolio_optimizer.py의 계산 로직을 Excel 수식으로 구현하는 스크립트.
두 시트: (1) Peer 기준 모드, (2) 가중 평균 기준 모드
"""

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side, numbers
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

# ── 스타일 정의 ──
ACCENT = "6366F1"
HEADER_FILL = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
HEADER_FONT = Font(name="맑은 고딕", size=10, bold=True, color="475569")
TITLE_FONT = Font(name="맑은 고딕", size=14, bold=True, color="1E293B")
SECTION_FONT = Font(name="맑은 고딕", size=11, bold=True, color=ACCENT)
CELL_FONT = Font(name="맑은 고딕", size=10, color="1E293B")
DIM_FONT = Font(name="맑은 고딕", size=9, color="94A3B8")
PARAM_FONT = Font(name="맑은 고딕", size=10, bold=True, color=ACCENT)
INPUT_FILL = PatternFill(start_color="FFFBEB", end_color="FFFBEB", fill_type="solid")
RESULT_FILL = PatternFill(start_color="EEF2FF", end_color="EEF2FF", fill_type="solid")
GREEN_FONT = Font(name="맑은 고딕", size=10, bold=True, color="059669")
RED_FONT = Font(name="맑은 고딕", size=10, bold=True, color="DC2626")
THIN_BORDER = Border(
    bottom=Side(style="thin", color="E2E8F0"),
)
BOTTOM_BORDER = Border(
    bottom=Side(style="medium", color="CBD5E1"),
)

# ── 기본 데이터 ──
DEFAULT_DATA = [
    ("주식", "미국", 49.0, 45.5, "Neutral"),
    ("주식", "유럽", 10.5, 12.6, "Neutral"),
    ("주식", "일본",  3.5,  3.5, "Neutral"),
    ("주식", "중국",  2.1,  3.5, "Neutral"),
    ("주식", "한국",  3.5,  2.1, "Neutral"),
    ("주식", "기타",  1.4,  2.8, "Neutral"),
    ("채권", "미국", 21.0, 18.0, "Neutral"),
    ("채권", "한국",  9.0, 12.0, "Neutral"),
]

TAA_OPTIONS = ["Strong OW", "Overweight", "Neutral", "Underweight", "Strong UW"]
N = len(DEFAULT_DATA)


def set_col_widths(ws, widths):
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w


def write_header_row(ws, row, headers, start_col=1):
    for i, h in enumerate(headers):
        c = ws.cell(row=row, column=start_col + i, value=h)
        c.font = HEADER_FONT
        c.fill = HEADER_FILL
        c.alignment = Alignment(horizontal="center", vertical="center")
        c.border = BOTTOM_BORDER


def apply_data_style(ws, row, col, font=CELL_FONT, alignment=None, fill=None, border=THIN_BORDER, number_format=None):
    c = ws.cell(row=row, column=col)
    c.font = font
    if alignment:
        c.alignment = alignment
    if fill:
        c.fill = fill
    if border:
        c.border = border
    if number_format:
        c.number_format = number_format
    return c


def build_peer_sheet(wb):
    """Peer 기준 모드 시트"""
    ws = wb.active
    ws.title = "Peer 기준"
    set_col_widths(ws, [3, 8, 8, 10, 10, 14, 10, 10, 10, 10, 10, 10, 10, 10, 12])

    # ── Title ──
    ws.merge_cells("B1:H1")
    ws["B1"] = "TAA Dashboard — Peer 기준 (비대칭 Tilt)"
    ws["B1"].font = TITLE_FONT

    # ── Parameters ──
    ws["B3"] = "Parameters"
    ws["B3"].font = SECTION_FONT

    params = [
        ("B4", "α (확신도)", "C4", 0.50),
        ("B5", "Damping (반대방향)", "C5", 0.25),
        ("B6", "Min Tilt Rate", "C6", 0.20),
    ]
    for label_cell, label, val_cell, val in params:
        ws[label_cell] = label
        ws[label_cell].font = CELL_FONT
        c = ws[val_cell]
        c.value = val
        c.font = PARAM_FONT
        c.fill = INPUT_FILL
        c.number_format = "0.00"
        c.alignment = Alignment(horizontal="center")

    ws["E4"] = "← 0~1 (보수적 → 적극적)"
    ws["E4"].font = DIM_FONT
    ws["E5"] = "← 0~1 (0=강한억제, 1=억제없음)"
    ws["E5"].font = DIM_FONT
    ws["E6"] = "← gap=0일 때 최소 Tilt 보장율"
    ws["E6"].font = DIM_FONT

    # ── TAA Signal 매핑 참조 ──
    ws["H3"] = "TAA Signal 매핑"
    ws["H3"].font = SECTION_FONT
    mapping = [("Strong OW", 2), ("Overweight", 1), ("Neutral", 0), ("Underweight", -1), ("Strong UW", -2)]
    for i, (label, val) in enumerate(mapping):
        ws.cell(row=4 + i, column=8, value=label).font = CELL_FONT
        ws.cell(row=4 + i, column=9, value=val).font = PARAM_FONT
        ws.cell(row=4 + i, column=9).alignment = Alignment(horizontal="center")

    # ── Input Table ──
    DATA_START = 10
    ws[f"B{DATA_START - 1}"] = "Region Inputs"
    ws[f"B{DATA_START - 1}"].font = SECTION_FONT

    headers = ["자산", "지역", "SAA(%)", "Peer(%)", "TAA"]
    write_header_row(ws, DATA_START, headers, start_col=2)

    # TAA 드롭다운 유효성 검사
    dv = DataValidation(type="list", formula1='"Strong OW,Overweight,Neutral,Underweight,Strong UW"', allow_blank=True)
    dv.error = "TAA 옵션에서 선택하세요"
    dv.errorTitle = "잘못된 입력"
    ws.add_data_validation(dv)

    for i, (asset, region, saa, peer, taa) in enumerate(DEFAULT_DATA):
        r = DATA_START + 1 + i
        ws.cell(row=r, column=2, value=asset).font = Font(name="맑은 고딕", size=10, bold=True, color=ACCENT)
        ws.cell(row=r, column=3, value=region).font = Font(name="맑은 고딕", size=10, bold=True)
        c_saa = ws.cell(row=r, column=4, value=saa)
        c_saa.font = CELL_FONT
        c_saa.fill = INPUT_FILL
        c_saa.number_format = "0.0"
        c_saa.alignment = Alignment(horizontal="center")
        c_peer = ws.cell(row=r, column=5, value=peer)
        c_peer.font = CELL_FONT
        c_peer.fill = INPUT_FILL
        c_peer.number_format = "0.0"
        c_peer.alignment = Alignment(horizontal="center")
        c_taa = ws.cell(row=r, column=6, value=taa)
        c_taa.font = CELL_FONT
        c_taa.fill = INPUT_FILL
        c_taa.alignment = Alignment(horizontal="center")
        dv.add(c_taa)
        for col in range(2, 7):
            ws.cell(row=r, column=col).border = THIN_BORDER

    # ── Calculation Table ──
    CALC_START = DATA_START + N + 3
    ws[f"B{CALC_START - 1}"] = "Calculation"
    ws[f"B{CALC_START - 1}"].font = SECTION_FONT

    calc_headers = ["자산", "지역", "SAA", "Peer", "Signal", "Gap", "Aligned?", "Damping", "Min Tilt", "Tilt", "Adj", "Raw", "Final(%)", "vs Peer"]
    write_header_row(ws, CALC_START, calc_headers, start_col=2)

    # Named references for parameters
    alpha_ref = "$C$4"
    damping_ref = "$C$5"
    mintilt_ref = "$C$6"

    for i in range(N):
        r = CALC_START + 1 + i
        dr = DATA_START + 1 + i  # data row

        # 자산, 지역 (참조)
        ws.cell(row=r, column=2).value = f"=B{dr}"
        ws.cell(row=r, column=2).font = Font(name="맑은 고딕", size=10, bold=True, color=ACCENT)
        ws.cell(row=r, column=3).value = f"=C{dr}"
        ws.cell(row=r, column=3).font = Font(name="맑은 고딕", size=10, bold=True)

        # SAA, Peer (참조)
        ws.cell(row=r, column=4).value = f"=D{dr}"
        ws.cell(row=r, column=4).number_format = "0.0"
        ws.cell(row=r, column=5).value = f"=E{dr}"
        ws.cell(row=r, column=5).number_format = "0.0"

        # Signal = VLOOKUP 또는 중첩 IF
        # Signal: TAA → 숫자 변환
        taa_cell = f"F{dr}"
        ws.cell(row=r, column=6).value = (
            f'=IF({taa_cell}="Strong OW",2,'
            f'IF({taa_cell}="Overweight",1,'
            f'IF({taa_cell}="Neutral",0,'
            f'IF({taa_cell}="Underweight",-1,'
            f'IF({taa_cell}="Strong UW",-2,0)))))'
        )
        ws.cell(row=r, column=6).number_format = "0"

        # Gap = SAA - Peer
        ws.cell(row=r, column=7).value = f"=D{r}-E{r}"
        ws.cell(row=r, column=7).number_format = "0.00"

        # Aligned? = (Signal * Gap >= 0) → 1 or 0
        ws.cell(row=r, column=8).value = f"=IF(F{r}*G{r}>=0,1,0)"
        ws.cell(row=r, column=8).number_format = "0"

        # Damping = Aligned * (1 - damping_opposed) + damping_opposed
        ws.cell(row=r, column=9).value = f"=H{r}*(1-{damping_ref})+{damping_ref}"
        ws.cell(row=r, column=9).number_format = "0.00"

        # Min Tilt = Peer * min_tilt_rate
        ws.cell(row=r, column=10).value = f"=E{r}*{mintilt_ref}"
        ws.cell(row=r, column=10).number_format = "0.00"

        # Tilt = MAX(ABS(Gap) * Damping, Min Tilt)
        ws.cell(row=r, column=11).value = f"=MAX(ABS(G{r})*I{r}, J{r})"
        ws.cell(row=r, column=11).number_format = "0.00"

        # Adj = α * Signal * Tilt
        ws.cell(row=r, column=12).value = f"={alpha_ref}*F{r}*K{r}"
        ws.cell(row=r, column=12).number_format = "+0.00;-0.00;0.00"

        # Raw = MAX(Peer + Adj, 1.0)
        ws.cell(row=r, column=13).value = f"=MAX(E{r}+L{r}, 1.0)"
        ws.cell(row=r, column=13).number_format = "0.00"

        # Final(%) = Raw / SUM(Raw) * 100
        raw_range = f"M{CALC_START+1}:M{CALC_START+N}"
        ws.cell(row=r, column=14).value = f"=ROUND(M{r}/SUM({raw_range})*100, 2)"
        ws.cell(row=r, column=14).number_format = "0.00"
        ws.cell(row=r, column=14).fill = RESULT_FILL
        ws.cell(row=r, column=14).font = Font(name="맑은 고딕", size=10, bold=True)

        # vs Peer = Final - Peer
        ws.cell(row=r, column=15).value = f"=ROUND(N{r}-E{r}, 2)"
        ws.cell(row=r, column=15).number_format = "+0.00;-0.00;0.00"

        # 스타일
        for col in range(2, 16):
            c = ws.cell(row=r, column=col)
            if not c.font or c.font == Font():
                c.font = CELL_FONT
            c.alignment = Alignment(horizontal="center")
            c.border = THIN_BORDER

    # ── 합계 행 ──
    sum_row = CALC_START + N + 1
    ws.cell(row=sum_row, column=2, value="합계").font = Font(name="맑은 고딕", size=10, bold=True)
    for col in [4, 5, 13, 14]:
        rng = f"{get_column_letter(col)}{CALC_START+1}:{get_column_letter(col)}{CALC_START+N}"
        ws.cell(row=sum_row, column=col).value = f"=SUM({rng})"
        ws.cell(row=sum_row, column=col).font = Font(name="맑은 고딕", size=10, bold=True)
        ws.cell(row=sum_row, column=col).number_format = "0.0"
        ws.cell(row=sum_row, column=col).alignment = Alignment(horizontal="center")
        ws.cell(row=sum_row, column=col).border = Border(top=Side(style="medium", color="CBD5E1"))

    # ── Range (범위) ──
    RANGE_START = sum_row + 3
    ws[f"B{RANGE_START - 1}"] = "Range (허용 범위)"
    ws[f"B{RANGE_START - 1}"].font = SECTION_FONT

    range_headers = ["자산", "지역", "Final(%)", "Half Width", "Low(%)", "High(%)"]
    write_header_row(ws, RANGE_START, range_headers, start_col=2)

    for i in range(N):
        r = RANGE_START + 1 + i
        cr = CALC_START + 1 + i

        ws.cell(row=r, column=2).value = f"=B{cr}"
        ws.cell(row=r, column=2).font = Font(name="맑은 고딕", size=10, bold=True, color=ACCENT)
        ws.cell(row=r, column=3).value = f"=C{cr}"
        ws.cell(row=r, column=3).font = Font(name="맑은 고딕", size=10, bold=True)

        # Final 참조
        ws.cell(row=r, column=4).value = f"=N{cr}"
        ws.cell(row=r, column=4).number_format = "0.00"
        ws.cell(row=r, column=4).fill = RESULT_FILL

        # Half Width: >=20 → 7.5, >=10 → 5.0, else 2.5
        ws.cell(row=r, column=5).value = f'=IF(D{r}>=20, 7.5, IF(D{r}>=10, 5.0, 2.5))'
        ws.cell(row=r, column=5).number_format = "0.0"

        # Low = MAX(Final - HalfWidth, 0)
        ws.cell(row=r, column=6).value = f"=ROUND(MAX(D{r}-E{r}, 0), 2)"
        ws.cell(row=r, column=6).number_format = "0.00"
        ws.cell(row=r, column=6).fill = INPUT_FILL

        # High = Final + HalfWidth
        ws.cell(row=r, column=7).value = f"=ROUND(D{r}+E{r}, 2)"
        ws.cell(row=r, column=7).number_format = "0.00"
        ws.cell(row=r, column=7).fill = INPUT_FILL

        for col in range(2, 8):
            c = ws.cell(row=r, column=col)
            if not c.font or c.font == Font():
                c.font = CELL_FONT
            c.alignment = Alignment(horizontal="center")
            c.border = THIN_BORDER

    # ── Formula Reference ──
    FORMULA_START = RANGE_START + N + 3
    ws[f"B{FORMULA_START}"] = "Formula Reference"
    ws[f"B{FORMULA_START}"].font = SECTION_FONT
    formulas = [
        "1. Signal_i = TAA 의견 → 수치 (SOW=+2, OW=+1, N=0, UW=-1, SUW=-2)",
        "2. Gap_i = SAA_i - Peer_i",
        "3. Aligned = 1 if Signal×Gap ≥ 0, else 0",
        "4. Damping_i = Aligned × (1 - d) + d    (d = Damping 파라미터)",
        "5. Tilt_i = MAX( |Gap_i| × Damping_i,  Peer_i × Min Tilt Rate )",
        "6. Adj_i = α × Signal_i × Tilt_i",
        "7. Raw_i = MAX( Peer_i + Adj_i,  1.0 )",
        "8. Final_i = Raw_i / Σ Raw_j × 100",
        "9. Range: Final ≥ 20% → ±7.5%p, ≥ 10% → ±5%p, < 10% → ±2.5%p",
    ]
    for i, f in enumerate(formulas):
        ws.cell(row=FORMULA_START + 1 + i, column=2, value=f).font = Font(name="맑은 고딕", size=9, color="475569")

    return ws


def build_weighted_sheet(wb):
    """가중 평균 기준 모드 시트"""
    ws = wb.create_sheet("가중 평균 기준")
    set_col_widths(ws, [3, 8, 8, 10, 10, 14, 10, 10, 10, 10, 10, 10, 10, 12])

    # ── Title ──
    ws.merge_cells("B1:H1")
    ws["B1"] = "TAA Dashboard — 가중 평균 기준 (Base 비례 Tilt)"
    ws["B1"].font = TITLE_FONT

    # ── Parameters ──
    ws["B3"] = "Parameters"
    ws["B3"].font = SECTION_FONT

    params = [
        ("B4", "α (확신도)", "C4", 0.50),
        ("B5", "SAA 가중치 (w)", "C5", 0.50),
        ("B6", "Tilt Rate", "C6", 0.20),
    ]
    for label_cell, label, val_cell, val in params:
        ws[label_cell] = label
        ws[label_cell].font = CELL_FONT
        c = ws[val_cell]
        c.value = val
        c.font = PARAM_FONT
        c.fill = INPUT_FILL
        c.number_format = "0.00"
        c.alignment = Alignment(horizontal="center")

    ws["E4"] = "← 0~1 (보수적 → 적극적)"
    ws["E4"].font = DIM_FONT
    ws["E5"] = "← 0=Peer중심, 1=SAA중심"
    ws["E5"].font = DIM_FONT
    ws["E6"] = "← Base 대비 Tilt 비율"
    ws["E6"].font = DIM_FONT

    # ── TAA Signal 매핑 참조 ──
    ws["H3"] = "TAA Signal 매핑"
    ws["H3"].font = SECTION_FONT
    mapping = [("Strong OW", 2), ("Overweight", 1), ("Neutral", 0), ("Underweight", -1), ("Strong UW", -2)]
    for i, (label, val) in enumerate(mapping):
        ws.cell(row=4 + i, column=8, value=label).font = CELL_FONT
        ws.cell(row=4 + i, column=9, value=val).font = PARAM_FONT
        ws.cell(row=4 + i, column=9).alignment = Alignment(horizontal="center")

    # ── Input Table ──
    DATA_START = 10
    ws[f"B{DATA_START - 1}"] = "Region Inputs"
    ws[f"B{DATA_START - 1}"].font = SECTION_FONT

    headers = ["자산", "지역", "SAA(%)", "Peer(%)", "TAA"]
    write_header_row(ws, DATA_START, headers, start_col=2)

    dv = DataValidation(type="list", formula1='"Strong OW,Overweight,Neutral,Underweight,Strong UW"', allow_blank=True)
    ws.add_data_validation(dv)

    for i, (asset, region, saa, peer, taa) in enumerate(DEFAULT_DATA):
        r = DATA_START + 1 + i
        ws.cell(row=r, column=2, value=asset).font = Font(name="맑은 고딕", size=10, bold=True, color=ACCENT)
        ws.cell(row=r, column=3, value=region).font = Font(name="맑은 고딕", size=10, bold=True)
        c_saa = ws.cell(row=r, column=4, value=saa)
        c_saa.font = CELL_FONT
        c_saa.fill = INPUT_FILL
        c_saa.number_format = "0.0"
        c_saa.alignment = Alignment(horizontal="center")
        c_peer = ws.cell(row=r, column=5, value=peer)
        c_peer.font = CELL_FONT
        c_peer.fill = INPUT_FILL
        c_peer.number_format = "0.0"
        c_peer.alignment = Alignment(horizontal="center")
        c_taa = ws.cell(row=r, column=6, value=taa)
        c_taa.font = CELL_FONT
        c_taa.fill = INPUT_FILL
        c_taa.alignment = Alignment(horizontal="center")
        dv.add(c_taa)
        for col in range(2, 7):
            ws.cell(row=r, column=col).border = THIN_BORDER

    # ── Calculation Table ──
    CALC_START = DATA_START + N + 3
    ws[f"B{CALC_START - 1}"] = "Calculation"
    ws[f"B{CALC_START - 1}"].font = SECTION_FONT

    calc_headers = ["자산", "지역", "SAA", "Peer", "Signal", "Base", "Tilt", "Adj", "Raw", "Final(%)", "vs Peer"]
    write_header_row(ws, CALC_START, calc_headers, start_col=2)

    alpha_ref = "$C$4"
    w_ref = "$C$5"
    tilt_rate_ref = "$C$6"

    for i in range(N):
        r = CALC_START + 1 + i
        dr = DATA_START + 1 + i

        # 자산, 지역
        ws.cell(row=r, column=2).value = f"=B{dr}"
        ws.cell(row=r, column=2).font = Font(name="맑은 고딕", size=10, bold=True, color=ACCENT)
        ws.cell(row=r, column=3).value = f"=C{dr}"
        ws.cell(row=r, column=3).font = Font(name="맑은 고딕", size=10, bold=True)

        # SAA, Peer
        ws.cell(row=r, column=4).value = f"=D{dr}"
        ws.cell(row=r, column=4).number_format = "0.0"
        ws.cell(row=r, column=5).value = f"=E{dr}"
        ws.cell(row=r, column=5).number_format = "0.0"

        # Signal
        taa_cell = f"F{dr}"
        ws.cell(row=r, column=6).value = (
            f'=IF({taa_cell}="Strong OW",2,'
            f'IF({taa_cell}="Overweight",1,'
            f'IF({taa_cell}="Neutral",0,'
            f'IF({taa_cell}="Underweight",-1,'
            f'IF({taa_cell}="Strong UW",-2,0)))))'
        )
        ws.cell(row=r, column=6).number_format = "0"

        # Base = w * SAA + (1-w) * Peer
        ws.cell(row=r, column=7).value = f"={w_ref}*D{r}+(1-{w_ref})*E{r}"
        ws.cell(row=r, column=7).number_format = "0.00"

        # Tilt = Base * tilt_rate
        ws.cell(row=r, column=8).value = f"=G{r}*{tilt_rate_ref}"
        ws.cell(row=r, column=8).number_format = "0.00"

        # Adj = α * Signal * Tilt
        ws.cell(row=r, column=9).value = f"={alpha_ref}*F{r}*H{r}"
        ws.cell(row=r, column=9).number_format = "+0.00;-0.00;0.00"

        # Raw = MAX(Base + Adj, 1.0)
        ws.cell(row=r, column=10).value = f"=MAX(G{r}+I{r}, 1.0)"
        ws.cell(row=r, column=10).number_format = "0.00"

        # Final(%) = Raw / SUM(Raw) * 100
        raw_range = f"J{CALC_START+1}:J{CALC_START+N}"
        ws.cell(row=r, column=11).value = f"=ROUND(J{r}/SUM({raw_range})*100, 2)"
        ws.cell(row=r, column=11).number_format = "0.00"
        ws.cell(row=r, column=11).fill = RESULT_FILL
        ws.cell(row=r, column=11).font = Font(name="맑은 고딕", size=10, bold=True)

        # vs Peer = Final - Peer
        ws.cell(row=r, column=12).value = f"=ROUND(K{r}-E{r}, 2)"
        ws.cell(row=r, column=12).number_format = "+0.00;-0.00;0.00"

        for col in range(2, 13):
            c = ws.cell(row=r, column=col)
            if not c.font or c.font == Font():
                c.font = CELL_FONT
            c.alignment = Alignment(horizontal="center")
            c.border = THIN_BORDER

    # ── 합계 행 ──
    sum_row = CALC_START + N + 1
    ws.cell(row=sum_row, column=2, value="합계").font = Font(name="맑은 고딕", size=10, bold=True)
    for col in [4, 5, 7, 10, 11]:
        rng = f"{get_column_letter(col)}{CALC_START+1}:{get_column_letter(col)}{CALC_START+N}"
        ws.cell(row=sum_row, column=col).value = f"=SUM({rng})"
        ws.cell(row=sum_row, column=col).font = Font(name="맑은 고딕", size=10, bold=True)
        ws.cell(row=sum_row, column=col).number_format = "0.0"
        ws.cell(row=sum_row, column=col).alignment = Alignment(horizontal="center")
        ws.cell(row=sum_row, column=col).border = Border(top=Side(style="medium", color="CBD5E1"))

    # ── Range (범위) ──
    RANGE_START = sum_row + 3
    ws[f"B{RANGE_START - 1}"] = "Range (허용 범위)"
    ws[f"B{RANGE_START - 1}"].font = SECTION_FONT

    range_headers = ["자산", "지역", "Final(%)", "Half Width", "Low(%)", "High(%)"]
    write_header_row(ws, RANGE_START, range_headers, start_col=2)

    for i in range(N):
        r = RANGE_START + 1 + i
        cr = CALC_START + 1 + i

        ws.cell(row=r, column=2).value = f"=B{cr}"
        ws.cell(row=r, column=2).font = Font(name="맑은 고딕", size=10, bold=True, color=ACCENT)
        ws.cell(row=r, column=3).value = f"=C{cr}"
        ws.cell(row=r, column=3).font = Font(name="맑은 고딕", size=10, bold=True)

        ws.cell(row=r, column=4).value = f"=K{cr}"
        ws.cell(row=r, column=4).number_format = "0.00"
        ws.cell(row=r, column=4).fill = RESULT_FILL

        ws.cell(row=r, column=5).value = f'=IF(D{r}>=20, 7.5, IF(D{r}>=10, 5.0, 2.5))'
        ws.cell(row=r, column=5).number_format = "0.0"

        ws.cell(row=r, column=6).value = f"=ROUND(MAX(D{r}-E{r}, 0), 2)"
        ws.cell(row=r, column=6).number_format = "0.00"
        ws.cell(row=r, column=6).fill = INPUT_FILL

        ws.cell(row=r, column=7).value = f"=ROUND(D{r}+E{r}, 2)"
        ws.cell(row=r, column=7).number_format = "0.00"
        ws.cell(row=r, column=7).fill = INPUT_FILL

        for col in range(2, 8):
            c = ws.cell(row=r, column=col)
            if not c.font or c.font == Font():
                c.font = CELL_FONT
            c.alignment = Alignment(horizontal="center")
            c.border = THIN_BORDER

    # ── Formula Reference ──
    FORMULA_START = RANGE_START + N + 3
    ws[f"B{FORMULA_START}"] = "Formula Reference"
    ws[f"B{FORMULA_START}"].font = SECTION_FONT
    formulas = [
        "1. Signal_i = TAA 의견 → 수치 (SOW=+2, OW=+1, N=0, UW=-1, SUW=-2)",
        "2. Base_i = w × SAA_i + (1-w) × Peer_i",
        "3. Tilt_i = Base_i × Tilt Rate",
        "4. Adj_i = α × Signal_i × Tilt_i",
        "5. Raw_i = MAX( Base_i + Adj_i,  1.0 )",
        "6. Final_i = Raw_i / Σ Raw_j × 100",
        "7. Range: Final ≥ 20% → ±7.5%p, ≥ 10% → ±5%p, < 10% → ±2.5%p",
    ]
    for i, f in enumerate(formulas):
        ws.cell(row=FORMULA_START + 1 + i, column=2, value=f).font = Font(name="맑은 고딕", size=9, color="475569")

    return ws


def main():
    wb = openpyxl.Workbook()
    build_peer_sheet(wb)
    build_weighted_sheet(wb)

    output_path = "/home/byoun/projects/taa-dashboard/TAA_Dashboard.xlsx"
    wb.save(output_path)
    print(f"Excel 파일 생성 완료: {output_path}")


if __name__ == "__main__":
    main()
