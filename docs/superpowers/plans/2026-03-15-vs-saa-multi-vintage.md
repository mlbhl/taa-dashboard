# vs SAA & Multi-Vintage TDF Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add vs SAA display to main 2050 results and propagate TAA tilts to other TDF vintages (2030/2040/2060) using proportional Raw-based tilt ratios.

**Architecture:** Modify existing compute functions to add vs_SAA. Add new `derive_vintage_saa()` and `propagate_to_vintage()` functions. Add UI sections for vintage SAA input and vintage results display. All in `taa_portfolio_optimizer.py`.

**Tech Stack:** Dash, Pandas, Plotly (existing)

---

## Chunk 1: vs SAA Column + Vintage Computation Logic

### Task 1: Add vs_SAA to compute functions

**Files:**
- Modify: `taa_portfolio_optimizer.py:59-90` (compute_final)
- Modify: `taa_portfolio_optimizer.py:93-121` (compute_final_weighted)

- [ ] **Step 1: Add vs_SAA to compute_final**

After line 83 (`df["vs_Peer"]`), add:
```python
    df["vs_SAA"] = (df["Final"] - df["SAA"]).round(2)
```

- [ ] **Step 2: Add vs_SAA to compute_final_weighted**

After line 115 (`df["vs_Peer"]`), add:
```python
    df["vs_SAA"] = (df["Final"] - df["SAA"]).round(2)
```

- [ ] **Step 3: Verify compute functions produce vs_SAA**

Run:
```bash
python -c "
import pandas as pd
from taa_portfolio_optimizer import compute_final, compute_final_weighted, DEFAULT_REGIONS
df = pd.DataFrame(DEFAULT_REGIONS)
r = compute_final(df, 0.5)
assert 'vs_SAA' in r.columns, 'vs_SAA missing from compute_final'
r2 = compute_final_weighted(df, 0.5)
assert 'vs_SAA' in r2.columns, 'vs_SAA missing from compute_final_weighted'
print('vs_SAA OK')
"
```
Expected: `vs_SAA OK`

- [ ] **Step 4: Commit**

```bash
git add taa_portfolio_optimizer.py
git commit -m "Add vs_SAA column to compute functions"
```

### Task 2: Add DEFAULT_VINTAGES and internal weight constants

**Files:**
- Modify: `taa_portfolio_optimizer.py:27-46` (constants section)

- [ ] **Step 1: Add internal weight constants and DEFAULT_VINTAGES**

After `DEFAULT_CLASS_SIGNALS` (line 43) and before `TAA_MAP` (line 45), add:

```python
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
```

- [ ] **Step 2: Verify import**

Run:
```bash
python -c "from taa_portfolio_optimizer import EQUITY_INTERNAL_WEIGHTS, BOND_INTERNAL_WEIGHTS, DEFAULT_VINTAGES; print('Constants OK')"
```
Expected: `Constants OK`

- [ ] **Step 3: Commit**

```bash
git add taa_portfolio_optimizer.py
git commit -m "Add vintage SAA constants and internal weights"
```

### Task 3: Add derive_vintage_saa function

**Files:**
- Modify: `taa_portfolio_optimizer.py` (after compute_final_weighted, before `app = dash.Dash`)

- [ ] **Step 1: Add derive_vintage_saa function**

Insert after `compute_final_weighted` (after line 121):

```python
def derive_vintage_saa(equity_pct: float, bond_pct: float) -> list[dict]:
    """빈티지의 주식/채권 총비율에서 지역별 SAA를 산출 (2050 내부비중 기준)"""
    rows = []
    for region, weight in EQUITY_INTERNAL_WEIGHTS.items():
        rows.append({"자산": "주식", "지역": region, "SAA": round(equity_pct * weight / 100, 2)})
    for region, weight in BOND_INTERNAL_WEIGHTS.items():
        rows.append({"자산": "채권", "지역": region, "SAA": round(bond_pct * weight / 100, 2)})
    return rows
```

- [ ] **Step 2: Verify derive_vintage_saa**

Run:
```bash
python -c "
from taa_portfolio_optimizer import derive_vintage_saa
rows = derive_vintage_saa(55, 45)
total = sum(r['SAA'] for r in rows)
assert abs(total - 100.0) < 0.1, f'Total {total} != 100'
assert rows[0] == {'자산': '주식', '지역': '미국', 'SAA': 38.5}
print(f'derive OK, total={total}')
for r in rows:
    print(f\"  {r['자산']} {r['지역']}: {r['SAA']}%\")
"
```
Expected: `derive OK, total=100.0` with correct sub-asset SAAs

- [ ] **Step 3: Commit**

```bash
git add taa_portfolio_optimizer.py
git commit -m "Add derive_vintage_saa function"
```

### Task 4: Add propagate_to_vintage function

