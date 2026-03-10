"""
TAA Portfolio Optimizer Dashboard
==================================
Peer 평균을 기준점으로, TAA 시그널 방향에 따라 틸트를 가감하여
Peer를 이길 수 있는 Final 비중을 산출

Formula: Final_i = normalize( Peer_i + α × Signal_i × Tilt_i )
    Tilt_i = |SAA_i - Peer_i| × d  (d=1.0 aligned, d=0.25 opposed)

Requirements:
    pip install dash pandas plotly

Run:
    python taa_portfolio_optimizer.py
"""

import json
import dash
from dash import dcc, html, dash_table, Input, Output, State, callback_context
import plotly.graph_objects as go
import pandas as pd


DEFAULT_REGIONS = [
    # 주식 70% — 내부비중(100기준): 미국70 유럽15 일본5 중국3 한국5 기타2
    {"자산": "주식", "지역": "미국","SAA": 49.0, "Peer": 45.5, "TAA": "Neutral"},
    {"자산": "주식", "지역": "유럽","SAA": 10.5, "Peer": 12.6, "TAA": "Neutral"},
    {"자산": "주식", "지역": "일본","SAA":  3.5, "Peer":  3.5, "TAA": "Neutral"},
    {"자산": "주식", "지역": "중국","SAA":  2.1, "Peer":  3.5, "TAA": "Neutral"},
    {"자산": "주식", "지역": "한국","SAA":  3.5, "Peer":  2.1, "TAA": "Neutral"},
    {"자산": "주식", "지역": "기타","SAA":  1.4, "Peer":  2.8, "TAA": "Neutral"},
    # 채권 30% — 내부비중(100기준): 미국70 한국30
    {"자산": "채권", "지역": "미국","SAA": 21.0, "Peer": 18.0, "TAA": "Neutral"},
    {"자산": "채권", "지역": "한국","SAA":  9.0, "Peer": 12.0, "TAA": "Neutral"},
]

TAA_MAP = {"Strong OW": 2, "Overweight": 1, "Neutral": 0, "Underweight": -1, "Strong UW": -2}
REGION_COLORS = ["#6366f1", "#f59e0b", "#ec4899", "#06b6d4", "#10b981", "#f97316", "#8b5cf6", "#14b8a6"]


def compute_final(df: pd.DataFrame, alpha: float, damping_opposed: float = 0.25, min_tilt_rate: float = 0.20) -> pd.DataFrame:
    """Final 비중 계산 후 정규화

    비대칭 Tilt: Signal 방향이 SAA 쪽이면 적극적(×1.0),
    SAA 반대 쪽이면 억제(×damping_opposed)하여 SAA 앵커 효과를 구현.
    min_tilt_rate: gap=0일 때도 최소 Tilt = Peer × min_tilt_rate 보장.
    """
    df = df.copy()
    df["Signal"] = df["TAA"].map(TAA_MAP).fillna(0).astype(float)

    gap = df["SAA"] - df["Peer"]
    aligned = df["Signal"] * gap >= 0          # Signal이 SAA 쪽으로 향하는가
    damping = aligned * (1.0 - damping_opposed) + damping_opposed
    min_tilt = df["Peer"] * min_tilt_rate
    df["Tilt"] = (gap.abs() * damping).clip(lower=min_tilt)

    df["Adj"] = alpha * df["Signal"] * df["Tilt"]
    df["Raw"] = df["Peer"] + df["Adj"]
    df["Raw"] = df["Raw"].clip(lower=1.0)  # floor

    total = df["Raw"].sum()
    df["Final"] = (df["Raw"] / total * 100).round(2)
    df["vs_Peer"] = (df["Final"] - df["Peer"]).round(2)

    # 디폴트 범위: Final ≥ 10%이면 ±5%p, 미만이면 ±2.5%p (비음수)
    half_w = df["Final"].apply(lambda v: 5.0 if v >= 10 else 2.5)
    df["Final_Low"] = (df["Final"] - half_w).clip(lower=0.0).round(2)
    df["Final_High"] = (df["Final"] + half_w).round(2)

    return df


app = dash.Dash(
    __name__,
    title="TAA Portfolio Optimizer",
    suppress_callback_exceptions=True,
)

