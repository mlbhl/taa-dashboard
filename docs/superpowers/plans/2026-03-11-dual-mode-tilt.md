# Dual-Mode Tilt (Peer 기준 / 가중 평균 기준) Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 라디오 버튼으로 두 가지 Tilt 계산 모드를 전환할 수 있도록 하고, 가중 평균 모드에서는 SAA 가중치(w) 슬라이더와 Tilt Rate 슬라이더를 제공한다.

**Architecture:** 단일 파일(`taa_portfolio_optimizer.py`)에 `compute_final_weighted` 함수를 추가하고, 라디오 버튼 값에 따라 기존/대안 계산 함수를 분기 호출한다. Parameters 카드에 라디오 버튼을 추가하고, 모드에 따라 슬라이더를 동적으로 표시/숨김한다.

**Tech Stack:** Dash, Pandas, Plotly (기존과 동일)

---

## File Structure

- Modify: `taa_portfolio_optimizer.py` — 유일한 소스 파일, 모든 변경이 여기서 이루어짐

---

### Task 1: 대안 계산 함수 추가

**Files:**
- Modify: `taa_portfolio_optimizer.py:41-70` (기존 `compute_final` 아래에 새 함수 추가)

- [ ] **Step 1: `compute_final_weighted` 함수 작성**

`compute_final` 함수 바로 아래(line 71)에 새 함수를 추가한다:

```python
def compute_final_weighted(df: pd.DataFrame, alpha: float, saa_weight: float = 0.5, tilt_rate: float = 0.20) -> pd.DataFrame:
    """가중 평균 기준 Final 비중 계산

    Base_i = w × SAA_i + (1-w) × Peer_i
    Tilt_i = Base_i × tilt_rate
    Adj_i = α × Signal_i × Tilt_i
    Final = normalize(Base + Adj)
    """
    df = df.copy()
    df["Signal"] = df["TAA"].map(TAA_MAP).fillna(0).astype(float)

    df["Base"] = saa_weight * df["SAA"] + (1 - saa_weight) * df["Peer"]
    df["Tilt"] = df["Base"] * tilt_rate

    df["Adj"] = alpha * df["Signal"] * df["Tilt"]
    df["Raw"] = df["Base"] + df["Adj"]
    df["Raw"] = df["Raw"].clip(lower=1.0)

    total = df["Raw"].sum()
    df["Final"] = (df["Raw"] / total * 100).round(2)
    df["vs_Peer"] = (df["Final"] - df["Peer"]).round(2)

    half_w = df["Final"].apply(lambda v: 5.0 if v >= 10 else 2.5)
    df["Final_Low"] = (df["Final"] - half_w).clip(lower=0.0).round(2)
    df["Final_High"] = (df["Final"] + half_w).round(2)

    return df
```

- [ ] **Step 2: 검증 — 문법 체크**

Run: `python -c "import ast; ast.parse(open('taa_portfolio_optimizer.py').read()); print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add taa_portfolio_optimizer.py
git commit -m "Add compute_final_weighted function"
```

---

### Task 2: UI — 라디오 버튼 및 모드별 슬라이더 추가

**Files:**
- Modify: `taa_portfolio_optimizer.py:215-271` (Parameters 카드 레이아웃)

- [ ] **Step 1: Parameters 카드 리팩토링**

Parameters 카드(line 216~271)를 다음과 같이 교체한다:
- 라디오 버튼 (`dcc.RadioItems`, id=`mode-radio`) 추가: "Peer 기준" / "가중 평균 기준"
- 슬라이더 영역을 `html.Div(id="sliders-container")`로 감싸서 콜백으로 동적 렌더링

```python
# ── Parameters ──
html.Div(style=card_style, children=[
    html.Div("Parameters", style=label_style),
    # 모드 선택 라디오 버튼
    html.Div(style={"marginBottom": "20px"}, children=[
        dcc.RadioItems(
            id="mode-radio",
            options=[
                {"label": " Peer 기준 (비대칭 Tilt)", "value": "peer"},
                {"label": " 가중 평균 기준 (Base 비례 Tilt)", "value": "weighted"},
            ],
            value="peer",
            inline=True,
            style={"fontSize": "14px", "fontWeight": "600"},
            inputStyle={"marginRight": "6px"},
            labelStyle={"marginRight": "24px", "cursor": "pointer"},
        ),
    ]),
    # 슬라이더 영역 (모드에 따라 동적 렌더링)
    html.Div(id="sliders-container"),
]),
```

- [ ] **Step 2: 슬라이더 동적 렌더링 콜백 추가**

모드에 따라 다른 슬라이더 세트를 렌더링하는 콜백을 추가한다.
- `mode == "peer"`: α, Damping, Min Tilt Rate (기존 3개, 1×3 그리드)
- `mode == "weighted"`: α, SAA 가중치(w), Tilt Rate (3개, 1×3 그리드)