**Files:**
- Modify: `taa_portfolio_optimizer.py` (after derive_vintage_saa)

- [ ] **Step 1: Add propagate_to_vintage function**

Insert after `derive_vintage_saa`:

```python
def propagate_to_vintage(result_2050: pd.DataFrame, vintage_saa: list[dict]) -> pd.DataFrame:
    """2050 Raw 기준 비례 tilt를 다른 빈티지에 전파

    tilt_ratio = (Raw_2050 - SAA_2050) / SAA_2050  (SAA >= 0.5%)
               = Raw_2050 - SAA_2050                (SAA < 0.5%, absolute fallback)
    Vintage_Raw = Vintage_SAA × (1 + tilt_ratio)    or  Vintage_SAA + absolute_tilt
    Final = normalize(Vintage_Raw)
    """
    vdf = pd.DataFrame(vintage_saa)
    raw_2050 = result_2050["Raw"].values
    saa_2050 = result_2050["SAA"].values

    v_raw = []
    for i in range(len(vdf)):
        saa_i = saa_2050[i]
        raw_i = raw_2050[i]
        v_saa_i = vdf.at[i, "SAA"]
        if saa_i >= 0.5:
            tilt_ratio = (raw_i - saa_i) / saa_i
            v_raw.append(v_saa_i * (1 + tilt_ratio))
        else:
            absolute_tilt = raw_i - saa_i
            v_raw.append(v_saa_i + absolute_tilt)

    vdf["Raw"] = [max(r, 1.0) for r in v_raw]
    total = vdf["Raw"].sum()
    vdf["Final"] = (vdf["Raw"] / total * 100).round(2)
    vdf["vs_SAA"] = (vdf["Final"] - vdf["SAA"]).round(2)

    half_w = vdf["Final"].apply(lambda v: 7.5 if v >= 20 else 5.0 if v >= 10 else 2.5)
    vdf["Final_Low"] = (vdf["Final"] - half_w).clip(lower=0.0).round(2)
    vdf["Final_High"] = (vdf["Final"] + half_w).round(2)

    return vdf
```

- [ ] **Step 2: Verify propagate_to_vintage**

Run:
```bash
python -c "
import pandas as pd
from taa_portfolio_optimizer import compute_final, propagate_to_vintage, derive_vintage_saa, DEFAULT_REGIONS

df = pd.DataFrame(DEFAULT_REGIONS)
# Set US equity to OW for visible tilt
df.loc[0, 'TAA'] = 'Overweight'
result = compute_final(df, 0.5, class_signals={'주식': 0, '채권': 0})

vintage_saa = derive_vintage_saa(55, 45)
vr = propagate_to_vintage(result, vintage_saa)
total = vr['Final'].sum()
assert abs(total - 100.0) < 0.1, f'Total {total} != 100'
assert 'vs_SAA' in vr.columns
print(f'propagate OK, total={total:.2f}')
for _, r in vr.iterrows():
    print(f\"  {r['자산']} {r['지역']}: SAA={r['SAA']:.2f} Final={r['Final']:.2f} vs_SAA={r['vs_SAA']:+.2f}\")
"
```
Expected: US equity has positive vs_SAA, total ~100

- [ ] **Step 3: Commit**

```bash
git add taa_portfolio_optimizer.py
git commit -m "Add propagate_to_vintage function"
```

## Chunk 2: UI Updates — vs SAA Display

### Task 5: Add vs SAA to Result Cards

**Files:**
- Modify: `taa_portfolio_optimizer.py:769-800` (result cards in update_results)

- [ ] **Step 1: Add vs SAA line to each card**

In the `update_results` function, in the card children list (around line 794-797), after the vs Peer `html.Div`, add a vs SAA div. Replace the card children block:

Find this block (lines 784-798):
```python
                children=[
                    html.Div(row["Label"], style={"fontSize": "14px", "color": TEXT_DIM, "marginBottom": "4px"}),
                    html.Div([
                        html.Span(f"{row['Final']:.1f}", style={"fontSize": "32px", "fontWeight": "700", "fontFamily": "monospace"}),
                        html.Span("%", style={"fontSize": "16px", "color": TEXT_DIM}),
                    ]),
                    html.Div(
                        f"({row['Final_Low']:.1f} – {row['Final_High']:.1f}%)",
                        style={"fontSize": "13px", "fontFamily": "monospace", "color": "#b45309", "marginTop": "2px"},
                    ),
                    html.Div(
                        f"vs Peer {'+' if diff > 0 else ''}{diff:.1f}%p",
                        style={"fontSize": "14px", "fontFamily": "monospace", "fontWeight": "600", "color": diff_color, "marginTop": "4px"},
                    ),
                ],
```