# 드롭다운 셀 텍스트 색상을 밝게
app.index_string = '''<!DOCTYPE html>
<html>
<head>{%metas%}<title>{%title%}</title>{%favicon%}{%css%}
<style>
.Select-value-label, .Select-placeholder, .Select-input input {
    color: #e2e5ea !important;
}
.Select-menu-outer { background-color: #1a1d24 !important; }
.Select-option { background-color: #1a1d24 !important; color: #e2e5ea !important; }
.Select-option.is-focused { background-color: #2a2d34 !important; }
</style>
</head>
<body>{%app_entry%}<footer>{%config%}{%scripts%}{%renderer%}</footer>
</body>
</html>'''

# ── 스타일 상수 ──
DARK_BG   = "#0d0f13"
CARD_BG   = "#13161c"
CARD_BD   = "#1e2128"
TEXT_MAIN  = "#e2e5ea"
TEXT_DIM   = "#6b7280"
ACCENT     = "#6366f1"
GREEN      = "#10b981"
RED        = "#ef4444"

card_style = {
    "backgroundColor": CARD_BG,
    "border": f"1px solid {CARD_BD}",
    "borderRadius": "12px",
    "padding": "24px",
    "marginBottom": "20px",
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
    style={"backgroundColor": DARK_BG, "minHeight": "100vh", "padding": "30px 20px", "fontFamily": "Inter, sans-serif", "color": TEXT_MAIN},
    children=[
        html.Div(
            style={"maxWidth": "1080px", "margin": "0 auto"},
            children=[
                # ── Header ──
                html.Div([
                    html.H1(
                        "TAA Portfolio Optimizer",
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
                                html.Span("α (확신도)", style={"fontSize": "15px", "color": "#94a3b8"}),
                                html.Span(id="alpha-display", style={"fontSize": "18px", "fontWeight": "600", "fontFamily": "monospace", "color": ACCENT}),
                            ]),
                            dcc.Slider(
                                id="alpha-slider", min=0, max=1, step=0.05, value=0.5,
                                marks={0: {"label": "0.0", "style": {"color": TEXT_DIM, "fontSize": "12px"}},
                                       0.5: {"label": "0.5", "style": {"color": TEXT_DIM, "fontSize": "12px"}},
                                       1: {"label": "1.0", "style": {"color": TEXT_DIM, "fontSize": "12px"}}},
                                tooltip={"placement": "bottom", "always_visible": False},
                            ),
                            html.Div(style={"display": "flex", "justifyContent": "space-between", "fontSize": "12px", "color": "#4b5563"}, children=[
                                html.Span("보수적"), html.Span("적극적"),
                            ]),
                        ]),
                        # Damping slider
                        html.Div([
                            html.Div(style={"display": "flex", "justifyContent": "space-between", "marginBottom": "4px"}, children=[
                                html.Span("Damping (반대방향 억제)", style={"fontSize": "15px", "color": "#94a3b8"}),
                                html.Span(id="damping-display", style={"fontSize": "18px", "fontWeight": "600", "fontFamily": "monospace", "color": ACCENT}),
                            ]),
                            dcc.Slider(
                                id="damping-slider", min=0, max=1, step=0.05, value=0.25,
                                marks={0: {"label": "0.0", "style": {"color": TEXT_DIM, "fontSize": "12px"}},
                                       0.25: {"label": "0.25", "style": {"color": TEXT_DIM, "fontSize": "12px"}},
                                       1: {"label": "1.0", "style": {"color": TEXT_DIM, "fontSize": "12px"}}},
                                tooltip={"placement": "bottom", "always_visible": False},
                            ),
                            html.Div(style={"display": "flex", "justifyContent": "space-between", "fontSize": "12px", "color": "#4b5563"}, children=[
                                html.Span("강한 억제"), html.Span("억제 없음"),
                            ]),
                        ]),
                        # Min Tilt Rate slider
                        html.Div([
                            html.Div(style={"display": "flex", "justifyContent": "space-between", "marginBottom": "4px"}, children=[
                                html.Span("Min Tilt Rate", style={"fontSize": "15px", "color": "#94a3b8"}),
                                html.Span(id="mintilt-display", style={"fontSize": "18px", "fontWeight": "600", "fontFamily": "monospace", "color": ACCENT}),
                            ]),
                            dcc.Slider(
                                id="mintilt-slider", min=0, max=0.5, step=0.05, value=0.20,
                                marks={0: {"label": "0%", "style": {"color": TEXT_DIM, "fontSize": "12px"}},
                                       0.2: {"label": "20%", "style": {"color": TEXT_DIM, "fontSize": "12px"}},
                                       0.5: {"label": "50%", "style": {"color": TEXT_DIM, "fontSize": "12px"}}},
                                tooltip={"placement": "bottom", "always_visible": False},
                            ),
                            html.Div(style={"display": "flex", "justifyContent": "space-between", "fontSize": "12px", "color": "#4b5563"}, children=[
                                html.Span("최소 보장 없음"), html.Span("Peer의 50%"),
                            ]),
                        ]),
                    ]),
                ]),

                # ── Region Input Table ──
                html.Div(style=card_style, children=[
                    html.Div("Region Inputs", style=label_style),
                    html.Div(
                        "SAA, Peer(%), TAA 의견을 직접 수정할 수 있습니다. 행 추가/삭제도 가능합니다.",
                        style={"fontSize": "14px", "color": TEXT_DIM, "marginBottom": "12px"},
                    ),
                    dash_table.DataTable(
                        id="region-table",
                        columns=[
                            {"name": "자산", "id": "자산", "editable": True},
                            {"name": "지역", "id": "지역", "editable": True},
                            {"name": "SAA (%)", "id": "SAA", "type": "numeric", "editable": True},
                            {"name": "Peer (%)", "id": "Peer", "type": "numeric", "editable": True},
                            {"name": "TAA", "id": "TAA", "presentation": "dropdown", "editable": True},
                        ],
                        data=DEFAULT_REGIONS,
                        dropdown={
                            "TAA": {
                                "options": [{"label": t, "value": t} for t in ["Strong OW", "Overweight", "Neutral", "Underweight", "Strong UW"]],
                            }
                        },
                        editable=True,
                        row_deletable=True,
                        style_table={"overflowX": "auto"},
                        style_header={
                            "backgroundColor": "#1a1d24",
                            "color": "#94a3b8",
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
                            "borderBottom": f"1px solid #1a1d24",
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
                            {"if": {"filter_query": '{TAA} = "Strong OW"', "column_id": "TAA"},
                             "color": "#34d399", "fontWeight": "700"},
                            {"if": {"filter_query": '{TAA} = "Overweight"', "column_id": "TAA"},
                             "color": "#34d399", "fontWeight": "600"},
                            {"if": {"filter_query": '{TAA} = "Neutral"', "column_id": "TAA"},
                             "color": TEXT_MAIN},
                            {"if": {"filter_query": '{TAA} = "Underweight"', "column_id": "TAA"},
                             "color": "#f87171", "fontWeight": "600"},
                            {"if": {"filter_query": '{TAA} = "Strong UW"', "column_id": "TAA"},
                             "color": "#f87171", "fontWeight": "700"},
                        ],
                    ),
                    html.Br(),
                    html.Button(
                        "+ 지역 추가",
                        id="add-row-btn",
                        n_clicks=0,
                        style={
                            "backgroundColor": "#1a1d24", "color": ACCENT, "border": f"1px dashed {ACCENT}40",
                            "borderRadius": "6px", "padding": "8px 16px", "fontSize": "14px",
                            "cursor": "pointer", "fontWeight": "600",
                        },
                    ),
                ]),

                # ── Range Confirmation ──
                html.Div(style=card_style, children=[
                    html.Div("Range Confirmation", style=label_style),
                    html.Div(
                        "디폴트 범위는 Final 값의 ±5% (최소 ±0.3%p)로 자동 설정됩니다. Low/High를 수기로 조정하여 확정하세요.",
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
                    html.Div("Final Allocation", style=label_style),
                    html.Div(id="result-cards"),
                    html.Br(),
                    dcc.Graph(id="comparison-chart", config={"displayModeBar": False}),
                ]),

                # ── Active Bets ──
                html.Div(style=card_style, children=[
                    html.Div("Active Bets vs Peer", style=label_style),
                    html.Div(id="active-bets"),
                ]),

                # ── Detailed Result Table ──
                html.Div(style=card_style, children=[
                    html.Div("Detailed Breakdown", style=label_style),
                    html.Div(id="result-table"),
                ]),

                # ── Formula ──
                html.Div(style=card_style, children=[
                    html.Div("Formula Reference", style=label_style),
                    html.Div(id="formula-text", style={"fontFamily": "monospace", "fontSize": "15px", "lineHeight": "2.0", "color": "#94a3b8"}),
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
    rows.append({"자산": "주식", "지역": "신규", "SAA": 0, "Peer": 0, "TAA": "Neutral"})
    return rows


# 파라미터 표시
@app.callback(Output("alpha-display", "children"), Input("alpha-slider", "value"))
def update_alpha_display(val):
    return f"{val:.2f}"

@app.callback(Output("damping-display", "children"), Input("damping-slider", "value"))
def update_damping_display(val):
    return f"{val:.2f}"

@app.callback(Output("mintilt-display", "children"), Input("mintilt-slider", "value"))
def update_mintilt_display(val):
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
        Input("damping-slider", "value"),
        Input("mintilt-slider", "value"),
    ],
)
def update_range_table(rows, alpha, damping_opposed, min_tilt_rate):
    if not rows:
        return html.Div("데이터를 입력하세요.", style={"color": TEXT_DIM}), None, ""

    df = pd.DataFrame(rows)
    for col in ["SAA", "Peer"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    df["TAA"] = df["TAA"].fillna("Neutral")

    result = compute_final(df, alpha, damping_opposed, min_tilt_rate)
    if "자산" in result.columns:
        result["Label"] = result["자산"] + " " + result["지역"]
    else:
        result["Label"] = result["지역"]

    range_data = result[["Label", "Final", "Final_Low", "Final_High"]].to_dict("records")

    range_table = dash_table.DataTable(
        id="range-table",
        columns=[
            {"name": "자산/지역", "id": "Label", "editable": False},
            {"name": "Final (%)", "id": "Final", "type": "numeric", "editable": False},
            {"name": "Low (%)", "id": "Final_Low", "type": "numeric", "editable": True},
            {"name": "High (%)", "id": "Final_High", "type": "numeric", "editable": True},
        ],
        data=range_data,
        style_header={
            "backgroundColor": "#1a1d24", "color": "#94a3b8", "fontWeight": "600",
            "fontSize": "13px", "fontFamily": "monospace", "border": "none",
            "borderBottom": f"1px solid {CARD_BD}",
        },
        style_cell={
            "backgroundColor": CARD_BG, "color": TEXT_MAIN, "border": "none",
            "borderBottom": "1px solid #1a1d24", "fontSize": "14px", "fontFamily": "monospace",
            "padding": "10px 12px", "textAlign": "center",
        },
        style_cell_conditional=[
            {"if": {"column_id": "Label"}, "textAlign": "left", "fontWeight": "600", "fontFamily": "Inter, sans-serif"},
        ],
        style_data_conditional=[
            {"if": {"column_id": "Final_Low"}, "backgroundColor": "#1a1d24", "color": "#facc15"},
            {"if": {"column_id": "Final_High"}, "backgroundColor": "#1a1d24", "color": "#facc15"},
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
        Input("damping-slider", "value"),
        Input("mintilt-slider", "value"),
        Input("confirmed-range-store", "data"),
    ],
)
def update_results(rows, alpha, damping_opposed, min_tilt_rate, confirmed_range):
    if not rows:
        empty = html.Div("데이터를 입력하세요.", style={"color": TEXT_DIM})
        return empty, go.Figure(), empty, empty, ""

    df = pd.DataFrame(rows)
    for col in ["SAA", "Peer"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    df["TAA"] = df["TAA"].fillna("Neutral")

    result = compute_final(df, alpha, damping_opposed, min_tilt_rate)
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
                result.at[i, "Final_Low"] = float(cr[lbl].get("Final_Low", row["Final_Low"]))
                result.at[i, "Final_High"] = float(cr[lbl].get("Final_High", row["Final_High"]))

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
                    "backgroundColor": DARK_BG,
                    "borderRadius": "10px",
                    "padding": "16px 12px",
                    "textAlign": "center",
                    "borderTop": f"3px solid {colors[i]}",
                },
                children=[
                    html.Div(row["Label"], style={"fontSize": "14px", "color": TEXT_DIM, "marginBottom": "4px"}),
                    html.Div([
                        html.Span(f"{row['Final']:.1f}", style={"fontSize": "32px", "fontWeight": "700", "fontFamily": "monospace"}),
                        html.Span("%", style={"fontSize": "16px", "color": TEXT_DIM}),
                    ]),
                    html.Div(
                        f"({row['Final_Low']:.1f} – {row['Final_High']:.1f}%)",
                        style={"fontSize": "13px", "fontFamily": "monospace", "color": "#facc15", "marginTop": "2px"},
                    ),
                    html.Div(
                        f"vs Peer {'+' if diff > 0 else ''}{diff:.1f}%p",
                        style={"fontSize": "14px", "fontFamily": "monospace", "fontWeight": "600", "color": diff_color, "marginTop": "4px"},
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
        marker_color="#4b5563",
        text=result["SAA"].apply(lambda v: f"{v:.1f}%"),
        textposition="inside",
        textfont=dict(size=12, family="monospace", color="white"),
    ))
    fig.add_trace(go.Bar(
        name="Peer",
        x=result["Label"],
        y=result["Peer"],
        marker_color="#6b7280",
        text=result["Peer"].apply(lambda v: f"{v:.1f}%"),
        textposition="inside",
        textfont=dict(size=12, family="monospace", color="white"),
    ))
    fig.add_trace(go.Bar(
        name="Final",
        x=result["Label"],
        y=result["Final"],
        marker_color=ACCENT,
        text=result["Final"].apply(lambda v: f"{v:.1f}%"),
        textposition="inside",
        textfont=dict(size=12, family="monospace", color="white"),
        error_y=dict(
            type="data",
            symmetric=False,
            array=(result["Final_High"] - result["Final"]).tolist(),
            arrayminus=(result["Final"] - result["Final_Low"]).tolist(),
            color="#facc15",
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
        yaxis=dict(gridcolor="#1e2128", title=None, ticksuffix="%"),
        xaxis=dict(title=None),
    )

    # ── 3) Active Bets ──
    ow = result[result["vs_Peer"] > 0.05]
    uw = result[result["vs_Peer"] < -0.05]
    total_active = result["vs_Peer"].abs().sum() / 2

    ow_items = [
        html.Div(
            style={"display": "flex", "justifyContent": "space-between", "padding": "4px 0", "fontSize": "15px"},
            children=[
                html.Span(row["Label"]),
                html.Span(f"+{row['vs_Peer']:.1f}%p", style={"fontFamily": "monospace", "color": GREEN, "fontWeight": "600"}),
            ],
        )
        for _, row in ow.iterrows()
    ]
    uw_items = [
        html.Div(
            style={"display": "flex", "justifyContent": "space-between", "padding": "4px 0", "fontSize": "15px"},
            children=[
                html.Span(row["Label"]),
                html.Span(f"{row['vs_Peer']:.1f}%p", style={"fontFamily": "monospace", "color": RED, "fontWeight": "600"}),
            ],
        )
        for _, row in uw.iterrows()
    ]

    active_bets = html.Div([
        html.Div(style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "20px"}, children=[
            html.Div([
                html.Div("▲ Overweight", style={"fontSize": "14px", "color": GREEN, "fontWeight": "600", "marginBottom": "8px"}),
                *(ow_items if ow_items else [html.Div("없음", style={"fontSize": "14px", "color": "#4b5563"})]),
            ]),
            html.Div([
                html.Div("▼ Underweight", style={"fontSize": "14px", "color": RED, "fontWeight": "600", "marginBottom": "8px"}),
                *(uw_items if uw_items else [html.Div("없음", style={"fontSize": "14px", "color": "#4b5563"})]),
            ]),
        ]),
        html.Div(
            f"Total Active Risk: ±{total_active:.1f}%p (one-way)",
            style={
                "marginTop": "12px", "padding": "8px 12px", "backgroundColor": DARK_BG,
                "borderRadius": "6px", "fontSize": "14px", "color": TEXT_DIM, "fontFamily": "monospace",
            },
        ),
    ])

    # ── 4) Detail Table ──
    detail_cols = ["자산", "지역", "SAA", "Peer", "TAA", "Signal", "Tilt", "Adj", "Raw", "Final", "Final_Low", "Final_High", "vs_Peer"] if "자산" in result.columns else ["지역", "SAA", "Peer", "TAA", "Signal", "Tilt", "Adj", "Raw", "Final", "Final_Low", "Final_High", "vs_Peer"]
    detail_df = result[detail_cols].copy()
    rename = {"SAA": "SAA(%)", "Peer": "Peer(%)", "Signal": "Signal", "Tilt": "Tilt(%p)", "Adj": "Adj(%p)", "Raw": "Raw(%)", "Final": "Final(%)", "Final_Low": "Low(%)", "Final_High": "High(%)", "vs_Peer": "vs Peer(%p)"}
    detail_df = detail_df.rename(columns=rename)

    for c in ["Tilt(%p)", "Adj(%p)", "Raw(%)", "Final(%)", "Low(%)", "High(%)", "vs Peer(%p)"]:
        use_sign = "vs" in c or "Adj" in c
        detail_df[c] = detail_df[c].apply(lambda v, s=use_sign: f"{v:+.2f}" if s else f"{v:.2f}")

    detail_table = dash_table.DataTable(
        data=detail_df.to_dict("records"),
        columns=[{"name": c, "id": c} for c in detail_df.columns],
        style_header={
            "backgroundColor": "#1a1d24", "color": "#94a3b8", "fontWeight": "600",
            "fontSize": "13px", "fontFamily": "monospace", "border": "none", "borderBottom": f"1px solid {CARD_BD}",
        },
        style_cell={
            "backgroundColor": CARD_BG, "color": TEXT_MAIN, "border": "none",
            "borderBottom": "1px solid #1a1d24", "fontSize": "14px", "fontFamily": "monospace",
            "padding": "8px 10px", "textAlign": "center",
        },
        style_cell_conditional=[
            {"if": {"column_id": "자산"}, "textAlign": "left", "fontWeight": "600", "color": ACCENT, "fontFamily": "Inter, sans-serif"},
            {"if": {"column_id": "지역"}, "textAlign": "left", "fontWeight": "600", "fontFamily": "Inter, sans-serif"},
        ],
    )

    # ── 5) Formula ──
    formula = [
        html.Div([html.Span("1. ", style={"color": ACCENT}), "Signal_i = TAA 의견의 수치 변환 (SOW=+2, OW=+1, N=0, UW=−1, SUW=−2)"]),
        html.Div([html.Span("2. ", style={"color": ACCENT}), f"Tilt_i = max( |SAA_i − Peer_i| × d_i,  Peer_i × {min_tilt_rate:.0%} )"]),
        html.Div([html.Span("   ", style={"color": ACCENT}), f"d_i = 1.0 (Signal이 SAA 방향)  /  {damping_opposed:.2f} (Signal이 SAA 반대 방향)"]),
        html.Div([html.Span("3. ", style={"color": ACCENT}), "Adj_i = α × Signal_i × Tilt_i"]),
        html.Div([html.Span("4. ", style={"color": ACCENT}), "Raw_i = max( Peer_i + Adj_i,  1.0 )"]),
        html.Div([html.Span("5. ", style={"color": ACCENT}), "Final_i = Raw_i / Σ Raw_j × 100"]),
        html.Div([html.Span("6. ", style={"color": ACCENT}), "Range: Final ≥ 10% → ±5%p,  Final < 10% → ±2.5%p  (수기 조정 가능)"]),
        html.Div(
            f"α = {alpha:.2f} | Damping = {damping_opposed:.2f} | Min Tilt Rate = {min_tilt_rate:.0%} | Floor = 1.0%",
            style={"marginTop": "8px", "fontSize": "13px", "color": "#4b5563"},
        ),
    ]

    return result_cards, fig, active_bets, detail_table, formula


# ──────────────────────────────────────────────
# Run
# ──────────────────────────────────────────────
if __name__ == "__main__":
    print("\n  TAA Portfolio Optimizer")
    app.run(debug=True)