**Peer 모드 슬라이더:** 기존 α, Damping, Min Tilt Rate 슬라이더 코드를 그대로 사용. 단, id에 접미사 없이 기존 id 유지: `alpha-slider`, `damping-slider`, `mintilt-slider`.

**가중 평균 모드 슬라이더:**
- α 슬라이더: id=`alpha-slider` (동일)
- SAA 가중치(w): id=`w-slider`, min=0, max=1, step=0.05, value=0.5, marks={0: "0 (Peer)", 0.5: "0.5", 1: "1 (SAA)"}
- Tilt Rate: id=`tiltrate-slider`, min=0, max=0.5, step=0.05, value=0.20, marks={0: "0%", 0.2: "20%", 0.5: "50%"}

**주의:** Dash에서 동적으로 id가 다른 컴포넌트를 렌더링하면, 해당 id를 참조하는 콜백이 없는 경우 에러가 발생할 수 있다. `suppress_callback_exceptions=True`가 이미 설정되어 있으므로 괜찮다.

**대안 접근 (더 안정적):** 동적 렌더링 대신, 모든 슬라이더를 처음부터 레이아웃에 배치하고 `style={"display": "none"/"block"}`으로 토글한다.

이 방식을 사용한다:
- `peer-sliders` div: Damping, Min Tilt Rate 슬라이더 (Peer 모드에서만 표시)
- `weighted-sliders` div: SAA 가중치(w), Tilt Rate 슬라이더 (가중 평균 모드에서만 표시)
- α 슬라이더는 공통이므로 항상 표시

레이아웃 구조:
```
Parameters 카드
├── 라디오 버튼
├── 2×2 그리드
│   ├── α 슬라이더 (공통, 항상 표시)
│   ├── peer-sliders div (Peer 모드: Damping)
│   │   또는 weighted-sliders div (가중 평균 모드: SAA 가중치 w)
│   ├── peer-sliders div (Peer 모드: Min Tilt Rate)
│   │   또는 weighted-sliders div (가중 평균 모드: Tilt Rate)
│   └── (빈칸 또는 추가 파라미터)
```

실제 구현: 모든 슬라이더를 배치하되, 모드에 따라 display 토글하는 콜백 작성.

```python
@app.callback(
    [Output("peer-sliders", "style"), Output("weighted-sliders", "style")],
    Input("mode-radio", "value"),
)
def toggle_sliders(mode):
    if mode == "peer":
        return {"display": "contents"}, {"display": "none"}
    else:
        return {"display": "none"}, {"display": "contents"}
```

- [ ] **Step 3: 파라미터 표시 콜백 추가**

기존 `update_damping_display`, `update_mintilt_display` 콜백은 유지하고, 새 슬라이더용 콜백 추가:

```python
@app.callback(Output("w-display", "children"), Input("w-slider", "value"))
def update_w_display(val):
    return f"{val:.2f}"

@app.callback(Output("tiltrate-display", "children"), Input("tiltrate-slider", "value"))
def update_tiltrate_display(val):
    return f"{val:.0%}"
```

- [ ] **Step 4: 검증**

Run: `python -c "import ast; ast.parse(open('taa_portfolio_optimizer.py').read()); print('OK')"`
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add taa_portfolio_optimizer.py
git commit -m "Add mode radio button and conditional sliders"
```

---

### Task 3: 콜백 분기 — 모드별 계산 로직 연결

**Files:**
- Modify: `taa_portfolio_optimizer.py:428-487` (`update_range_table` 콜백)
- Modify: `taa_portfolio_optimizer.py:506-727` (`update_results` 콜백)

- [ ] **Step 1: `update_range_table` 콜백에 모드 분기 추가**

`mode-radio`, `w-slider`, `tiltrate-slider`를 Input으로 추가하고, 모드에 따라 `compute_final` 또는 `compute_final_weighted` 호출:

```python
@app.callback(
    [Output("range-table-container", "children"),
     Output("confirmed-range-store", "data"),
     Output("range-status", "children")],
    [Input("region-table", "data"),
     Input("alpha-slider", "value"),
     Input("damping-slider", "value"),
     Input("mintilt-slider", "value"),
     Input("mode-radio", "value"),
     Input("w-slider", "value"),
     Input("tiltrate-slider", "value")],
)
def update_range_table(rows, alpha, damping_opposed, min_tilt_rate, mode, saa_weight, tilt_rate):
    ...
    if mode == "peer":
        result = compute_final(df, alpha, damping_opposed, min_tilt_rate)
    else:
        result = compute_final_weighted(df, alpha, saa_weight, tilt_rate)
    ...