Replace with:
```python
                children=[
                    html.Div(row["Label"], style={"fontSize": "14px", "color": TEXT_DIM, "marginBottom": "4px"}),
                    html.Div([
                        html.Span(f"{row['Final']:.1f}", style={"fontSize": "32px", "fontWeight": "700", "fontFamily": "monospace"}),
                        html.Span("%", style={"fontSize": "16px", "color": TEXT_DIM}),
                    ]),
                    html.Div(
                        f"({row['Final_Low']:.1f} – {row['Final_High']:.1f}%)",
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
```

- [ ] **Step 2: Verify app imports without error**

Run:
```bash
python -c "import taa_portfolio_optimizer; print('Import OK')"
```
Expected: `Import OK`

- [ ] **Step 3: Commit**

```bash
git add taa_portfolio_optimizer.py
git commit -m "Add vs SAA to result cards"
```

### Task 6: Add vs SAA to Detail Table

**Files:**
- Modify: `taa_portfolio_optimizer.py:899-916` (detail table columns in update_results)

- [ ] **Step 1: Add vs_SAA to rest_cols and rename map**

In the detail table section, change `rest_cols` (line 906) from:
```python
    rest_cols = ["Tilt", "Adj", "Raw", "Final", "Final_Low", "Final_High", "vs_Peer"]
```
to:
```python
    rest_cols = ["Tilt", "Adj", "Raw", "Final", "Final_Low", "Final_High", "vs_Peer", "vs_SAA"]
```

In the `rename` dict (line 910), add `"vs_SAA": "vs SAA(%p)"`:
```python
    rename = {"SAA": "SAA(%)", "Peer": "Peer(%)", "Base": "Base(%)", "Signal_Class": "Class Sig", "Signal_Asset": "Asset Sig", "Signal": "Signal", "Tilt": "Tilt(%p)", "Adj": "Adj(%p)", "Raw": "Raw(%)", "Final": "Final(%)", "Final_Low": "Low(%)", "Final_High": "High(%)", "vs_Peer": "vs Peer(%p)", "vs_SAA": "vs SAA(%p)"}
```

In the `fmt_cols` list (line 913), add `"vs SAA(%p)"`:
```python
    fmt_cols = [c for c in ["Class Sig", "Asset Sig", "Base(%)", "Tilt(%p)", "Adj(%p)", "Raw(%)", "Final(%)", "Low(%)", "High(%)", "vs Peer(%p)", "vs SAA(%p)"] if c in detail_df.columns]
```

- [ ] **Step 2: Verify import**

Run:
```bash
python -c "import taa_portfolio_optimizer; print('Import OK')"
```

- [ ] **Step 3: Commit**

```bash
git add taa_portfolio_optimizer.py
git commit -m "Add vs SAA to detail table"
```

### Task 7: Add vs SAA to Active Bets section

**Files:**
- Modify: `taa_portfolio_optimizer.py:853-897` (active bets in update_results)

- [ ] **Step 1: Update Active Bets card title in layout**

In `app.layout`, change the Active Bets card title from `"Active Bets vs Peer"` to `"Active Bets"`.

- [ ] **Step 2: Replace Active Bets section in callback**

Replace the active bets section (from `# ── 3) Active Bets ──` through the closing of `active_bets = html.Div([...])`) with:

```python
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
```

- [ ] **Step 3: Verify import**

Run:
```bash
python -c "import taa_portfolio_optimizer; print('Import OK')"
```

- [ ] **Step 4: Commit**

```bash
git add taa_portfolio_optimizer.py
git commit -m "Add vs SAA to active bets section"
```

## Chunk 3: Multi-Vintage UI

### Task 8: Add Vintage SAA input table to layout

**Files:**
- Modify: `taa_portfolio_optimizer.py` layout section (after Active Bets card, before Detailed Breakdown)

- [ ] **Step 1: Add Vintage SAA card to layout**

In `app.layout`, after the Active Bets card (`html.Div(id="active-bets")`) and before the Detailed Breakdown card, insert:

```python
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
```

- [ ] **Step 2: Verify import**

Run:
```bash
python -c "import taa_portfolio_optimizer; print('Import OK')"
```

- [ ] **Step 3: Commit**

```bash
git add taa_portfolio_optimizer.py
git commit -m "Add vintage SAA input and results cards to layout"
```

### Task 9: Add vintage row add callback

**Files:**
- Modify: `taa_portfolio_optimizer.py` (callbacks section, after `add_row`)

- [ ] **Step 1: Add vintage row add callback**

After the existing `add_row` callback (around line 577), add:

```python
@app.callback(
    Output("vintage-table", "data"),
    Input("add-vintage-btn", "n_clicks"),
    State("vintage-table", "data"),
    prevent_initial_call=True,
)
def add_vintage_row(n_clicks, rows):
    rows.append({"Vintage": "20XX", "Equity": 50, "Bond": 50})
    return rows
```

