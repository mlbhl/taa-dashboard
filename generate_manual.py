"""TAA Dashboard 매뉴얼 PDF 생성 스크립트"""
from fpdf import FPDF

FONT_R = "/usr/share/fonts/truetype/nanum/NanumGothic.ttf"
FONT_B = "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf"
FONT_MONO = "/usr/share/fonts/truetype/nanum/NanumGothicCodingBold.ttf"

class Manual(FPDF):
    def __init__(self):
        super().__init__()
        self.add_font("ng", "", FONT_R)
        self.add_font("ng", "B", FONT_B)
        self.add_font("mono", "", FONT_MONO)
        self.set_auto_page_break(auto=True, margin=20)

    def section_title(self, text):
        self.ln(6)
        self.set_font("ng", "B", 14)
        self.cell(0, 10, text, new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def sub_title(self, text):
        self.ln(3)
        self.set_font("ng", "B", 11)
        self.cell(0, 8, text, new_x="LMARGIN", new_y="NEXT")
        self.ln(1)

    def body(self, text):
        self.set_font("ng", "", 10)
        self.set_x(self.l_margin)
        self.multi_cell(0, 6, text)

    def body_bold(self, text):
        self.set_font("ng", "B", 10)
        self.set_x(self.l_margin)
        self.multi_cell(0, 6, text)

    def mono(self, text):
        self.set_font("mono", "", 8)
        self.set_x(self.l_margin)
        self.multi_cell(0, 5, text)
        self.set_font("ng", "", 10)

    def bullet(self, text):
        self.set_font("ng", "", 10)
        self.set_x(self.l_margin)
        self.multi_cell(0, 6, "  " + text)

    def table(self, headers, rows, col_widths=None):
        if col_widths is None:
            w = (self.w - 20) / len(headers)
            col_widths = [w] * len(headers)
        # header
        self.set_font("ng", "B", 9)
        for i, h in enumerate(headers):
            self.cell(col_widths[i], 7, h, border=1, align="C")
        self.ln()
        # rows
        self.set_font("ng", "", 9)
        for row in rows:
            for i, val in enumerate(row):
                self.cell(col_widths[i], 7, str(val), border=1, align="C")
            self.ln()
        self.ln(2)


pdf = Manual()
pdf.add_page()

# ── Title ──
pdf.set_font("ng", "B", 18)
pdf.cell(0, 12, "TAA Dashboard - 매뉴얼", new_x="LMARGIN", new_y="NEXT")
pdf.ln(4)

# ── 1. 핵심 아이디어 ──
pdf.section_title("1. 핵심 아이디어")
pdf.body(
    "TAA 시그널 방향에 따라 틸트(tilt)를 가감하여 Final 비중을 산출합니다. "
    "두 가지 모드를 제공하며, 라디오 버튼으로 전환할 수 있습니다."
)
pdf.ln(1)
pdf.body_bold("[모드 A] Peer 기준 (비대칭 Tilt)")
pdf.body(
    "Peer 평균을 출발점으로, SAA가 Tilt의 크기(|SAA-Peer|)와 "
    "방향 판정(aligned/opposed)을 모두 결정합니다. "
    "Signal이 SAA 쪽으로 향하면 적극적으로, 반대 방향이면 억제합니다."
)
pdf.ln(1)
pdf.body_bold("[모드 B] 가중 평균 기준 (Base 비례 Tilt)")
pdf.body(
    "SAA와 Peer의 가중 평균(Base)을 출발점으로 사용합니다. "
    "Tilt는 Base에 비례하여 산출되며, 비중이 큰 자산일수록 조정 여지가 커집니다. "
    "비대칭 Tilt나 Damping 개념이 없는 대칭적 방식입니다."
)

# ── 2. 공식 ──
pdf.section_title("2. 공식")

# ── 2A. Peer 기준 ──
pdf.body_bold("━━━ 모드 A: Peer 기준 (비대칭 Tilt) ━━━")
pdf.ln(1)

pdf.sub_title("Step 1. Signal 변환")
pdf.mono("  Signal_i = TAA 의견의 수치 변환")
pdf.body("TAA 5단계 의견을 -2 ~ +2 수치로 매핑합니다.")
pdf.ln(1)

pdf.sub_title("Step 2. Tilt 계산 (비대칭, SAA 앵커)")
pdf.mono("  Tilt_i = max( |SAA_i - Peer_i| * d_i,  Peer_i * MinTiltRate )")
pdf.ln(1)
pdf.body("여기서 d_i는 Signal 방향과 SAA 위치 관계에 따라 결정됩니다:")
pdf.ln(1)
pdf.bullet("d = 1.0 - Signal이 Peer에서 SAA 쪽으로 향할 때 (적극적 틸트)")
pdf.bullet("d = Damping - Signal이 SAA 반대 쪽으로 향할 때 (억제)")
pdf.ln(1)
pdf.body(
    "SAA = Peer인 경우 |SAA - Peer| = 0이 되어 Tilt가 0이 됩니다. "
    "이를 방지하기 위해 Min Tilt Rate를 적용하여 최소 Tilt = Peer × MinTiltRate를 보장합니다."
)
pdf.ln(1)
pdf.body_bold("판정 기준:  Signal * (SAA - Peer) >= 0 이면 aligned (d=1.0), 아니면 opposed (d=Damping)")
pdf.ln(2)

pdf.sub_title("Step 3. Adjustment 계산")
pdf.mono("  Adj_i = a * Signal_i * Tilt_i")
pdf.ln(1)

pdf.sub_title("Step 4. Raw 비중")
pdf.mono("  Raw_i = max( Peer_i + Adj_i,  1.0 )")
pdf.body("각 지역의 Raw 비중이 1.0% 미만으로 내려가지 않도록 하한선(floor)을 적용합니다.")
pdf.ln(1)

pdf.sub_title("Step 5. Final 정규화")
pdf.mono("  Final_i = Raw_i / Sum(Raw_j) * 100")
pdf.ln(1)

pdf.sub_title("Step 6. Range (범위)")
pdf.mono("  Final >= 10% -> +/- 5%p")
pdf.mono("  Final <  10% -> +/- 2.5%p")
pdf.body(
    "Final 값의 크기에 따라 디폴트 상하 범위가 자동 설정됩니다. "
    "Range Confirmation 테이블에서 Low/High를 수기로 조정한 뒤 '범위 확정' 버튼으로 확정합니다."
)

# ── 2B. 가중 평균 기준 ──
pdf.ln(4)
pdf.body_bold("━━━ 모드 B: 가중 평균 기준 (Base 비례 Tilt) ━━━")
pdf.ln(1)

pdf.sub_title("Step 1. Signal 변환")
pdf.mono("  Signal_i = TAA 의견의 수치 변환")
pdf.body("모드 A와 동일합니다.")
pdf.ln(1)

pdf.sub_title("Step 2. Base 계산")
pdf.mono("  Base_i = w * SAA_i + (1 - w) * Peer_i")
pdf.ln(1)
pdf.body("SAA 가중치(w)에 따라 출발점이 결정됩니다:")
pdf.bullet("w = 0.0: Base = Peer (Peer만 반영)")
pdf.bullet("w = 0.5: Base = (SAA + Peer) / 2 (균등 평균)")
pdf.bullet("w = 1.0: Base = SAA (SAA만 반영)")
pdf.ln(1)

pdf.sub_title("Step 3. Tilt 계산 (Base 비례)")
pdf.mono("  Tilt_i = Base_i * TiltRate")
pdf.ln(1)
pdf.body(
    "Base에 비례하여 Tilt가 결정됩니다. "
    "비중이 큰 자산은 조정 여지가 크고, 작은 자산은 조정이 작습니다. "
    "모드 A와 달리 비대칭 Tilt나 Damping 개념이 없습니다."
)
pdf.ln(1)

pdf.sub_title("Step 4. Adjustment 계산")
pdf.mono("  Adj_i = a * Signal_i * Tilt_i")
pdf.ln(1)

pdf.sub_title("Step 5. Raw 비중")
pdf.mono("  Raw_i = max( Base_i + Adj_i,  1.0 )")
pdf.body("모드 A와 동일하게 1.0% 하한선(floor)을 적용합니다.")
pdf.ln(1)

pdf.sub_title("Step 6. Final 정규화")
pdf.mono("  Final_i = Raw_i / Sum(Raw_j) * 100")
pdf.ln(1)

pdf.sub_title("Step 7. Range (범위)")
pdf.body("모드 A와 동일한 디폴트 범위 규칙이 적용됩니다.")

# ── 두 모드 비교 ──
pdf.ln(2)
pdf.sub_title("두 모드 비교 요약")
pdf.table(
    ["항목", "모드 A (Peer 기준)", "모드 B (가중 평균 기준)"],
    [
        ["출발점", "Peer", "w*SAA + (1-w)*Peer"],
        ["Tilt", "|SAA-Peer| * d", "Base * TiltRate"],
        ["비대칭", "O (Damping)", "X"],
        ["SAA 역할", "Tilt 크기 및 방향 결정", "Base에 직접 반영"],
        ["Neutral 시", "Final ≈ Peer", "Final ≈ Base"],
    ],
    [25, 55, 55],
)

# ── 3. 파라미터 ──
pdf.section_title("3. 파라미터")

pdf.sub_title("TAA Signal (5단계) — 공통")
pdf.table(
    ["TAA 레벨", "Signal 값", "의미"],
    [
        ["Strong OW", "+2", "강한 비중확대"],
        ["Overweight", "+1", "비중확대"],
        ["Neutral", "0", "중립"],
        ["Underweight", "-1", "비중축소"],
        ["Strong UW", "-2", "강한 비중축소"],
    ],
    [40, 30, 60],
)

pdf.sub_title("α (확신도) — 공통")
pdf.bullet("범위: 0.0 ~ 1.0 (슬라이더로 조정)")
pdf.bullet("α = 0: Active bet 없음, Final = 출발점(Peer 또는 Base) 그대로")
pdf.bullet("α = 0.5: 기본값, 적당한 틸트")
pdf.bullet("α = 1.0: 최대 확신, 최대 틸트")
pdf.ln(1)

pdf.sub_title("Damping (반대방향 억제) — 모드 A 전용")
pdf.bullet("범위: 0.0 ~ 1.0 (슬라이더로 조정)")
pdf.bullet("기본값: 0.25")
pdf.bullet("Signal이 SAA 반대 방향일 때 Tilt에 적용되는 계수")
pdf.bullet("0에 가까울수록 반대방향 베팅을 강하게 억제")
pdf.bullet("1.0이면 방향에 관계없이 동일한 Tilt 적용 (억제 없음)")
pdf.ln(1)

pdf.sub_title("Min Tilt Rate (최소 틸트 비율) — 모드 A 전용")
pdf.bullet("범위: 0% ~ 50% (슬라이더로 조정)")
pdf.bullet("기본값: 20%")
pdf.bullet("SAA = Peer인 경우에도 최소 Tilt = Peer × MinTiltRate 보장")
pdf.bullet("0%이면 SAA = Peer일 때 Signal이 작동하지 않음")
pdf.ln(1)

pdf.sub_title("SAA 가중치 w — 모드 B 전용")
pdf.bullet("범위: 0.0 ~ 1.0 (슬라이더로 조정)")
pdf.bullet("기본값: 0.5")
pdf.bullet("Base = w × SAA + (1-w) × Peer")
pdf.bullet("w = 0이면 Peer 100% 반영, w = 1이면 SAA 100% 반영")
pdf.ln(1)

pdf.sub_title("Tilt Rate — 모드 B 전용")
pdf.bullet("범위: 0% ~ 50% (슬라이더로 조정)")
pdf.bullet("기본값: 20%")
pdf.bullet("Tilt = Base × TiltRate")
pdf.bullet("비중이 큰 자산일수록 Tilt가 커져 조정 여지가 확대됨")
pdf.ln(1)

pdf.sub_title("Floor — 공통")
pdf.body("각 지역의 Raw 비중이 1.0% 미만으로 내려가지 않도록 하한선(floor)을 적용합니다.")

# ── 4. 기본 데이터 ──
pdf.section_title("4. 기본 데이터 (Default)")
pdf.body("주식 70%, 채권 30% 기준으로 자산군 내 비중을 스케일링한 값입니다.")
pdf.ln(2)

pdf.sub_title("주식 (70%)")
pdf.table(
    ["지역", "내부비중", "SAA (스케일)", "Peer (스케일)"],
    [
        ["미국", "70%", "49.0%", "45.5%"],
        ["유럽", "15%", "10.5%", "12.6%"],
        ["일본", "5%", "3.5%", "3.5%"],
        ["중국", "3%", "2.1%", "3.5%"],
        ["한국", "5%", "3.5%", "2.1%"],
        ["기타", "2%", "1.4%", "2.8%"],
    ],
    [30, 30, 35, 35],
)

pdf.sub_title("채권 (30%)")
pdf.table(
    ["지역", "내부비중", "SAA (스케일)", "Peer (스케일)"],
    [
        ["미국", "70%", "21.0%", "18.0%"],
        ["한국", "30%", "9.0%", "12.0%"],
    ],
    [30, 30, 35, 35],
)

pdf.body("SAA 합계 = 100%, Peer 합계 = 100%. 사용자가 자유롭게 수정할 수 있습니다.")

# ── 5. 적용 예시 ──
pdf.section_title("5. 적용 예시")

pdf.sub_title("예시 A: Peer 기준 모드")
pdf.body("α = 0.5, Damping = 0.25, Min Tilt Rate = 20%")
pdf.body("주식 미국 OW / 주식 중국 UW / 채권 미국 Strong OW 설정 시:")
pdf.ln(2)

pdf.table(
    ["자산", "지역", "SAA", "Peer", "TAA", "Signal", "Tilt", "Adj", "Raw", "Final"],
    [
        ["주식", "미국", "49.0", "45.5", "OW", "+1", "9.10", "+4.55", "50.05", "46.58"],
        ["주식", "유럽", "10.5", "12.6", "N", "0", "2.52", "0", "12.60", "11.73"],
        ["주식", "일본", "3.5", "3.5", "N", "0", "0.70", "0", "3.50", "3.26"],
        ["주식", "중국", "2.1", "3.5", "UW", "-1", "1.40", "-0.70", "2.80", "2.61"],
        ["주식", "한국", "3.5", "2.1", "N", "0", "1.40", "0", "2.10", "1.95"],
        ["주식", "기타", "1.4", "2.8", "N", "0", "1.40", "0", "2.80", "2.61"],
        ["채권", "미국", "21.0", "18.0", "SOW", "+2", "3.60", "+3.60", "21.60", "20.10"],
        ["채권", "한국", "9.0", "12.0", "N", "0", "3.00", "0", "12.00", "11.17"],
    ],
    [12, 12, 12, 12, 12, 14, 12, 12, 12, 12],
)

pdf.sub_title("비대칭 Tilt 상세")
pdf.body(
    "• 주식 미국 (SAA=49 > Peer=45.5, OW): SAA 방향 → d=1.0\n"
    "    Tilt = max(|49-45.5|×1.0, 45.5×0.2) = max(3.5, 9.1) = 9.10\n"
    "• 주식 중국 (SAA=2.1 < Peer=3.5, UW): SAA 방향 → d=1.0\n"
    "    Tilt = max(|2.1-3.5|×1.0, 3.5×0.2) = max(1.4, 0.7) = 1.40\n"
    "• 채권 미국 (SAA=21 > Peer=18, SOW): SAA 방향 → d=1.0\n"
    "    Tilt = max(|21-18|×1.0, 18×0.2) = max(3.0, 3.6) = 3.60"
)
pdf.ln(2)

pdf.sub_title("예시 B: 가중 평균 기준 모드")
pdf.body("α = 0.5, SAA 가중치(w) = 0.5, Tilt Rate = 20%")
pdf.body("동일한 TAA 설정 (주식 미국 OW / 주식 중국 UW / 채권 미국 Strong OW):")
pdf.ln(2)

pdf.table(
    ["자산", "지역", "SAA", "Peer", "Base", "TAA", "Signal", "Tilt", "Adj", "Final"],
    [
        ["주식", "미국", "49.0", "45.5", "47.25", "OW", "+1", "9.45", "+4.73", "47.97"],
        ["주식", "유럽", "10.5", "12.6", "11.55", "N", "0", "2.31", "0", "10.66"],
        ["주식", "일본", "3.5", "3.5", "3.50", "N", "0", "0.70", "0", "3.23"],
        ["주식", "중국", "2.1", "3.5", "2.80", "UW", "-1", "0.56", "-0.28", "2.33"],
        ["주식", "한국", "3.5", "2.1", "2.80", "N", "0", "0.56", "0", "2.58"],
        ["주식", "기타", "1.4", "2.8", "2.10", "N", "0", "0.42", "0", "1.94"],
        ["채권", "미국", "21.0", "18.0", "19.50", "SOW", "+2", "3.90", "+3.90", "21.60"],
        ["채권", "한국", "9.0", "12.0", "10.50", "N", "0", "2.10", "0", "9.69"],
    ],
    [12, 12, 10, 10, 10, 10, 14, 10, 10, 12],
)

pdf.body(
    "• Base = 0.5×SAA + 0.5×Peer → Neutral이어도 Peer가 아닌 SAA-Peer 중간점 출발\n"
    "• Tilt = Base × 20% → 비중이 큰 자산(미국 47.25%)의 Tilt가 자연스럽게 큼\n"
    "• 방향 비대칭(Damping) 없이 대칭적으로 Signal 적용"
)

# ── 6. 왜 이 방식이 작동하는가 ──
pdf.section_title("6. 왜 이 방식이 작동하는가")

pdf.sub_title("모드 A (Peer 기준)")
pdf.body(
    "1. Peer를 출발점으로 쓰기 때문에 Peer 대비 tracking error가 관리됩니다.\n\n"
    "2. TAA가 맞으면 OW 지역이 outperform → Peer 대비 초과수익이 발생합니다.\n\n"
    "3. TAA가 틀려도 비대칭 Tilt 덕분에 SAA 반대 방향 베팅은 억제되어 "
    "underperformance가 제한적입니다.\n\n"
    "4. SAA 앵커 효과: Signal이 SAA 쪽으로 향하면 적극적 Tilt, "
    "반대 방향이면 Damping만큼 억제하여 과도한 쏠림을 방지합니다.\n\n"
    "5. Min Tilt Rate: SAA = Peer인 지역에서도 TAA 시그널이 작동하도록 "
    "최소한의 Tilt를 보장합니다."
)
pdf.ln(2)

pdf.sub_title("모드 B (가중 평균 기준)")
pdf.body(
    "1. SAA의 장기 전략적 관점을 출발점(Base)에 직접 반영합니다.\n\n"
    "2. w 조절로 SAA와 Peer 사이에서 유연하게 기준점을 설정할 수 있습니다.\n\n"
    "3. Base 비례 Tilt: 비중이 큰 자산은 조정 여지가 크고, "
    "작은 자산은 자연스럽게 조정이 제한됩니다.\n\n"
    "4. 대칭적 구조: 방향에 따른 편향 없이 Signal을 균등하게 적용합니다.\n\n"
    "5. 단, w가 높으면 Peer와의 괴리가 커질 수 있으므로 "
    "tracking error 관리에 유의가 필요합니다."
)

# ── 7. 대시보드 UI ──
pdf.section_title("7. 대시보드 UI 구성")

pdf.sub_title("Parameters")
pdf.body(
    "• 모드 선택 라디오 버튼: 'Peer 기준 (비대칭 Tilt)' / '가중 평균 기준 (Base 비례 Tilt)'\n"
    "• α 슬라이더: 확신도 조절 (공통)\n"
    "• [모드 A] Damping 슬라이더 + Min Tilt Rate 슬라이더\n"
    "• [모드 B] SAA 가중치(w) 슬라이더 + Tilt Rate 슬라이더\n"
    "  → 모드 전환 시 해당 슬라이더만 표시됩니다."
)
pdf.ln(1)

pdf.sub_title("Region Inputs")
pdf.body(
    "• 자산(주식/채권), 지역, SAA(%), Peer(%), TAA를 직접 편집 가능\n"
    "• TAA 드롭다운: Strong OW / Overweight / Neutral / Underweight / Strong UW\n"
    "• 행 추가/삭제 가능"
)
pdf.ln(1)

pdf.sub_title("Range Confirmation")
pdf.body(
    "• Final 값의 크기에 따라 디폴트 범위(Low/High)가 자동 생성\n"
    "  - Final >= 10%: ±5%p / Final < 10%: ±2.5%p\n"
    "• Low/High 셀을 수기로 조정 가능\n"
    "• '범위 확정' 버튼 클릭으로 확정\n"
    "• 입력(SAA/Peer/TAA/α/모드 등)이 변경되면 자동으로 리셋"
)
pdf.ln(1)

pdf.sub_title("Final Allocation")
pdf.body(
    "• 각 자산/지역별 Final 비중 카드 + 범위(Low ~ High) 표시\n"
    "• vs Peer 차이 표시\n"
    "• SAA / Peer / Final 비교 바 차트 (Final에 범위 error bar 포함)"
)
pdf.ln(1)

pdf.sub_title("Active Bets vs Peer")
pdf.body("• Overweight / Underweight 포지션 목록\n• Total Active Risk (one-way %p)")
pdf.ln(1)

pdf.sub_title("Detailed Breakdown")
pdf.body(
    "• [모드 A] SAA, Peer, TAA, Signal, Tilt, Adj, Raw, Final, Low, High, vs Peer\n"
    "• [모드 B] SAA, Peer, Base, TAA, Signal, Tilt, Adj, Raw, Final, Low, High, vs Peer\n"
    "  → 모드 B에서는 Base 컬럼이 추가로 표시됩니다."
)
pdf.ln(1)

pdf.sub_title("Formula Reference")
pdf.body("• 현재 선택된 모드의 공식과 파라미터 값이 실시간으로 표시됩니다.")

# ── 8. 실행 ──
pdf.section_title("8. 실행 방법")
pdf.mono("  pip install dash pandas plotly")
pdf.mono("  python taa_portfolio_optimizer.py")
pdf.ln(1)


# ── Save ──
output_path = "/home/byoun/projects/taa-dashboard/taa-dashboard-manual.pdf"
pdf.output(output_path)
print(f"PDF saved: {output_path}")
