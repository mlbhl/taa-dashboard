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
    "View 시그널 방향에 따라 틸트(tilt)를 가감하여 TAA 비중을 산출합니다. "
    "2단계 배분 방식을 사용합니다."
)
pdf.ln(1)
pdf.body_bold("Step 1: 자산군 시그널 → 주식/채권 총비중 (SAA 기준)")
pdf.body(
    "자산군(주식/채권) 시그널의 점수 차이에 따라 SAA 대비 비중을 조정합니다. "
    "shift = (주식점수 - 채권점수) × 2.5%p"
)
pdf.ln(1)
pdf.body_bold("Step 2: 개별 시그널 → Base 비례 Tilt로 자산군 내 배분")
pdf.body(
    "SAA와 Peer의 가중 평균(Base)을 출발점으로 사용합니다. "
    "Tilt는 Base에 비례하여 산출되며, 비중이 큰 자산일수록 조정 여지가 커집니다. "
    "대칭적 구조로 Signal을 균등하게 적용합니다."
)

# ── 2. 공식 ──
pdf.section_title("2. 공식")

pdf.sub_title("Step 1. 자산군 비중 결정 (SAA 기준)")
pdf.mono("  shift = (equity_score - bond_score) * 2.5%p")
pdf.mono("  equity_total = MAX(SAA_equity + shift, 0)")
pdf.mono("  bond_total = MAX(SAA_bond - shift, 0)")
pdf.body(
    "자산군(주식/채권) 시그널도 개별 자산과 동일한 5단계(±2) 스케일을 사용합니다. "
    "점수 차이에 2.5%p를 곱하여 SAA 대비 비중을 조정합니다. "
    "합이 100%를 초과할 경우 초과분을 큰 쪽에서 차감합니다. 비음수 조건만 유지합니다."
)
pdf.body(
    "예: 주식 OW(+1), 채권 UW(-1) → shift = (+1-(-1))×2.5 = 5%p → 주식 75%, 채권 25%"
)
pdf.ln(1)

pdf.sub_title("Step 2. Signal 변환")
pdf.mono("  Signal_i = View 의견의 수치 변환")
pdf.body("View 5단계 의견을 -2 ~ +2 수치로 매핑합니다.")
pdf.ln(1)

pdf.sub_title("Step 3. Base 계산")
pdf.mono("  Base_i = w * SAA_i + (1 - w) * Peer_i")
pdf.ln(1)
pdf.body("SAA 가중치(w)에 따라 출발점이 결정됩니다:")
pdf.bullet("w = 0.0: Base = Peer (Peer만 반영)")
pdf.bullet("w = 0.5: Base = (SAA + Peer) / 2 (균등 평균)")
pdf.bullet("w = 1.0: Base = SAA (SAA만 반영)")
pdf.ln(1)

pdf.sub_title("Step 4. Tilt 계산 (Base 비례)")
pdf.mono("  Tilt_i = Base_i * TiltRate")
pdf.ln(1)
pdf.body(
    "Base에 비례하여 Tilt가 결정됩니다. "
    "비중이 큰 자산은 조정 여지가 크고, 작은 자산은 조정이 작습니다."
)
pdf.ln(1)

pdf.sub_title("Step 5. Adjustment 계산")
pdf.mono("  Adj_i = a * Signal_i * Tilt_i")
pdf.ln(1)

pdf.sub_title("Step 6. Raw 비중")
pdf.mono("  Raw_i = max( Base_i + Adj_i,  0 )")
pdf.body("Raw 비중이 음수가 되지 않도록 비음수 조건을 적용합니다.")
pdf.ln(1)

pdf.sub_title("Step 7. TAA 정규화")
pdf.mono("  TAA = class_total * (Raw_i / Sum(Raw_within_class))")
pdf.body("자산군 내 Raw 비율에 Step 1에서 결정된 자산군 총비중을 곱합니다.")
pdf.ln(1)

pdf.sub_title("Step 8. Range (범위)")
pdf.mono("  TAA >= 20% -> +/- 7.5%p")
pdf.mono("  TAA >= 10% -> +/- 5%p")
pdf.mono("  TAA <  10% -> +/- 2.5%p")
pdf.body(
    "TAA 값의 크기에 따라 디폴트 상하 범위가 자동 설정됩니다. "
    "Range Confirmation 테이블에서 Low/High를 수기로 조정한 뒤 '범위 확정' 버튼으로 확정합니다."
)

