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


def compute_final(df: pd.DataFrame, alpha: float) -> pd.DataFrame:
    """Final 비중 계산 후 정규화

    비대칭 Tilt: Signal 방향이 SAA 쪽이면 적극적(×1.0),
    SAA 반대 쪽이면 억제(×0.25)하여 SAA 앵커 효과를 구현.
    """
    df = df.copy()
    df["Signal"] = df["TAA"].map(TAA_MAP).fillna(0).astype(float)

    gap = df["SAA"] - df["Peer"]
    aligned = df["Signal"] * gap >= 0          # Signal이 SAA 쪽으로 향하는가
    damping = aligned * 0.75 + 0.25            # aligned=1.0, opposed=0.25
    df["Tilt"] = gap.abs() * damping

    df["Adj"] = alpha * df["Signal"] * df["Tilt"]
    df["Raw"] = df["Peer"] + df["Adj"]
    df["Raw"] = df["Raw"].clip(lower=1.0)  # floor

    total = df["Raw"].sum()
    df["Final"] = (df["Raw"] / total * 100).round(2)
    df["vs_Peer"] = (df["Final"] - df["Peer"]).round(2)

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
                        style={"fontSize": "28px", "fontWeight": "700", "margin": "0 0 4px 0", "letterSpacing": "-0.5px"},
                    ),
                    html.P(
                        "Final = Peer + α × Signal × Tilt  →  normalized to 100%",
                        style={"fontSize": "15px", "color": TEXT_DIM, "margin": 0},
                    ),
                ], style={"marginBottom": "28px"}),

                # ── Parameters ──
                html.Div(style=card_style, children=[
                    html.Div("Parameters", style=label_style),
                    html.Div(style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "24px", "alignItems": "start"}, children=[
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


# Alpha 표시
@app.callback(Output("alpha-display", "children"), Input("alpha-slider", "value"))
def update_alpha_display(val):
    return f"{val:.2f}"


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
    ],
)
def update_results(rows, alpha):
    if not rows:
        empty = html.Div("데이터를 입력하세요.", style={"color": TEXT_DIM})
        return empty, go.Figure(), empty, empty, ""

    df = pd.DataFrame(rows)
    for col in ["SAA", "Peer"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    df["TAA"] = df["TAA"].fillna("Neutral")

    result = compute_final(df, alpha)
    # 자산+지역 라벨 (차트/카드 표시용)
    if "자산" in result.columns:
        result["Label"] = result["자산"] + " " + result["지역"]
    else:
        result["Label"] = result["지역"]
    n = len(result)
    colors = REGION_COLORS[:n]

    # ── 1) Result Cards ──
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
    detail_cols = ["자산", "지역", "SAA", "Peer", "TAA", "Signal", "Tilt", "Adj", "Raw", "Final", "vs_Peer"] if "자산" in result.columns else ["지역", "SAA", "Peer", "TAA", "Signal", "Tilt", "Adj", "Raw", "Final", "vs_Peer"]
    detail_df = result[detail_cols].copy()
    rename = {"SAA": "SAA(%)", "Peer": "Peer(%)", "Signal": "Signal", "Tilt": "Tilt(%p)", "Adj": "Adj(%p)", "Raw": "Raw(%)", "Final": "Final(%)", "vs_Peer": "vs Peer(%p)"}
    detail_df = detail_df.rename(columns=rename)

    for c in ["Tilt(%p)", "Adj(%p)", "Raw(%)", "Final(%)", "vs Peer(%p)"]:
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
        html.Div([html.Span("1. ", style={"color": ACCENT}), "Raw_i = Peer_i + α × Signal_i × Tilt_i"]),
        html.Div([html.Span("2. ", style={"color": ACCENT}), "Tilt_i = |SAA_i − Peer_i| × d_i"]),
        html.Div([html.Span("   ", style={"color": ACCENT}), "d = 1.0 (Peer→SAA 방향 틸트) / 0.25 (Peer→SAA 반대 방향 틸트)"]),
        html.Div([html.Span("3. ", style={"color": ACCENT}), "Final_i = max(Raw_i, 1.0) / Σ max(Raw_j, 1.0) × 100"]),
        html.Div(
            f"α = {alpha:.2f} | TAA: SOW=+2, OW=+1, N=0, UW=−1, SUW=−2 | Floor = 1.0%",
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
