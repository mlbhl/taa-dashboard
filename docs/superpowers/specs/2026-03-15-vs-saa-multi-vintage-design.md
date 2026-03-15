# vs SAA & Multi-Vintage TDF Design

## Overview

Two additions to the TAA Dashboard:
1. **vs SAA display** — show `Final - SAA` alongside existing `vs Peer`
2. **Multi-vintage propagation** — apply 2050's TAA tilts to other TDF vintages (2030, 2040, 2060) that have SAA but no Peer data

## 1. vs SAA Column

Add `vs_SAA = Final - SAA` to both `compute_final` and `compute_final_weighted`. Display in:
- Result Cards (below vs Peer)
- Detail Table (new column after vs Peer)
- Active Bets section (add vs SAA perspective)

## 2. Multi-Vintage Propagation

### Default Vintage SAA

| Vintage | Equity | Bond | Internal weights |
|---------|--------|------|-----------------|
| 2030    | 40%    | 60%  | Same as 2050    |
| 2040    | 55%    | 45%  | Same as 2050    |
| 2050    | 70%    | 30%  | Main result     |
| 2060    | 90%    | 10%  | Same as 2050    |

Assumes only 2 asset classes (주식/채권). If new asset classes are added, the vintage table structure must be updated accordingly.

Internal weight derivation example (2040, equity=55%):
- 미국: 55 × 70/100 = 38.50%
- 유럽: 55 × 15/100 = 8.25%
- 일본: 55 × 5/100 = 2.75%
- 중국: 55 × 3/100 = 1.65%
- 한국: 55 × 5/100 = 2.75%
- 기타: 55 × 2/100 = 1.10%
- 채권 미국: 45 × 70/100 = 31.50%
- 채권 한국: 45 × 30/100 = 13.50%

### Proportional Tilt Formula (Raw-based)

Uses the literal `Raw` column from the active mode's computation (Peer mode or Weighted mode, whichever is currently selected). Raw is the pre-normalization value (Peer + Adj or Base + Adj) and does NOT sum to 100. This is intentional — the tilt_ratio captures the pure TAA intent relative to SAA, and normalization happens separately for each vintage.

```
tilt_ratio_i = (Raw_2050_i - SAA_2050_i) / SAA_2050_i    if SAA_2050_i >= 0.5%
             = (Raw_2050_i - SAA_2050_i)                   if SAA_2050_i < 0.5%  (absolute fallback)

Other_Raw_i  = Other_SAA_i × (1 + tilt_ratio_i)           if ratio-based
             = Other_SAA_i + absolute_tilt                  if absolute fallback
Other_Raw_i  = max(Other_Raw_i, 1.0)                       floor (consistent with 2050)

Other_Final_i = Other_Raw_i / sum(Other_Raw) × 100         normalize
Other_vs_SAA  = Other_Final_i - Other_SAA_i
```

**Why Raw-based**: Raw captures pure TAA intent before normalization. Final-based would propagate cross-asset normalization distortion (e.g., Neutral assets showing negative vs_SAA due to compression from other assets' OW).

### Range Tiers

Applied to each vintage's own Final values (not 2050's):
- Final >= 20% → +/-7.5%p
- Final >= 10% → +/-5.0%p
- Final < 10% → +/-2.5%p

## 3. UI Structure

### Vintage SAA Input
- New card below main results: "Vintage SAA"
- Table with columns: Vintage, Equity(%), Bond(%)
- Default values pre-filled (2030/2040/2060), editable
- Equity + Bond must sum to 100% (validated; if not, show warning and use last valid values)
- Vintage names must be unique
- Row add/delete supported for custom vintages

### Vintage Results
- New card: "Other Vintages"
- Sub-table per vintage showing: Asset, Region, SAA(%), Final(%), vs SAA(%p), Low(%), High(%)
- Compact layout — summary view, not full detail breakdown

## 4. Data Flow

```
Input: 2050 SAA + Peer + TAA signals + Class signals
  → compute_final/weighted (active mode)
  → Raw_2050, Final_2050, vs_SAA_2050

For each vintage V in [2030, 2040, 2060]:
  → Derive V_SAA from (equity%, bond%) × 2050 internal weights
  → tilt_ratio = (Raw_2050 - SAA_2050) / SAA_2050
  → V_Raw = V_SAA × (1 + tilt_ratio)
  → V_Final = normalize(V_Raw)
  → V_vs_SAA = V_Final - V_SAA
  → Apply range tiers to V's own Final values
```

## 5. Implementation Scope

### Functions to modify
- `compute_final` — add vs_SAA column
- `compute_final_weighted` — add vs_SAA column

### Functions to add
- `derive_vintage_saa(equity_pct, bond_pct, base_regions)` — compute vintage SAA from total split + internal weights
- `propagate_to_vintage(raw_2050, saa_2050, vintage_saa)` — apply proportional tilt to a vintage

### UI components to add
- Vintage SAA input table (editable, with defaults)
- Vintage results display (per-vintage summary tables)

### UI components to modify
- Result Cards — add vs SAA line
- Detail Table — add vs SAA column
- Active Bets — optionally show vs SAA
- Callbacks — wire new inputs/outputs