# ── 3. 파라미터 ──
pdf.section_title("3. 파라미터")

pdf.sub_title("View Signal (5단계)")
pdf.table(
    ["View 레벨", "Signal 값", "의미"],
    [
        ["Strong OW", "+2", "강한 비중확대"],
        ["Overweight", "+1", "비중확대"],
        ["Neutral", "0", "중립"],
        ["Underweight", "-1", "비중축소"],
        ["Strong UW", "-2", "강한 비중축소"],
    ],
    [40, 30, 60],
)

pdf.sub_title("α (확신도)")
pdf.bullet("범위: 0.0 ~ 1.0 (슬라이더로 조정)")
pdf.bullet("α = 0: Active bet 없음, TAA = Base 그대로")
pdf.bullet("α = 0.5: 기본값, 적당한 틸트")
pdf.bullet("α = 1.0: 최대 확신, 최대 틸트")
pdf.ln(1)

pdf.sub_title("SAA 가중치 (w)")
pdf.bullet("범위: 0.0 ~ 1.0 (슬라이더로 조정)")
pdf.bullet("기본값: 0.5")
pdf.bullet("Base = w × SAA + (1-w) × Peer")
pdf.bullet("w = 0이면 Peer 100% 반영, w = 1이면 SAA 100% 반영")
pdf.ln(1)

pdf.sub_title("Tilt Rate")
pdf.bullet("범위: 0% ~ 50% (슬라이더로 조정)")
pdf.bullet("기본값: 20%")
pdf.bullet("Tilt = Base × TiltRate")
pdf.bullet("비중이 큰 자산일수록 Tilt가 커져 조정 여지가 확대됨")
pdf.ln(1)

pdf.sub_title("비음수 조건")
pdf.body("모든 비중(Raw, 자산군 총비중)은 비음수 조건만 적용합니다.")

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

pdf.sub_title("예시: α = 0.5, SAA 가중치(w) = 0.5, Tilt Rate = 20%")
pdf.body("주식 미국 OW / 주식 중국 UW / 채권 미국 Strong OW 설정 시:")
pdf.ln(2)

pdf.body("자산군 시그널: 모두 Neutral → shift = 0, 주식 70%, 채권 30% (SAA 그대로)")
pdf.ln(1)

pdf.table(
    ["자산", "지역", "SAA", "Peer", "Base", "View", "Signal", "Tilt", "Adj", "TAA"],
    [
        ["주식", "미국", "49.0", "45.5", "47.25", "OW", "+1", "9.45", "+4.73", "48.88"],
        ["주식", "유럽", "10.5", "12.6", "11.55", "N", "0", "2.31", "0", "10.86"],
        ["주식", "일본", "3.5", "3.5", "3.50", "N", "0", "0.70", "0", "3.29"],
        ["주식", "중국", "2.1", "3.5", "2.80", "UW", "-1", "0.56", "-0.28", "2.37"],
        ["주식", "한국", "3.5", "2.1", "2.80", "N", "0", "0.56", "0", "2.63"],
        ["주식", "기타", "1.4", "2.8", "2.10", "N", "0", "0.42", "0", "1.97"],
        ["채권", "미국", "21.0", "18.0", "19.50", "SOW", "+2", "3.90", "+3.90", "20.71"],
        ["채권", "한국", "9.0", "12.0", "10.50", "N", "0", "2.10", "0", "9.29"],
    ],
    [12, 12, 10, 10, 10, 10, 14, 10, 10, 12],
)

pdf.body(
    "• 주식 합계 = 70.00%, 채권 합계 = 30.00% (자산군별 분리 정규화)\n"
    "• Base = 0.5×SAA + 0.5×Peer → Neutral이어도 Peer가 아닌 SAA-Peer 중간점 출발\n"
    "• Tilt = Base × 20% → 비중이 큰 자산(미국 47.25%)의 Tilt가 자연스럽게 큼\n"
    "• TAA = Raw / Σ(같은자산군 Raw) × 자산군비중"
)

# ── 6. 왜 이 방식이 작동하는가 ──
pdf.section_title("6. 왜 이 방식이 작동하는가")