```

- [ ] **Step 2: `update_results` 콜백에 모드 분기 추가**

동일하게 `mode-radio`, `w-slider`, `tiltrate-slider`를 Input으로 추가하고 분기:

```python
@app.callback(
    [Output("result-cards", "children"),
     Output("comparison-chart", "figure"),
     Output("active-bets", "children"),
     Output("result-table", "children"),
     Output("formula-text", "children")],
    [Input("region-table", "data"),
     Input("alpha-slider", "value"),
     Input("damping-slider", "value"),
     Input("mintilt-slider", "value"),
     Input("confirmed-range-store", "data"),
     Input("mode-radio", "value"),
     Input("w-slider", "value"),
     Input("tiltrate-slider", "value")],
)
def update_results(rows, alpha, damping_opposed, min_tilt_rate, confirmed_range, mode, saa_weight, tilt_rate):
    ...
    if mode == "peer":
        result = compute_final(df, alpha, damping_opposed, min_tilt_rate)
    else:
        result = compute_final_weighted(df, alpha, saa_weight, tilt_rate)
    ...
```

- [ ] **Step 3: Detail Table에 Base 컬럼 추가 (가중 평균 모드)**

가중 평균 모드에서는 `Base` 컬럼이 결과에 포함되므로, detail_cols 구성 시 모드별 분기:

```python
if mode == "weighted" and "Base" in result.columns:
    # Base 컬럼 포함, SAA-Peer gap 관련 컬럼 대신 Base 표시
    detail_cols = ["자산", "지역", "SAA", "Peer", "Base", "TAA", "Signal", "Tilt", "Adj", "Raw", "Final", "Final_Low", "Final_High", "vs_Peer"]
    rename["Base"] = "Base(%)"
```

- [ ] **Step 4: Formula 섹션 모드별 분기**

```python
if mode == "peer":
    formula = [
        # 기존 Peer 모드 수식 (현재 코드 그대로)
    ]
else:
    formula = [
        html.Div([html.Span("1. ", style={"color": ACCENT}), "Signal_i = TAA 의견의 수치 변환 (SOW=+2, OW=+1, N=0, UW=−1, SUW=−2)"]),
        html.Div([html.Span("2. ", style={"color": ACCENT}), f"Base_i = {saa_weight:.2f} × SAA_i + {1-saa_weight:.2f} × Peer_i"]),
        html.Div([html.Span("3. ", style={"color": ACCENT}), f"Tilt_i = Base_i × {tilt_rate:.0%}"]),
        html.Div([html.Span("4. ", style={"color": ACCENT}), "Adj_i = α × Signal_i × Tilt_i"]),
        html.Div([html.Span("5. ", style={"color": ACCENT}), "Raw_i = max( Base_i + Adj_i,  1.0 )"]),
        html.Div([html.Span("6. ", style={"color": ACCENT}), "Final_i = Raw_i / Σ Raw_j × 100"]),
        html.Div([html.Span("7. ", style={"color": ACCENT}), "Range: Final ≥ 10% → ±5%p,  Final < 10% → ±2.5%p  (수기 조정 가능)"]),
        html.Div(
            f"α = {alpha:.2f} | SAA Weight = {saa_weight:.2f} | Tilt Rate = {tilt_rate:.0%} | Floor = 1.0%",
            style={"marginTop": "8px", "fontSize": "13px", "color": "#94a3b8"},
        ),
    ]
```

- [ ] **Step 5: 검증**

Run: `python -c "import ast; ast.parse(open('taa_portfolio_optimizer.py').read()); print('OK')"`
Expected: `OK`

- [ ] **Step 6: Commit**

```bash
git add taa_portfolio_optimizer.py
git commit -m "Wire mode-based calculation and formula display"
```

---

### Task 4: Docstring 및 주석 업데이트

**Files:**
- Modify: `taa_portfolio_optimizer.py:1-15` (파일 상단 docstring)

- [ ] **Step 1: 파일 docstring 업데이트**

```python
"""
TAA Portfolio Optimizer Dashboard
==================================
두 가지 모드로 Final 비중을 산출:

[Peer 기준] Final_i = normalize( Peer_i + α × Signal_i × Tilt_i )
    Tilt_i = |SAA_i - Peer_i| × d  (gap=0이면 Peer_i × min_tilt_rate)

[가중 평균 기준] Final_i = normalize( Base_i + α × Signal_i × Tilt_i )
    Base_i = w × SAA_i + (1-w) × Peer_i
    Tilt_i = Base_i × tilt_rate

Requirements:
    pip install dash pandas plotly

Run:
    python taa_portfolio_optimizer.py
"""
```

- [ ] **Step 2: Commit**

```bash
git add taa_portfolio_optimizer.py
git commit -m "Update docstring for dual mode"
```
