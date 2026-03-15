"""
TAA Dashboard
==================================
2단계 배분으로 TAA 비중을 산출:

Step 1: 자산군 시그널 → 주식/채권 총비중 (SAA 기준, 점수차 × 2.5%p)
Step 2: 개별 시그널 → Base 비례 Tilt로 자산군 내 배분
    Base_i = w × SAA_i + (1-w) × Peer_i
    Tilt_i = Base_i × tilt_rate
    TAA_i = normalize( Base_i + α × Signal_i × Tilt_i )

Requirements:
    pip install dash pandas plotly

Run:
    python taa_portfolio_optimizer.py
"""

import dash
from dash import dcc, html, dash_table, Input, Output, State, callback_context
import plotly.graph_objects as go
import pandas as pd


DEFAULT_REGIONS = [
    # 주식 70% — 내부비중(100기준): 미국70 유럽15 일본5 중국3 한국5 기타2
    {"자산": "주식", "지역": "미국","SAA": 49.0, "Peer": 45.5, "View": "Neutral"},
    {"자산": "주식", "지역": "유럽","SAA": 10.5, "Peer": 12.6, "View": "Neutral"},
    {"자산": "주식", "지역": "일본","SAA":  3.5, "Peer":  3.5, "View": "Neutral"},
    {"자산": "주식", "지역": "중국","SAA":  2.1, "Peer":  3.5, "View": "Neutral"},
    {"자산": "주식", "지역": "한국","SAA":  3.5, "Peer":  2.1, "View": "Neutral"},
    {"자산": "주식", "지역": "기타","SAA":  1.4, "Peer":  2.8, "View": "Neutral"},
    # 채권 30% — 내부비중(100기준): 미국70 한국30
    {"자산": "채권", "지역": "미국","SAA": 21.0, "Peer": 18.0, "View": "Neutral"},
    {"자산": "채권", "지역": "한국","SAA":  9.0, "Peer": 12.0, "View": "Neutral"},
]

DEFAULT_CLASS_SIGNALS = [
    {"자산군": "주식", "View": "Neutral"},
    {"자산군": "채권", "View": "Neutral"},
]

# 2050 기준 내부비중 (자산군 내 지역별 비율, 합계=100)
EQUITY_INTERNAL_WEIGHTS = {
    "미국": 70, "유럽": 15, "일본": 5, "중국": 3, "한국": 5, "기타": 2,
}
BOND_INTERNAL_WEIGHTS = {
    "미국": 70, "한국": 30,
}

DEFAULT_VINTAGES = [
    {"Vintage": "2030", "Equity": 40, "Bond": 60},
    {"Vintage": "2040", "Equity": 55, "Bond": 45},
    {"Vintage": "2060", "Equity": 90, "Bond": 10},
]

VIEW_MAP = {"Strong OW": 2, "Overweight": 1, "Neutral": 0, "Underweight": -1, "Strong UW": -2}
REGION_COLORS = ["#6366f1", "#f59e0b", "#ec4899", "#06b6d4", "#10b981", "#f97316", "#8b5cf6", "#14b8a6"]


def compute_taa(df: pd.DataFrame, alpha: float, saa_weight: float = 0.5, tilt_rate: float = 0.20, class_signals: dict = None) -> pd.DataFrame:
    """2단계 배분: 자산군 비중 → 자산군 내 지역 배분

    Step 1: 자산군 시그널로 자산군 간 비중 조정 (SAA 기준, 점수차 × 2.5%p)
    Step 2: 개별 시그널로 Base 비례 Tilt → 자산군 내 지역 배분
    TAA = 자산군 비중 × 자산군 내 비율
    """
    if class_signals is None:
        class_signals = {}

    df = df.copy()
    df["Signal_Asset"] = df["View"].map(VIEW_MAP).fillna(0).astype(float)
    if "자산" in df.columns:
        df["Signal_Class"] = df["자산"].map(class_signals).fillna(0).astype(float)
    else:
        df["Signal_Class"] = 0.0

    # ── Step 1: 자산군 간 비중 결정 (SAA 기준, 점수차 × 2.5%p) ──
    asset_classes = df["자산"].unique().tolist() if "자산" in df.columns else ["전체"]
    class_saa_totals = {}
    for ac in asset_classes:
        mask = df["자산"] == ac if "자산" in df.columns else pd.Series(True, index=df.index)
        class_saa_totals[ac] = df.loc[mask, "SAA"].sum()

    SHIFT_PER_POINT = 2.5
    if len(asset_classes) == 2:
        ac_a, ac_b = asset_classes[0], asset_classes[1]
        score_diff = class_signals.get(ac_a, 0) - class_signals.get(ac_b, 0)
        shift = score_diff * SHIFT_PER_POINT
        class_taa = {
            ac_a: max(class_saa_totals[ac_a] + shift, 0),
            ac_b: max(class_saa_totals[ac_b] - shift, 0),
        }
    else:
        class_taa = {ac: class_saa_totals[ac] for ac in asset_classes}

    # 합계 보정 — 초과분을 큰 쪽에서 차감
    total_cf = sum(class_taa.values())
    if total_cf > 0 and abs(total_cf - 100.0) > 1e-9:
        excess = total_cf - 100.0
        larger_ac = max(class_taa, key=class_taa.get)
        class_taa[larger_ac] -= excess

    # ── Step 2: Base 비례 Tilt → 자산군 내 지역 배분 ──
    results = []
    for ac in asset_classes:
        mask = df["자산"] == ac if "자산" in df.columns else pd.Series(True, index=df.index)
        sub = df.loc[mask].copy()

        sub["Base"] = saa_weight * sub["SAA"] + (1 - saa_weight) * sub["Peer"]
        sub["Tilt"] = sub["Base"] * tilt_rate
        sub["Adj"] = alpha * sub["Signal_Asset"] * sub["Tilt"]
        sub["Raw"] = (sub["Base"] + sub["Adj"]).clip(lower=0)

        # 자산군 내 정규화: Raw → 비율 → 자산군 비중 곱하기
        raw_total = sub["Raw"].sum()
        if class_taa[ac] > 0 and raw_total > 0:
            sub["TAA"] = sub["Raw"] / raw_total * class_taa[ac]
        else:
            sub["TAA"] = 0.0
        results.append(sub)

    result = pd.concat(results, ignore_index=True)

    result["vs_Peer"] = result["TAA"] - result["Peer"]
    result["vs_SAA"] = result["TAA"] - result["SAA"]

    half_w = result["TAA"].apply(lambda v: 7.5 if v >= 20 else 5.0 if v >= 10 else 2.5)
    result["TAA_Low"] = (result["TAA"] - half_w).clip(lower=0.0)
    result["TAA_High"] = result["TAA"] + half_w

    return result