pdf.body(
    "1. SAA의 장기 전략적 관점을 출발점(Base)에 직접 반영합니다.\n\n"
    "2. w 조절로 SAA와 Peer 사이에서 유연하게 기준점을 설정할 수 있습니다.\n\n"
    "3. Base 비례 Tilt: 비중이 큰 자산은 조정 여지가 크고, "
    "작은 자산은 자연스럽게 조정이 제한됩니다.\n\n"
    "4. 대칭적 구조: 방향에 따른 편향 없이 Signal을 균등하게 적용합니다.\n\n"
    "5. 2단계 배분: 자산군 비중(Step 1)과 자산군 내 배분(Step 2)을 분리하여 "
    "각각의 시그널이 명확하게 반영됩니다.\n\n"
    "6. 단, w가 높으면 Peer와의 괴리가 커질 수 있으므로 "
    "tracking error 관리에 유의가 필요합니다."
)

# ── 7. 대시보드 UI ──
pdf.section_title("7. 대시보드 UI 구성")

pdf.sub_title("Parameters")
pdf.body(
    "• α 슬라이더: 확신도 조절\n"
    "• SAA 가중치(w) 슬라이더: SAA-Peer 블렌드 비율\n"
    "• Tilt Rate 슬라이더: Base 대비 Tilt 비율"
)
pdf.ln(1)

pdf.sub_title("Asset Class Signal")
pdf.body(
    "• 자산군(주식/채권) 전체에 대한 View 시그널\n"
    "• Step 1에서 자산군 총비중 결정에 사용"
)
pdf.ln(1)

pdf.sub_title("Region Inputs")
pdf.body(
    "• 자산(주식/채권), 지역, SAA(%), Peer(%), View를 직접 편집 가능\n"
    "• View 드롭다운: Strong OW / Overweight / Neutral / Underweight / Strong UW\n"
    "• 행 추가/삭제 가능"
)
pdf.ln(1)

pdf.sub_title("Range Confirmation")
pdf.body(
    "• TAA 값의 크기에 따라 디폴트 범위(Low/High)가 자동 생성\n"
    "  - TAA >= 20%: ±7.5%p / TAA >= 10%: ±5%p / TAA < 10%: ±2.5%p\n"
    "• Low/High 셀을 수기로 조정 가능\n"
    "• '범위 확정' 버튼 클릭으로 확정\n"
    "• 입력(SAA/Peer/View/α 등)이 변경되면 자동으로 리셋"
)
pdf.ln(1)

pdf.sub_title("TAA Allocation")
pdf.body(
    "• 각 자산/지역별 TAA 비중 카드 + 범위(Low ~ High) 표시\n"
    "• vs Peer, vs SAA 차이 표시\n"
    "• SAA / Peer / TAA 비교 바 차트 (TAA에 범위 error bar 포함)"
)
pdf.ln(1)

pdf.sub_title("Active Bets")
pdf.body(
    "• vs Peer / vs SAA 기준 Overweight / Underweight 포지션 목록\n"
    "• Total Active Risk (one-way %p)"
)
pdf.ln(1)

pdf.sub_title("Vintage SAA & Other Vintages")
pdf.body(
    "• 다른 TDF 빈티지(2030, 2040, 2060)의 주식/채권 비율 설정\n"
    "• Step 1: 자산군 시그널 shift가 빈티지에도 동일 적용 (빈티지SAA ± shift)\n"
    "• Step 2: 2050 Raw 기준 tilt_ratio를 빈티지 SAA에 비례 전파\n"
    "• 자산군별 per-class 정규화 후 TAA 비중 산출\n"
    "• 빈티지별 SAA, TAA, vs SAA, Low, High 표시"
)
pdf.ln(1)

pdf.sub_title("Detailed Breakdown")
pdf.body(
    "• SAA, Peer, Base, View, Signal, Tilt, Adj, Raw, TAA, Low, High, vs Peer, vs SAA\n"
    "• 모든 계산 단계를 확인할 수 있는 상세 테이블"
)
pdf.ln(1)

pdf.sub_title("Formula Reference")
pdf.body("• 현재 파라미터 값이 반영된 공식이 실시간으로 표시됩니다.")

# ── 8. 실행 ──
pdf.section_title("8. 실행 방법")
pdf.mono("  pip install dash pandas plotly")
pdf.mono("  python taa_portfolio_optimizer.py")
pdf.ln(1)


# ── Save ──
output_path = "/home/byoun/projects/taa-dashboard/taa-dashboard-manual.pdf"
pdf.output(output_path)
print(f"PDF saved: {output_path}")