- [ ] **Step 2: Verify import**

Run:
```bash
python -c "import taa_portfolio_optimizer; print('Import OK')"
```

- [ ] **Step 3: Commit**

```bash
git add taa_portfolio_optimizer.py
git commit -m "Add vintage row add callback"
```

### Task 10: Add vintage results callback

**Files:**
- Modify: `taa_portfolio_optimizer.py` (callbacks section, after vintage row add callback)

- [ ] **Step 1: Add vintage computation callback**

Add a new callback that computes vintage results. Place it after the vintage row add callback:

```python
@app.callback(
    [Output("vintage-results", "children"),
     Output("vintage-warning", "children")],
    [Input("region-table", "data"),
     Input("alpha-slider", "value"),
     Input("damping-slider", "value"),
     Input("mintilt-slider", "value"),
     Input("mode-radio", "value"),
     Input("w-slider", "value"),
     Input("tiltrate-slider", "value"),
     Input("class-signal-table", "data"),
     Input("vintage-table", "data")],
)
def update_vintage_results(rows, alpha, damping_opposed, min_tilt_rate, mode, saa_weight, tilt_rate, class_rows, vintage_rows):
    if not rows or not vintage_rows:
        return html.Div("데이터를 입력하세요.", style={"color": TEXT_DIM}), ""

    # Compute 2050 result
    df = pd.DataFrame(rows)
    for col in ["SAA", "Peer"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    df["TAA"] = df["TAA"].fillna("Neutral")

    class_signals = {}
    if class_rows:
        for r in class_rows:
            class_signals[r["자산군"]] = TAA_MAP.get(r.get("TAA", "Neutral"), 0)

    if mode == "peer":
        result_2050 = compute_final(df, alpha, damping_opposed, min_tilt_rate, class_signals)
    else:
        result_2050 = compute_final_weighted(df, alpha, saa_weight, tilt_rate, class_signals)

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
        vr = propagate_to_vintage(result_2050, vintage_saa)
        vr["Label"] = vr["자산"] + " " + vr["지역"]

        # Build compact table
        display_df = vr[["Label", "SAA", "Final", "vs_SAA", "Final_Low", "Final_High"]].copy()
        display_df = display_df.rename(columns={
            "Label": "자산/지역", "SAA": "SAA(%)", "Final": "Final(%)",
            "vs_SAA": "vs SAA(%p)", "Final_Low": "Low(%)", "Final_High": "High(%)",
        })
        for c in ["SAA(%)", "Final(%)", "Low(%)", "High(%)"]:
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
```

- [ ] **Step 2: Verify import**

Run:
```bash
python -c "import taa_portfolio_optimizer; print('Import OK')"
```

- [ ] **Step 3: Full integration test**

Run:
```bash
python -c "
import pandas as pd
from taa_portfolio_optimizer import (
    compute_final, derive_vintage_saa, propagate_to_vintage,
    DEFAULT_REGIONS, DEFAULT_VINTAGES
)

df = pd.DataFrame(DEFAULT_REGIONS)
df.loc[0, 'TAA'] = 'Overweight'  # US equity OW
result = compute_final(df, 0.5, class_signals={'주식': 1, '채권': -1})

print('=== 2050 (Main) ===')
for _, r in result.iterrows():
    print(f\"  {r['자산']} {r['지역']}: Final={r['Final']:.2f} vs_SAA={r['vs_SAA']:+.2f}\")

for v in DEFAULT_VINTAGES:
    saa = derive_vintage_saa(v['Equity'], v['Bond'])
    vr = propagate_to_vintage(result, saa)
    print(f\"\\n=== TDF {v['Vintage']} (Eq={v['Equity']}% Bd={v['Bond']}%) ===\")
    for _, r in vr.iterrows():
        print(f\"  {r['자산']} {r['지역']}: SAA={r['SAA']:.2f} Final={r['Final']:.2f} vs_SAA={r['vs_SAA']:+.2f}\")
    print(f'  Total: {vr[\"Final\"].sum():.2f}%')
"
```
Expected: Each vintage totals ~100%, tilt pattern mirrors 2050 proportionally

- [ ] **Step 4: Commit**

```bash
git add taa_portfolio_optimizer.py
git commit -m "Add vintage results callback"
```

### Task 11: Final smoke test

- [ ] **Step 1: Run the app and verify**

Run:
```bash
timeout 5 python taa_portfolio_optimizer.py 2>&1 || true
```
Expected: App starts without errors (will timeout after 5s, that's fine)

- [ ] **Step 2: Commit all changes**

```bash
git add taa_portfolio_optimizer.py
git commit -m "Add vs SAA display and multi-vintage TDF propagation"
```