def derive_vintage_saa(equity_pct: float, bond_pct: float) -> list[dict]:
    """빈티지의 주식/채권 총비율에서 지역별 SAA를 산출 (2050 내부비중 기준)"""
    rows = []
    for region, weight in EQUITY_INTERNAL_WEIGHTS.items():
        rows.append({"자산": "주식", "지역": region, "SAA": round(equity_pct * weight / 100, 2)})
    for region, weight in BOND_INTERNAL_WEIGHTS.items():
        rows.append({"자산": "채권", "지역": region, "SAA": round(bond_pct * weight / 100, 2)})
    return rows


def propagate_to_vintage(result_2050: pd.DataFrame, vintage_saa: list[dict],
                         class_signals: dict = None) -> pd.DataFrame:
    """2050 Raw 기준 비례 tilt를 다른 빈티지에 전파 (Step 1 + Step 2)

    Step 1: 자산군 시그널 → 빈티지 주식/채권 총비중 shift
    Step 2: tilt_ratio = (Raw_2050 - SAA_2050) / SAA_2050 → 자산군 내 배분
    TAA = per-class normalize(Vintage_Raw) × class_taa
    """
    if class_signals is None:
        class_signals = {}

    vdf = pd.DataFrame(vintage_saa)

    # ── Step 1: 자산군 시그널 shift (2050과 동일 로직) ──
    asset_classes = vdf["자산"].unique().tolist()
    v_class_saa = {}
    for ac in asset_classes:
        v_class_saa[ac] = vdf.loc[vdf["자산"] == ac, "SAA"].sum()

    SHIFT_PER_POINT = 2.5
    if len(asset_classes) == 2 and class_signals:
        ac_a, ac_b = asset_classes[0], asset_classes[1]
        score_diff = class_signals.get(ac_a, 0) - class_signals.get(ac_b, 0)
        shift = score_diff * SHIFT_PER_POINT
        v_class_taa = {
            ac_a: max(v_class_saa[ac_a] + shift, 0),
            ac_b: max(v_class_saa[ac_b] - shift, 0),
        }
        total_cf = sum(v_class_taa.values())
        if total_cf > 0 and abs(total_cf - 100.0) > 1e-9:
            excess = total_cf - 100.0
            larger_ac = max(v_class_taa, key=v_class_taa.get)
            v_class_taa[larger_ac] -= excess
    else:
        v_class_taa = {ac: v_class_saa[ac] for ac in asset_classes}

    # ── Step 2: 자산군별 비례 tilt + per-class 정규화 ──
    parts = []
    for ac in asset_classes:
        v_sub = vdf.loc[vdf["자산"] == ac].copy()
        r_sub = result_2050.loc[result_2050["자산"] == ac]

        v_raw = []
        for (vi, vrow), (ri, rrow) in zip(v_sub.iterrows(), r_sub.iterrows()):
            saa_i = rrow["SAA"]
            raw_i = rrow["Raw"]
            v_saa_i = vrow["SAA"]
            if saa_i >= 0.5:
                tilt_ratio = (raw_i - saa_i) / saa_i
                v_raw.append(v_saa_i * (1 + tilt_ratio))
            else:
                absolute_tilt = raw_i - saa_i
                v_raw.append(v_saa_i + absolute_tilt)

        v_sub["Raw"] = [max(r, 0) for r in v_raw]
        raw_total = v_sub["Raw"].sum()
        if v_class_taa[ac] > 0 and raw_total > 0:
            v_sub["TAA"] = v_sub["Raw"] / raw_total * v_class_taa[ac]
        else:
            v_sub["TAA"] = 0.0
        parts.append(v_sub)

    vdf = pd.concat(parts, ignore_index=True)

    vdf["vs_SAA"] = vdf["TAA"] - vdf["SAA"]

    half_w = vdf["TAA"].apply(lambda v: 7.5 if v >= 20 else 5.0 if v >= 10 else 2.5)
    vdf["TAA_Low"] = (vdf["TAA"] - half_w).clip(lower=0.0)
    vdf["TAA_High"] = vdf["TAA"] + half_w

    return vdf


app = dash.Dash(
    __name__,
    title="TAA Dashboard (TDF 2050)",
    suppress_callback_exceptions=True,
)
server = app.server

# 드롭다운 & 입력 UX 개선
app.index_string = '''<!DOCTYPE html>
<html>
<head>{%metas%}<title>{%title%}</title>{%favicon%}{%css%}
<style>
/* 드롭다운 스타일 */
.Select-value-label, .Select-placeholder, .Select-input input {
    color: #1e293b !important;
}
.Select-control {
    background-color: #f8fafc !important;
    border: 1px solid #cbd5e1 !important;
    border-radius: 6px !important;
    min-height: 36px !important;
}
.Select-control:hover {
    border-color: #6366f1 !important;
}
.Select-menu-outer {
    background-color: #ffffff !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 6px !important;
    box-shadow: 0 4px 12px rgba(0,0,0,0.1) !important;
    z-index: 100 !important;
}
.Select-option {
    background-color: #ffffff !important;
    color: #1e293b !important;
    padding: 8px 12px !important;
}
.Select-option.is-focused {
    background-color: #eef2ff !important;
    color: #4338ca !important;
}
.Select-option.is-selected {
    background-color: #e0e7ff !important;
    color: #4338ca !important;
    font-weight: 600 !important;
}

/* 숫자 입력 필드 개선 */
.dash-cell input[type="text"],
.dash-cell input[type="number"] {
    background-color: #f8fafc !important;
    color: #1e293b !important;
    border: 1px solid #cbd5e1 !important;
    border-radius: 4px !important;
    padding: 6px 8px !important;
    font-size: 14px !important;
    transition: border-color 0.15s ease !important;
}
.dash-cell input[type="text"]:focus,
.dash-cell input[type="number"]:focus {
    border-color: #6366f1 !important;
    outline: none !important;
    box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.2) !important;
}



/* 편집 가능 셀 힌트 */
.dash-cell.cell--editable {
    cursor: pointer;
}
.dash-cell.cell--editable:hover {
    background-color: #f1f5f9 !important;
}

/* 삭제 버튼 스타일 */
.dash-cell.dash-delete-cell {
    color: #94a3b8 !important;
}
.dash-cell.dash-delete-cell:hover {
    color: #ef4444 !important;
}

/* 슬라이더 개선 */
.rc-slider-track { background-color: #6366f1 !important; }
.rc-slider-handle {
    border-color: #6366f1 !important;
    background-color: #ffffff !important;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1) !important;
}
.rc-slider-handle:hover,
.rc-slider-handle:active {
    border-color: #4f46e5 !important;
    box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.2) !important;
}
.rc-slider-rail { background-color: #e2e8f0 !important; }
</style>
</head>
<body>{%app_entry%}<footer>{%config%}{%scripts%}{%renderer%}</footer>
</body>
</html>'''

