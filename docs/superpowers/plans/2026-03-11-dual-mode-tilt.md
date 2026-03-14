# Dual-Mode Tilt (Peer 기준 / 가중 평균 기준) Implementation Plan

> **Status:** ✅ 구현 완료

**Goal:** 라디오 버튼으로 두 가지 Tilt 계산 모드를 전환할 수 있도록 하고, 가중 평균 모드에서는 SAA 가중치(w) 슬라이더와 Tilt Rate 슬라이더를 제공한다.

**Architecture:** 단일 파일(`taa_portfolio_optimizer.py`)에 `compute_final_weighted` 함수를 추가하고, 라디오 버튼 값에 따라 기존/대안 계산 함수를 분기 호출한다. Parameters 카드에 라디오 버튼을 추가하고, 모드에 따라 슬라이더를 동적으로 표시/숨김한다.

**Tech Stack:** Dash, Pandas, Plotly (기존과 동일)

---

## File Structure

- `taa_portfolio_optimizer.py` — 대시보드 메인 (Dash 앱 + 계산 로직)
- `generate_excel.py` — Excel 파일 생성 스크립트
- `TAA_Dashboard.xlsx` — 생성된 Excel 파일 (두 시트: Peer 기준, 가중 평균 기준)

---

### Task 1: 대안 계산 함수 추가

- [x] **`compute_final_weighted` 함수 작성**

```python
def compute_final_weighted(df, alpha, saa_weight=0.5, tilt_rate=0.20):
    Base_i = w × SAA_i + (1-w) × Peer_i
    Tilt_i = Base_i × tilt_rate
    Adj_i = α × Signal_i × Tilt_i
    Final = normalize(Base + Adj)
```

---

### Task 2: UI — 라디오 버튼 및 모드별 슬라이더 추가

- [x] **Parameters 카드에 라디오 버튼 추가** (`mode-radio`: "Peer 기준" / "가중 평균 기준")
- [x] **모드별 슬라이더 토글** (display none/block 방식)
  - Peer 모드: α, Damping, Min Tilt Rate
  - 가중 평균 모드: α, SAA 가중치(w), Tilt Rate

---

### Task 3: 콜백 분기 — 모드별 계산 로직 연결

- [x] **`update_range_table` / `update_results` 콜백에 모드 분기**
- [x] **Detail Table에 Base 컬럼 추가** (가중 평균 모드)
- [x] **Formula 섹션 모드별 분기**

---

### Task 4: Docstring 및 주석 업데이트

- [x] **파일 docstring 업데이트**

현재 docstring:
```
[Peer 기준] Final_i = normalize( Peer_i + α × Signal_i × Tilt_i )
    Tilt_i = |SAA_i - Peer_i| × d  (gap=0이면 Peer_i × min_tilt_rate)
    d = 1.0 (aligned) / damping (opposed)

[가중 평균 기준] Final_i = normalize( Base_i + α × Signal_i × Tilt_i )
    Base_i = w × SAA_i + (1-w) × Peer_i
    Tilt_i = Base_i × tilt_rate
```

---

### 주요 설계 결정 사항

1. **Peer 모드 Tilt**: min_tilt는 gap=0일 때만 적용 (gap≠0이면 `|Gap|×Damping`)
2. **Range 티어**: Final ≥ 20% → ±7.5%p, ≥ 10% → ±5%p, < 10% → ±2.5%p
3. **슬라이더 토글**: 동적 렌더링 대신 display none/block 방식 채택 (안정성)
4. **Excel 파일**: `generate_excel.py`로 생성, Signal 수식은 VLOOKUP으로 매핑 테이블 참조
