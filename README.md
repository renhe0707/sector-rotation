# Shenwan Sector Rotation Strategy | 申万行业轮动策略

A quantitative sector rotation strategy based on Shenwan Level-1 industry indices for the Chinese A-share market. The strategy selects top-performing sectors monthly using a multi-factor scoring system and benchmarks against the CSI 300 index.

## Strategy Overview

### Investment Logic

The strategy exploits sector-level **momentum** and **risk-adjusted return persistence** across Shenwan's 31 Level-1 industry classifications. Each month-end, industries are scored on three dimensions and the top 5 are held with equal weight for the following month.

### Factor Construction

| Factor | Description | Intuition |
|--------|-------------|-----------|
| **Momentum** | 12-month cumulative return | Industries with sustained upward trends |
| **Risk-Adjusted Momentum** | Return / Annualized Volatility | Favors high-return, low-volatility sectors |
| **Turnover Trend** | Recent 3-month avg volume / Prior period avg | Captures increasing institutional interest |

Each factor is cross-sectionally ranked into percentiles (0–1) each month. The **composite score** is the equal-weighted average of the three factor ranks.

### Execution

- **Universe**: 31 Shenwan Level-1 industry indices
- **Rebalance**: Monthly (end of month)
- **Signal Lag**: T-month score → T+1 month holding (no look-ahead bias)
- **Position Sizing**: Equal weight across top 5 industries
- **Benchmark**: CSI 300 Index

## Results

### Performance Summary (Jun 2022 – Mar 2026)

| Metric | Strategy | CSI 300 | Excess |
|--------|----------|---------|--------|
| Total Return | -3.22% | 3.86% | -7.08% |
| Annualized Return | -0.87% | 1.02% | -1.88% |
| Annualized Volatility | 19.07% | 18.16% | - |
| Sharpe Ratio | -0.046 | 0.056 | - |
| Max Drawdown | -38.27% | -22.90% | - |
| Information Ratio | - | - | -0.145 |
| Monthly Win Rate | - | - | 55.6% |

> **Note**: The backtest period (2022–2026) includes the severe A-share bear market (2022–2024 H1) followed by a sharp recovery. The strategy significantly outperformed in 2025 (+30.2% vs +17.7%) but underperformed during the drawdown phase due to momentum's inherent lag in trend reversals.

### Key Charts

#### Cumulative NAV & Drawdown
![Cumulative Returns](output/figures/01_cumulative_returns.png)

#### Monthly Excess Return vs CSI 300
![Monthly Excess](output/figures/02_monthly_excess_returns.png)

#### Top 10 Held Industries – Return Heatmap
![Holdings Heatmap](output/figures/03_holdings_heatmap.png)

#### Sector Allocation Over Time
![Sector Allocation](output/figures/04_sector_allocation.png)

#### Annual Return Comparison
![Annual Returns](output/figures/06_annual_returns.png)

## Project Structure

```
sector-rotation/
├── main.py                     # Main pipeline runner
├── src/
│   ├── data_fetcher.py         # AKShare data acquisition & factor computation
│   ├── backtest.py             # Backtest engine & performance analytics
│   └── visualizations.py       # Professional chart generation
├── data/                       # Cached CSV data (auto-generated)
│   ├── sw_industry_list.csv
│   ├── sw_industry_daily.csv
│   └── csi300_daily.csv
├── output/                     # Results & figures
│   ├── portfolio_returns.csv
│   ├── holdings_history.csv
│   ├── factor_scores.csv
│   ├── performance_metrics.json
│   └── figures/
│       ├── 01_cumulative_returns.png
│       ├── 02_monthly_excess_returns.png
│       ├── 03_holdings_heatmap.png
│       ├── 04_sector_allocation.png
│       ├── 05_performance_summary.png
│       └── 06_annual_returns.png
├── requirements.txt
└── README.md
```

## Quick Start

### Installation

```bash
git clone https://github.com/YOUR_USERNAME/sector-rotation.git
cd sector-rotation
pip install -r requirements.txt
```

### Run Full Pipeline

```bash
# Fetch data from AKShare + run backtest + generate charts
python main.py

# Use cached data (skip API calls)
python main.py --no-fetch
```

### Custom Parameters

```bash
# Hold top 3 industries with 6-month lookback, starting from 2023
python main.py --top-n 3 --lookback 6 --start 2023-01
```

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--no-fetch` | False | Skip data fetching, use cached CSV |
| `--top-n` | 5 | Number of industries to hold |
| `--lookback` | 12 | Factor lookback window (months) |
| `--start` | 2022-06 | Backtest start month |

## Data Sources

- **Industry Indices**: [Shenwan Research](https://www.swsresearch.com/) via AKShare
- **Benchmark**: CSI 300 Index via China Securities Index Co., Ltd.

All data is fetched in real-time via the [AKShare](https://github.com/akfamily/akshare) open-source library (no API key required).

## Technical Notes

### Why Momentum-Based (not Fundamental)?

AKShare's free API provides reliable historical **price/volume data** for Shenwan indices but does not offer time-series fundamental data (historical PE/ROE/revenue by industry-month). As a result, the factor model uses **price momentum, risk-adjusted momentum, and turnover trend** as proxy signals for sector rotation. These are well-documented factor premia in Chinese equity markets.

For a production strategy, incorporating fundamental factors (ROE, revenue growth, PE percentile) from Wind or Bloomberg would significantly enhance signal quality.

### Look-Ahead Bias Prevention

- Scoring uses only information available at the signal date (T-month data → T+1 month holding)
- Monthly returns are computed from daily close prices to avoid stale month-end pricing
- No survivorship bias: all 31 Shenwan industries are included throughout the backtest period

## Future Improvements

- [ ] Add fundamental factors (PE/PB/ROE) via paid data sources
- [ ] Implement transaction cost modeling (estimated 10-20bps per rebalance)
- [ ] Test alternative lookback windows and top-N sensitivity
- [ ] Add sector-neutral constraints
- [ ] Implement walk-forward optimization

## License

MIT

## Author

Robert Ren — Purdue University, B.S. Applied Statistics