# ── 스타일 상수 (Light Theme) ──
LIGHT_BG  = "#f1f5f9"
CARD_BG   = "#ffffff"
CARD_BD   = "#e2e8f0"
TEXT_MAIN  = "#1e293b"
TEXT_DIM   = "#64748b"
ACCENT     = "#6366f1"
GREEN      = "#059669"
RED        = "#dc2626"

card_style = {
    "backgroundColor": CARD_BG,
    "border": f"1px solid {CARD_BD}",
    "borderRadius": "12px",
    "padding": "24px",
    "marginBottom": "20px",
    "boxShadow": "0 1px 3px rgba(0,0,0,0.06)",
}
label_style = {
    "fontSize": "13px",
    "color": ACCENT,
    "fontWeight": "600",
    "textTransform": "uppercase",
    "letterSpacing": "1.5px",
    "fontFamily": "monospace",
    "marginBottom": "14px",
}


app.layout = html.Div(
    style={"backgroundColor": LIGHT_BG, "minHeight": "100vh", "padding": "30px 20px", "fontFamily": "Inter, sans-serif", "color": TEXT_MAIN},
    children=[
        html.Div(
            style={"maxWidth": "1080px", "margin": "0 auto"},
            children=[
                # ── Header ──
                html.Div([
                    html.H1(
                        "TAA Dashboard (TDF 2050)",
                        style={"fontSize": "28px", "fontWeight": "700", "margin": "0", "letterSpacing": "-0.5px"},
                    ),
                ], style={"marginBottom": "28px"}),

                # ── Parameters ──
                html.Div(style=card_style, children=[
                    html.Div("Parameters", style=label_style),
                    html.Div(style={"display": "grid", "gridTemplateColumns": "1fr 1fr 1fr", "gap": "24px", "alignItems": "start"}, children=[
                        # Alpha slider
                        html.Div([
                            html.Div(style={"display": "flex", "justifyContent": "space-between", "marginBottom": "4px"}, children=[
                                html.Span("α (확신도)", style={"fontSize": "15px", "color": "#475569"}),
                                html.Span(id="alpha-display", style={"fontSize": "18px", "fontWeight": "600", "fontFamily": "monospace", "color": ACCENT}),
                            ]),
                            dcc.Slider(
                                id="alpha-slider", min=0, max=1, step=0.05, value=0.5,
                                marks={0: {"label": "0.0", "style": {"color": TEXT_DIM, "fontSize": "12px"}},
                                       0.5: {"label": "0.5", "style": {"color": TEXT_DIM, "fontSize": "12px"}},
                                       1: {"label": "1.0", "style": {"color": TEXT_DIM, "fontSize": "12px"}}},
                                tooltip={"placement": "bottom", "always_visible": False},
                            ),
                            html.Div(style={"display": "flex", "justifyContent": "space-between", "fontSize": "12px", "color": "#94a3b8"}, children=[
                                html.Span("보수적"), html.Span("적극적"),
                            ]),
                        ]),
                        # SAA 가중치 (w)
                        html.Div([
                            html.Div(style={"display": "flex", "justifyContent": "space-between", "marginBottom": "4px"}, children=[
                                html.Span("SAA 가중치 (w)", style={"fontSize": "15px", "color": "#475569"}),
                                html.Span(id="w-display", style={"fontSize": "18px", "fontWeight": "600", "fontFamily": "monospace", "color": ACCENT}),
                            ]),
                            dcc.Slider(
                                id="w-slider", min=0, max=1, step=0.05, value=0.5,
                                marks={0: {"label": "0.0", "style": {"color": TEXT_DIM, "fontSize": "12px"}},
                                       0.5: {"label": "0.5", "style": {"color": TEXT_DIM, "fontSize": "12px"}},
                                       1: {"label": "1.0", "style": {"color": TEXT_DIM, "fontSize": "12px"}}},
                                tooltip={"placement": "bottom", "always_visible": False},
                            ),
                            html.Div(style={"display": "flex", "justifyContent": "space-between", "fontSize": "12px", "color": "#94a3b8"}, children=[
                                html.Span("Peer 중심"), html.Span("SAA 중심"),
                            ]),
                        ]),
                        # Tilt Rate
                        html.Div([
                            html.Div(style={"display": "flex", "justifyContent": "space-between", "marginBottom": "4px"}, children=[
                                html.Span("Tilt Rate", style={"fontSize": "15px", "color": "#475569"}),
                                html.Span(id="tiltrate-display", style={"fontSize": "18px", "fontWeight": "600", "fontFamily": "monospace", "color": ACCENT}),
                            ]),
                            dcc.Slider(
                                id="tiltrate-slider", min=0, max=0.5, step=0.05, value=0.20,
                                marks={0: {"label": "0%", "style": {"color": TEXT_DIM, "fontSize": "12px"}},
                                       0.2: {"label": "20%", "style": {"color": TEXT_DIM, "fontSize": "12px"}},
                                       0.5: {"label": "50%", "style": {"color": TEXT_DIM, "fontSize": "12px"}}},
                                tooltip={"placement": "bottom", "always_visible": False},
                            ),
                            html.Div(style={"display": "flex", "justifyContent": "space-between", "fontSize": "12px", "color": "#94a3b8"}, children=[
                                html.Span("조정 없음"), html.Span("Base의 50%"),
                            ]),
                        ]),
                    ]),
                ]),

                # ── Asset Class Signal ──
                html.Div(style=card_style, children=[
                    html.Div("Asset Class Signal", style=label_style),
                    html.Div(
                        "자산군(주식/채권) 전체에 대한 View 시그널입니다. 주식/채권 총비중을 결정합니다.",
                        style={"fontSize": "14px", "color": TEXT_DIM, "marginBottom": "12px"},
                    ),
                    dash_table.DataTable(
                        id="class-signal-table",
                        columns=[
                            {"name": "자산군", "id": "자산군", "editable": False},
                            {"name": "View", "id": "View", "presentation": "dropdown", "editable": True},
                        ],
                        data=DEFAULT_CLASS_SIGNALS,
                        dropdown={
                            "View": {
                                "options": [{"label": t, "value": t} for t in ["Strong OW", "Overweight", "Neutral", "Underweight", "Strong UW"]],
                            }
                        },
                        editable=True,
                        row_deletable=False,
                        style_table={"overflowX": "auto", "maxWidth": "400px"},
                        style_header={
                            "backgroundColor": "#f8fafc",
                            "color": "#475569",
                            "fontWeight": "600",
                            "fontSize": "13px",
                            "fontFamily": "monospace",
                            "border": "none",
                            "borderBottom": f"1px solid {CARD_BD}",
                        },
                        style_cell={
                            "backgroundColor": CARD_BG,
                            "color": TEXT_MAIN,
                            "border": "none",
                            "borderBottom": f"1px solid {CARD_BD}",
                            "fontSize": "14px",
                            "fontFamily": "Inter, sans-serif",
                            "padding": "10px 12px",
                            "textAlign": "center",
                        },
                        style_cell_conditional=[
                            {"if": {"column_id": "자산군"}, "textAlign": "left", "fontWeight": "600", "color": ACCENT},
                        ],
                        style_data_conditional=[
                            {"if": {"filter_query": '{View} = "Strong OW"', "column_id": "View"},
                             "color": "#059669", "fontWeight": "700"},
                            {"if": {"filter_query": '{View} = "Overweight"', "column_id": "View"},
                             "color": "#059669", "fontWeight": "600"},
                            {"if": {"filter_query": '{View} = "Neutral"', "column_id": "View"},
                             "color": TEXT_MAIN},
                            {"if": {"filter_query": '{View} = "Underweight"', "column_id": "View"},
                             "color": "#dc2626", "fontWeight": "600"},
                            {"if": {"filter_query": '{View} = "Strong UW"', "column_id": "View"},
                             "color": "#dc2626", "fontWeight": "700"},
                        ],
                    ),
                ]),

                # ── Region Input Table ──
                html.Div(style=card_style, children=[
                    html.Div("Region Inputs", style=label_style),
                    html.Div(
                        "SAA, Peer, View 시그널을 직접 수정할 수 있습니다. 행 추가/삭제도 가능합니다.",
                        style={"fontSize": "14px", "color": TEXT_DIM, "marginBottom": "12px"},
                    ),
                    dash_table.DataTable(
                        id="region-table",
                        columns=[
                            {"name": "자산", "id": "자산", "editable": True},
                            {"name": "지역", "id": "지역", "editable": True},
                            {"name": "SAA (%)", "id": "SAA", "type": "numeric", "editable": True},
                            {"name": "Peer (%)", "id": "Peer", "type": "numeric", "editable": True},
                            {"name": "View", "id": "View", "presentation": "dropdown", "editable": True},
                        ],
                        data=DEFAULT_REGIONS,
                        dropdown={
                            "View": {
                                "options": [{"label": t, "value": t} for t in ["Strong OW", "Overweight", "Neutral", "Underweight", "Strong UW"]],
                            }
                        },
                        editable=True,
                        row_deletable=True,
                        style_table={"overflowX": "auto"},
                        style_header={
                            "backgroundColor": "#f8fafc",
                            "color": "#475569",
                            "fontWeight": "600",
                            "fontSize": "13px",
                            "fontFamily": "monospace",
                            "border": "none",
                            "borderBottom": f"1px solid {CARD_BD}",
                        },
                        style_cell={
                            "backgroundColor": CARD_BG,
                            "color": TEXT_MAIN,
                            "border": "none",
                            "borderBottom": f"1px solid {CARD_BD}",
                            "fontSize": "14px",
                            "fontFamily": "Inter, sans-serif",
                            "padding": "10px 12px",
                            "textAlign": "center",
                        },
                        style_cell_conditional=[
                            {"if": {"column_id": "자산"}, "textAlign": "left", "fontWeight": "600", "color": ACCENT},
                            {"if": {"column_id": "지역"}, "textAlign": "left", "fontWeight": "600"},
                        ],
                        style_data_conditional=[
                            {"if": {"filter_query": '{View} = "Strong OW"', "column_id": "View"},
                             "color": "#059669", "fontWeight": "700"},
                            {"if": {"filter_query": '{View} = "Overweight"', "column_id": "View"},
                             "color": "#059669", "fontWeight": "600"},
                            {"if": {"filter_query": '{View} = "Neutral"', "column_id": "View"},
                             "color": TEXT_MAIN},
                            {"if": {"filter_query": '{View} = "Underweight"', "column_id": "View"},
                             "color": "#dc2626", "fontWeight": "600"},
                            {"if": {"filter_query": '{View} = "Strong UW"', "column_id": "View"},
                             "color": "#dc2626", "fontWeight": "700"},
                        ],
                    ),
                    html.Br(),
                    html.Button(
                        "+ 지역 추가",
                        id="add-row-btn",
                        n_clicks=0,
                        style={
                            "backgroundColor": "#eef2ff", "color": ACCENT, "border": f"1px dashed {ACCENT}80",
                            "borderRadius": "6px", "padding": "8px 16px", "fontSize": "14px",
                            "cursor": "pointer", "fontWeight": "600",
                        },
                    ),
                ]),

                # ── Range Confirmation ──
                html.Div(style=card_style, children=[
                    html.Div("Range Confirmation", style=label_style),
                    html.Div(
                        "디폴트 범위는 TAA ≥ 20%이면 ±7.5%p, ≥ 10%이면 ±5%p, < 10%이면 ±2.5%p로 자동 설정됩니다. Low/High를 수기로 조정하여 확정하세요.",
                        style={"fontSize": "14px", "color": TEXT_DIM, "marginBottom": "12px"},
                    ),
                    html.Div(id="range-table-container"),
                    html.Br(),
                    html.Button(
                        "범위 확정",
                        id="confirm-range-btn",
                        n_clicks=0,
                        style={
                            "backgroundColor": ACCENT, "color": "white", "border": "none",
                            "borderRadius": "6px", "padding": "10px 24px", "fontSize": "14px",
                            "cursor": "pointer", "fontWeight": "700",
                        },
                    ),
                    html.Div(id="range-status", style={"display": "inline-block", "marginLeft": "12px", "fontSize": "14px", "color": GREEN}),
                    dcc.Store(id="confirmed-range-store", data=None),
                ]),

                # ── Results ──
                html.Div(style=card_style, children=[
                    html.Div("TAA Allocation", style=label_style),
                    html.Div(id="result-cards"),
                    html.Br(),
                    dcc.Graph(id="comparison-chart", config={"displayModeBar": False}),
                ]),

                # ── Active Bets ──
                html.Div(style=card_style, children=[
                    html.Div("Active Bets", style=label_style),
                    html.Div(id="active-bets"),
                ]),

                # ── Detailed Result Table ──
                html.Div(style=card_style, children=[
                    html.Div("Detailed Breakdown", style=label_style),
                    html.Div(id="result-table"),
                ]),

                # ── Vintage SAA Input ──
                html.Div(style=card_style, children=[
                    html.Div("Vintage SAA", style=label_style),
                    html.Div(
                        "다른 TDF 빈티지의 주식/채권 비율을 설정합니다. 2050의 TAA 틸트가 비례 전파됩니다.",
                        style={"fontSize": "14px", "color": TEXT_DIM, "marginBottom": "12px"},
                    ),
                    dash_table.DataTable(
                        id="vintage-table",
                        columns=[
                            {"name": "Vintage", "id": "Vintage", "editable": True},
                            {"name": "Equity (%)", "id": "Equity", "type": "numeric", "editable": True},
                            {"name": "Bond (%)", "id": "Bond", "type": "numeric", "editable": True},
                        ],
                        data=DEFAULT_VINTAGES,
                        editable=True,
                        row_deletable=True,
                        style_table={"overflowX": "auto", "maxWidth": "500px"},
                        style_header={
                            "backgroundColor": "#f8fafc", "color": "#475569", "fontWeight": "600",
                            "fontSize": "13px", "fontFamily": "monospace", "border": "none",
                            "borderBottom": f"1px solid {CARD_BD}",
                        },
                        style_cell={
                            "backgroundColor": CARD_BG, "color": TEXT_MAIN, "border": "none",
                            "borderBottom": f"1px solid {CARD_BD}", "fontSize": "14px",
                            "fontFamily": "monospace", "padding": "10px 12px", "textAlign": "center",
                        },
                        style_cell_conditional=[
                            {"if": {"column_id": "Vintage"}, "textAlign": "left", "fontWeight": "600", "color": ACCENT, "fontFamily": "Inter, sans-serif"},
                        ],
                    ),
                    html.Br(),
                    html.Button(
                        "+ 빈티지 추가", id="add-vintage-btn", n_clicks=0,
                        style={
                            "backgroundColor": "#eef2ff", "color": ACCENT, "border": f"1px dashed {ACCENT}80",
                            "borderRadius": "6px", "padding": "8px 16px", "fontSize": "14px",
                            "cursor": "pointer", "fontWeight": "600",
                        },
                    ),
                    html.Div(id="vintage-warning", style={"marginTop": "8px", "fontSize": "13px", "color": RED}),
                ]),

                # ── Vintage Results ──
                html.Div(style=card_style, children=[
                    html.Div("Other Vintages", style=label_style),
                    html.Div(id="vintage-results"),
                ]),

                # ── Formula ──
                html.Div(style=card_style, children=[
                    html.Div("Formula Reference", style=label_style),
                    html.Div(id="formula-text", style={"fontFamily": "monospace", "fontSize": "15px", "lineHeight": "2.0", "color": "#475569"}),
                ]),
            ],
        ),
    ],
)



# 행 추가
@app.callback(
    Output("region-table", "data"),
    Input("add-row-btn", "n_clicks"),
    State("region-table", "data"),
    prevent_initial_call=True,
)
def add_row(n_clicks, rows):
    rows.append({"자산": "주식", "지역": "신규", "SAA": 0, "Peer": 0, "View": "Neutral"})
    return rows


@app.callback(
    Output("vintage-table", "data"),
    Input("add-vintage-btn", "n_clicks"),
    State("vintage-table", "data"),
    prevent_initial_call=True,
)
def add_vintage_row(n_clicks, rows):
    rows.append({"Vintage": "20XX", "Equity": 50, "Bond": 50})
    return rows


@app.callback(
    [Output("vintage-results", "children"),
     Output("vintage-warning", "children")],
    [Input("region-table", "data"),
     Input("alpha-slider", "value"),
     Input("w-slider", "value"),
     Input("tiltrate-slider", "value"),
     Input("class-signal-table", "data"),
     Input("vintage-table", "data")],
)
def update_vintage_results(rows, alpha, saa_weight, tilt_rate, class_rows, vintage_rows):
    if not rows or not vintage_rows:
        return html.Div("데이터를 입력하세요.", style={"color": TEXT_DIM}), ""

    # Compute 2050 result
    df = pd.DataFrame(rows)
    for col in ["SAA", "Peer"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    df["View"] = df["View"].fillna("Neutral")

    class_signals = {}
    if class_rows:
        for r in class_rows:
            class_signals[r["자산군"]] = VIEW_MAP.get(r.get("View", "Neutral"), 0)

    result_2050 = compute_taa(df, alpha, saa_weight, tilt_rate, class_signals)

    # Process each vintage
    vintage_sections = []
    warnings = []
    seen_names = set()
    for vrow in vintage_rows:
        name = vrow.get("Vintage", "?")
        eq = pd.to_numeric(vrow.get("Equity", 0), errors="coerce") or 0
        bd = pd.to_numeric(vrow.get("Bond", 0), errors="coerce") or 0
        if name in seen_names:
            warnings.append(f"{name}: 중복 빈티지")
            continue
        seen_names.add(name)
        if abs(eq + bd - 100) > 0.1:
            warnings.append(f"{name}: Equity({eq}%) + Bond({bd}%) = {eq+bd}% (100%가 아님)")
            continue

        vintage_saa = derive_vintage_saa(eq, bd)
        vr = propagate_to_vintage(result_2050, vintage_saa, class_signals)
        vr["Label"] = vr["자산"] + " " + vr["지역"]

        # Build compact table
        display_df = vr[["Label", "SAA", "TAA", "vs_SAA", "TAA_Low", "TAA_High"]].copy()
        display_df = display_df.rename(columns={
            "Label": "자산/지역", "SAA": "SAA(%)", "TAA": "TAA(%)",
            "vs_SAA": "vs SAA(%p)", "TAA_Low": "Low(%)", "TAA_High": "High(%)",
        })
        for c in ["SAA(%)", "TAA(%)", "Low(%)", "High(%)"]:
            display_df[c] = display_df[c].apply(lambda v: f"{v:.2f}")
        display_df["vs SAA(%p)"] = display_df["vs SAA(%p)"].apply(lambda v: f"{v:+.2f}")

        vintage_sections.append(
            html.Div(style={"marginBottom": "24px"}, children=[
                html.Div(f"TDF {name}  (주식 {eq:.0f}% / 채권 {bd:.0f}%)",
                         style={"fontSize": "15px", "fontWeight": "700", "marginBottom": "8px", "color": TEXT_MAIN}),
                dash_table.DataTable(
                    data=display_df.to_dict("records"),
                    columns=[{"name": c, "id": c} for c in display_df.columns],
                    style_header={
                        "backgroundColor": "#f8fafc", "color": "#475569", "fontWeight": "600",
                        "fontSize": "12px", "fontFamily": "monospace", "border": "none",
                        "borderBottom": f"1px solid {CARD_BD}",
                    },
                    style_cell={
                        "backgroundColor": CARD_BG, "color": TEXT_MAIN, "border": "none",
                        "borderBottom": "1px solid #e2e8f0", "fontSize": "13px", "fontFamily": "monospace",
                        "padding": "6px 8px", "textAlign": "center",
                    },
                    style_cell_conditional=[
                        {"if": {"column_id": "자산/지역"}, "textAlign": "left", "fontWeight": "600", "fontFamily": "Inter, sans-serif"},
                    ],
                ),
            ])
        )

    warning_text = " | ".join(warnings) if warnings else ""
    if not vintage_sections:
        vintage_sections = [html.Div("유효한 빈티지 데이터가 없습니다.", style={"color": TEXT_DIM})]

    return html.Div(vintage_sections), warning_text


# 파라미터 표시
@app.callback(Output("alpha-display", "children"), Input("alpha-slider", "value"))
def update_alpha_display(val):
    return f"{val:.2f}"

@app.callback(Output("w-display", "children"), Input("w-slider", "value"))
def update_w_display(val):
    return f"{val:.2f}"

@app.callback(Output("tiltrate-display", "children"), Input("tiltrate-slider", "value"))
def update_tiltrate_display(val):
    return f"{val:.0%}"


# ── Range Table 렌더링 (입력 변경 시 디폴트 범위 재생성) ──
@app.callback(
    [
        Output("range-table-container", "children"),
        Output("confirmed-range-store", "data"),
        Output("range-status", "children"),
    ],
    [
        Input("region-table", "data"),
        Input("alpha-slider", "value"),
        Input("w-slider", "value"),
        Input("tiltrate-slider", "value"),
        Input("class-signal-table", "data"),
    ],
)
def update_range_table(rows, alpha, saa_weight, tilt_rate, class_rows):
    if not rows:
        return html.Div("데이터를 입력하세요.", style={"color": TEXT_DIM}), None, ""

    df = pd.DataFrame(rows)
    for col in ["SAA", "Peer"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    df["View"] = df["View"].fillna("Neutral")

    class_signals = {}
    if class_rows:
        for r in class_rows:
            class_signals[r["자산군"]] = VIEW_MAP.get(r.get("View", "Neutral"), 0)

    result = compute_taa(df, alpha, saa_weight, tilt_rate, class_signals)
    if "자산" in result.columns:
        result["Label"] = result["자산"] + " " + result["지역"]
    else:
        result["Label"] = result["지역"]

    range_display = result[["Label", "TAA", "TAA_Low", "TAA_High"]].copy()
    range_display["AP_Active"] = result["SAA"].values.round(2)
    range_display["AP_EMP"] = result["SAA"].values.round(2)
    for col in ["TAA", "TAA_Low", "TAA_High"]:
        range_display[col] = range_display[col].round(2)
    range_data = range_display.to_dict("records")

    range_table = dash_table.DataTable(
        id="range-table",
        columns=[
            {"name": "자산/지역", "id": "Label", "editable": False},
            {"name": "액티브 (%)", "id": "AP_Active", "type": "numeric", "editable": True},
            {"name": "EMP (%)", "id": "AP_EMP", "type": "numeric", "editable": True},
            {"name": "TAA (%)", "id": "TAA", "type": "numeric", "editable": False},
            {"name": "Low (%)", "id": "TAA_Low", "type": "numeric", "editable": True},
            {"name": "High (%)", "id": "TAA_High", "type": "numeric", "editable": True},
        ],
        data=range_data,
        style_header={
            "backgroundColor": "#f8fafc", "color": "#475569", "fontWeight": "600",
            "fontSize": "13px", "fontFamily": "monospace", "border": "none",
            "borderBottom": f"1px solid {CARD_BD}",
        },
        style_cell={
            "backgroundColor": CARD_BG, "color": TEXT_MAIN, "border": "none",
            "borderBottom": "1px solid #e2e8f0", "fontSize": "14px", "fontFamily": "monospace",
            "padding": "10px 12px", "textAlign": "center",
        },
        style_cell_conditional=[
            {"if": {"column_id": "Label"}, "textAlign": "left", "fontWeight": "600", "fontFamily": "Inter, sans-serif"},
            {"if": {"column_id": "AP_Active"}, "backgroundColor": "#f0fdf4", "color": "#166534", "fontWeight": "600"},
            {"if": {"column_id": "AP_EMP"}, "backgroundColor": "#f0fdf4", "color": "#166534", "fontWeight": "600"},
        ],
        style_data_conditional=[
            {"if": {"column_id": "TAA_Low"}, "backgroundColor": "#fef3c7", "color": "#92400e", "fontWeight": "600"},
            {"if": {"column_id": "TAA_High"}, "backgroundColor": "#fef3c7", "color": "#92400e", "fontWeight": "600"},
        ],
    )
    # 입력 변경 시 확정 상태 리셋
    return range_table, None, ""


# ── 범위 확정 버튼 ──
@app.callback(
    [
        Output("confirmed-range-store", "data", allow_duplicate=True),
        Output("range-status", "children", allow_duplicate=True),
    ],
    Input("confirm-range-btn", "n_clicks"),
    State("range-table", "data"),
    prevent_initial_call=True,
)
def confirm_range(n_clicks, range_data):
    if not range_data:
        return None, ""
    return range_data, "✓ 범위가 확정되었습니다"


# ── 메인 계산 & 렌더링 ──
@app.callback(
    [
        Output("result-cards", "children"),
        Output("comparison-chart", "figure"),
        Output("active-bets", "children"),
        Output("result-table", "children"),
        Output("formula-text", "children"),
    ],
    [
        Input("region-table", "data"),
        Input("alpha-slider", "value"),
        Input("confirmed-range-store", "data"),
        Input("w-slider", "value"),
        Input("tiltrate-slider", "value"),
        Input("class-signal-table", "data"),
    ],
)
def update_results(rows, alpha, confirmed_range, saa_weight, tilt_rate, class_rows):
    if not rows:
        empty = html.Div("데이터를 입력하세요.", style={"color": TEXT_DIM})
        return empty, go.Figure(), empty, empty, ""

    df = pd.DataFrame(rows)
    for col in ["SAA", "Peer"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    df["View"] = df["View"].fillna("Neutral")

    class_signals = {}
    if class_rows:
        for r in class_rows:
            class_signals[r["자산군"]] = VIEW_MAP.get(r.get("View", "Neutral"), 0)

    result = compute_taa(df, alpha, saa_weight, tilt_rate, class_signals)
    # 자산+지역 라벨 (차트/카드 표시용)
    if "자산" in result.columns:
        result["Label"] = result["자산"] + " " + result["지역"]
    else:
        result["Label"] = result["지역"]

    # 확정된 범위 반영 (있으면 수기값 사용, 없으면 디폴트)
    if confirmed_range:
        cr = {r["Label"]: r for r in confirmed_range}
        for i, row in result.iterrows():
            lbl = row["Label"]
            if lbl in cr:
                result.at[i, "TAA_Low"] = float(cr[lbl].get("TAA_Low", row["TAA_Low"]))
                result.at[i, "TAA_High"] = float(cr[lbl].get("TAA_High", row["TAA_High"]))

    n = len(result)
    colors = REGION_COLORS[:n]

    # ── 1) Result Cards (범위 포함) ──
    cards = []
    for i, row in result.iterrows():
        diff = row["vs_Peer"]
        diff_color = GREEN if diff > 0.05 else RED if diff < -0.05 else TEXT_DIM
        cards.append(
            html.Div(
                style={
                    "backgroundColor": "#f8fafc",
                    "borderRadius": "10px",
                    "padding": "16px 12px",
                    "textAlign": "center",
                    "borderTop": f"3px solid {colors[i]}",
                    "border": f"1px solid {CARD_BD}",
                    "borderTopWidth": "3px",
                    "borderTopColor": colors[i],
                },
                children=[
                    html.Div(row["Label"], style={"fontSize": "14px", "color": TEXT_DIM, "marginBottom": "4px"}),
                    html.Div([
                        html.Span(f"{row['TAA']:.1f}", style={"fontSize": "32px", "fontWeight": "700", "fontFamily": "monospace"}),
                        html.Span("%", style={"fontSize": "16px", "color": TEXT_DIM}),
                    ]),
                    html.Div(
                        f"({row['TAA_Low']:.1f} – {row['TAA_High']:.1f}%)",
                        style={"fontSize": "13px", "fontFamily": "monospace", "color": "#b45309", "marginTop": "2px"},
                    ),
                    html.Div(
                        f"vs Peer {'+' if diff > 0 else ''}{diff:.1f}%p",
                        style={"fontSize": "14px", "fontFamily": "monospace", "fontWeight": "600", "color": diff_color, "marginTop": "4px"},
                    ),
                    html.Div(
                        f"vs SAA {'+' if row['vs_SAA'] > 0 else ''}{row['vs_SAA']:.1f}%p",
                        style={
                            "fontSize": "13px", "fontFamily": "monospace", "fontWeight": "600",
                            "color": GREEN if row["vs_SAA"] > 0.05 else RED if row["vs_SAA"] < -0.05 else TEXT_DIM,
                            "marginTop": "2px",
                        },
                    ),
                ],
            )
        )
    result_cards = html.Div(style={"display": "grid", "gridTemplateColumns": f"repeat({n}, 1fr)", "gap": "12px"}, children=cards)

    # ── 2) Comparison Chart ──
    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="SAA",
        x=result["Label"],
        y=result["SAA"],
        marker_color="#94a3b8",
        text=result["SAA"].apply(lambda v: f"{v:.1f}%"),
        textposition="inside",
        textfont=dict(size=12, family="monospace", color="#1e293b"),
    ))
    fig.add_trace(go.Bar(
        name="Peer",
        x=result["Label"],
        y=result["Peer"],
        marker_color="#cbd5e1",
        text=result["Peer"].apply(lambda v: f"{v:.1f}%"),
        textposition="inside",
        textfont=dict(size=12, family="monospace", color="#1e293b"),
    ))
    fig.add_trace(go.Bar(
        name="TAA",
        x=result["Label"],
        y=result["TAA"],
        marker_color=ACCENT,
        text=result["TAA"].apply(lambda v: f"{v:.1f}%"),
        textposition="inside",
        textfont=dict(size=12, family="monospace", color="white"),
        error_y=dict(
            type="data",
            symmetric=False,
            array=(result["TAA_High"] - result["TAA"]).tolist(),
            arrayminus=(result["TAA"] - result["TAA_Low"]).tolist(),
            color="#d97706",
            thickness=2,
            width=4,
        ),
    ))
    fig.update_layout(
        barmode="group",
        plot_bgcolor=CARD_BG,
        paper_bgcolor=CARD_BG,
        font=dict(color=TEXT_MAIN, family="Inter, sans-serif"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=12)),
        margin=dict(l=40, r=20, t=30, b=40),
        height=300,
        yaxis=dict(gridcolor="#e2e8f0", title=None, ticksuffix="%"),
        xaxis=dict(title=None),
    )

    # ── 3) Active Bets ──
    ow = result[result["vs_Peer"] > 0.05]
    uw = result[result["vs_Peer"] < -0.05]
    total_active = result["vs_Peer"].abs().sum() / 2

    def _bet_items(subset, col, color):
        return [
            html.Div(
                style={"display": "flex", "justifyContent": "space-between", "padding": "4px 0", "fontSize": "15px"},
                children=[
                    html.Span(row["Label"]),
                    html.Span(
                        f"{'+' if row[col] > 0 else ''}{row[col]:.1f}%p",
                        style={"fontFamily": "monospace", "color": color, "fontWeight": "600"},
                    ),
                ],
            )
            for _, row in subset.iterrows()
        ] or [html.Div("없음", style={"fontSize": "14px", "color": "#94a3b8"})]

    ow_saa = result[result["vs_SAA"] > 0.05]
    uw_saa = result[result["vs_SAA"] < -0.05]

    active_bets = html.Div([
        html.Div("vs Peer", style={"fontSize": "13px", "color": ACCENT, "fontWeight": "600", "marginBottom": "8px", "fontFamily": "monospace"}),
        html.Div(style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "20px"}, children=[
            html.Div([
                html.Div("▲ Overweight", style={"fontSize": "14px", "color": GREEN, "fontWeight": "600", "marginBottom": "8px"}),
                *_bet_items(ow, "vs_Peer", GREEN),
            ]),
            html.Div([
                html.Div("▼ Underweight", style={"fontSize": "14px", "color": RED, "fontWeight": "600", "marginBottom": "8px"}),
                *_bet_items(uw, "vs_Peer", RED),
            ]),
        ]),
        html.Div(
            f"Total Active Risk (vs Peer): ±{total_active:.1f}%p",
            style={"marginTop": "8px", "padding": "8px 12px", "backgroundColor": LIGHT_BG,
                    "borderRadius": "6px", "fontSize": "14px", "color": TEXT_DIM, "fontFamily": "monospace"},
        ),
        html.Hr(style={"border": "none", "borderTop": f"1px solid {CARD_BD}", "margin": "16px 0"}),
        html.Div("vs SAA", style={"fontSize": "13px", "color": ACCENT, "fontWeight": "600", "marginBottom": "8px", "fontFamily": "monospace"}),
        html.Div(style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "20px"}, children=[
            html.Div([
                html.Div("▲ Overweight", style={"fontSize": "14px", "color": GREEN, "fontWeight": "600", "marginBottom": "8px"}),
                *_bet_items(ow_saa, "vs_SAA", GREEN),
            ]),
            html.Div([
                html.Div("▼ Underweight", style={"fontSize": "14px", "color": RED, "fontWeight": "600", "marginBottom": "8px"}),
                *_bet_items(uw_saa, "vs_SAA", RED),
            ]),
        ]),
        html.Div(
            f"Total Active Risk (vs SAA): ±{result['vs_SAA'].abs().sum() / 2:.1f}%p",
            style={"marginTop": "8px", "padding": "8px 12px", "backgroundColor": LIGHT_BG,
                    "borderRadius": "6px", "fontSize": "14px", "color": TEXT_DIM, "fontFamily": "monospace"},
        ),
    ])

    # ── 4) Detail Table ──
    has_asset = "자산" in result.columns
    base_cols = ["자산", "지역"] if has_asset else ["지역"]
    num_cols = ["SAA", "Peer"]
    if "Base" in result.columns:
        num_cols.append("Base")
    signal_cols = ["View", "Signal_Class", "Signal_Asset"]
    rest_cols = ["Tilt", "Adj", "Raw", "TAA", "vs_Peer", "vs_SAA"]
    detail_cols = base_cols + num_cols + signal_cols + rest_cols
    detail_cols = [c for c in detail_cols if c in result.columns]
    detail_df = result[detail_cols].copy()
    rename = {"SAA": "SAA(%)", "Peer": "Peer(%)", "Base": "Base(%)", "Signal_Class": "Class Sig", "Signal_Asset": "Asset Sig", "Signal": "Signal", "Tilt": "Tilt(%p)", "Adj": "Adj(%p)", "Raw": "Raw(%)", "TAA": "TAA(%)", "vs_Peer": "vs Peer(%p)", "vs_SAA": "vs SAA(%p)"}
    detail_df = detail_df.rename(columns=rename)

    fmt_cols = [c for c in ["Class Sig", "Asset Sig", "Base(%)", "Tilt(%p)", "Adj(%p)", "Raw(%)", "TAA(%)", "vs Peer(%p)", "vs SAA(%p)"] if c in detail_df.columns]
    for c in fmt_cols:
        use_sign = "vs" in c or "Adj" in c
        detail_df[c] = detail_df[c].apply(lambda v, s=use_sign: f"{v:+.2f}" if s else f"{v:.2f}")

    detail_table = dash_table.DataTable(
        data=detail_df.to_dict("records"),
        columns=[{"name": c, "id": c} for c in detail_df.columns],
        style_table={"overflowX": "auto", "width": "100%"},
        style_header={
            "backgroundColor": "#f8fafc", "color": "#475569", "fontWeight": "600",
            "fontSize": "11px", "fontFamily": "monospace", "border": "none", "borderBottom": f"1px solid {CARD_BD}",
            "padding": "6px 4px", "whiteSpace": "nowrap",
        },
        style_cell={
            "backgroundColor": CARD_BG, "color": TEXT_MAIN, "border": "none",
            "borderBottom": "1px solid #e2e8f0", "fontSize": "12px", "fontFamily": "monospace",
            "padding": "5px 4px", "textAlign": "center", "minWidth": "45px", "maxWidth": "80px",
        },
        style_cell_conditional=[
            {"if": {"column_id": "자산"}, "textAlign": "left", "fontWeight": "600", "color": ACCENT, "fontFamily": "Inter, sans-serif"},
            {"if": {"column_id": "지역"}, "textAlign": "left", "fontWeight": "600", "fontFamily": "Inter, sans-serif"},
        ],
    )

    # ── 5) Formula ──
    two_level_desc = [
        html.Div([html.Span("[ 2단계 배분 ]", style={"color": ACCENT, "fontWeight": "700"})]),
        html.Div([html.Span("Step 1. ", style={"color": ACCENT}), "자산군 비중 = SAA ± (주식점수 − 채권점수) × 2.5%p"]),
        html.Div([html.Span("Step 2. ", style={"color": ACCENT}), "개별 시그널 → 자산군 내 지역 배분 후 총비중에 곱함"]),
        html.Div([html.Span("   ", style={"color": ACCENT}), "  View 수치: SOW=+2, OW=+1, N=0, UW=−1, SUW=−2"]),
        html.Div("", style={"marginTop": "4px"}),
    ]

    formula = two_level_desc + [
        html.Div([html.Span("1. ", style={"color": ACCENT}), f"Base_i = {saa_weight:.2f} × SAA_i + {1 - saa_weight:.2f} × Peer_i"]),
        html.Div([html.Span("2. ", style={"color": ACCENT}), f"Tilt_i = Base_i × {tilt_rate:.0%}"]),
        html.Div([html.Span("3. ", style={"color": ACCENT}), "Adj_i = α × Asset_Signal_i × Tilt_i"]),
        html.Div([html.Span("4. ", style={"color": ACCENT}), "Raw_i = Base_i + Adj_i"]),
        html.Div([html.Span("5. ", style={"color": ACCENT}), "TAA = 자산군비중 × (Raw_i / Σ Raw_within_class)"]),
        html.Div([html.Span("6. ", style={"color": ACCENT}), "Range: TAA ≥ 20% → ±7.5%p,  ≥ 10% → ±5%p,  < 10% → ±2.5%p"]),
        html.Div("", style={"marginTop": "12px"}),
        html.Div([html.Span("[ 빈티지 전파 ]", style={"color": ACCENT, "fontWeight": "700"})]),
        html.Div([html.Span("Step 1. ", style={"color": ACCENT}), "빈티지 자산군비중 = 빈티지SAA ± (주식점수 − 채권점수) × 2.5%p"]),
        html.Div([html.Span("Step 2. ", style={"color": ACCENT}), "2050 Raw 기준 비례 tilt 전파"]),
        html.Div([html.Span("   ", style={"color": ACCENT}), "  tilt_ratio_i = (Raw_2050_i − SAA_2050_i) / SAA_2050_i"]),
        html.Div([html.Span("   ", style={"color": ACCENT}), "  V_Raw_i = V_SAA_i × (1 + tilt_ratio_i)"]),
        html.Div([html.Span("   ", style={"color": ACCENT}), "  V_TAA = 빈티지자산군비중 × (V_Raw_i / Σ V_Raw_within_class)"]),
        html.Div(
            f"α = {alpha:.2f} | SAA Weight = {saa_weight:.2f} | Tilt Rate = {tilt_rate:.0%}",
            style={"marginTop": "8px", "fontSize": "13px", "color": "#94a3b8"},
        ),
    ]

    return result_cards, fig, active_bets, detail_table, formula


# ──────────────────────────────────────────────
# Run
# ──────────────────────────────────────────────
if __name__ == "__main__":
    print("\n  TAA Dashboard (TDF 2050)")
    app.run(debug=True)
