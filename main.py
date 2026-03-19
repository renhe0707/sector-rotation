"""
行业轮动策略 - 主运行脚本
Shenwan Sector Rotation Strategy: Full Pipeline

Usage:
    python main.py              # Run full pipeline (fetch + backtest + charts)
    python main.py --no-fetch   # Skip data fetching, use cached CSV files
"""

import sys
import os
import argparse
import pandas as pd
import numpy as np
import json

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from data_fetcher import (
    get_sw_industry_list,
    fetch_all_industry_daily,
    get_csi300_daily,
    compute_monthly_returns,
    compute_fundamental_scores,
)
from backtest import (
    run_backtest,
    add_benchmark_returns,
    compute_performance_metrics,
    compute_rolling_metrics,
)
from visualizations import generate_all_charts

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")


def fetch_and_save_data():
    """Step 1: 获取数据并缓存到CSV"""
    os.makedirs(DATA_DIR, exist_ok=True)

    print("=" * 60)
    print("STEP 1: Data Fetching")
    print("=" * 60)

    print("\n[1/3] Fetching Shenwan Level-1 industry list...")
    industry_list = get_sw_industry_list()
    industry_list.to_csv(os.path.join(DATA_DIR, "sw_industry_list.csv"), index=False)
    print(f"  Found {len(industry_list)} industries")

    print("\n[2/3] Fetching daily data for all industries (since 2021-01)...")
    daily_data = fetch_all_industry_daily(industry_list, start_date="2021-01-01")
    daily_data.to_csv(os.path.join(DATA_DIR, "sw_industry_daily.csv"), index=False)
    print(f"  Saved {len(daily_data)} rows")

    print("\n[3/3] Fetching CSI 300 daily data...")
    csi300 = get_csi300_daily(start_date="20210101")
    csi300.to_csv(os.path.join(DATA_DIR, "csi300_daily.csv"), index=False)
    print(f"  Saved {len(csi300)} rows")

    return industry_list, daily_data, csi300


def load_cached_data():
    """从缓存CSV加载数据"""
    print("Loading cached data from CSV...")
    industry_list = pd.read_csv(os.path.join(DATA_DIR, "sw_industry_list.csv"))
    daily_data = pd.read_csv(os.path.join(DATA_DIR, "sw_industry_daily.csv"), parse_dates=["date"])
    csi300 = pd.read_csv(os.path.join(DATA_DIR, "csi300_daily.csv"), parse_dates=["date"])
    return industry_list, daily_data, csi300


def run_strategy(daily_data, csi300, top_n=5, lookback=12, start_month="2022-06"):
    """Step 2 & 3: 构建因子 + 回测"""
    print("\n" + "=" * 60)
    print("STEP 2: Factor Construction & Scoring")
    print("=" * 60)

    print(f"\n  Computing factor scores (lookback={lookback} months)...")
    scores = compute_fundamental_scores(daily_data, lookback_months=lookback)
    print(f"  Generated {len(scores)} industry-month score records")

    print("\n  Computing monthly returns from daily data...")
    monthly_returns = compute_monthly_returns(daily_data)
    print(f"  Generated {len(monthly_returns)} monthly return records")

    print("\n" + "=" * 60)
    print(f"STEP 3: Backtest (top {top_n} industries, start={start_month})")
    print("=" * 60)

    portfolio_df, holdings_df = run_backtest(
        scores, monthly_returns, top_n=top_n, start_month=start_month
    )
    print(f"\n  Portfolio: {len(portfolio_df)} months of returns")
    print(f"  Holdings:  {len(holdings_df)} total position records")

    # Add benchmark
    returns_df = add_benchmark_returns(portfolio_df, csi300)
    returns_df = returns_df.dropna(subset=["benchmark_return"])

    # Performance metrics
    metrics = compute_performance_metrics(returns_df)

    return scores, monthly_returns, returns_df, holdings_df, metrics


def print_results(metrics):
    """打印回测结果"""
    print("\n" + "=" * 60)
    print("PERFORMANCE RESULTS")
    print("=" * 60)

    print(f"\n{'Metric':<30} {'Strategy':>12} {'CSI 300':>12} {'Excess':>12}")
    print("-" * 70)
    print(f"{'Total Return':<30} {metrics['total_return']:>11.2%} {metrics['benchmark_total_return']:>11.2%} {metrics['excess_total_return']:>11.2%}")
    print(f"{'Annualized Return':<30} {metrics['annualized_return']:>11.2%} {metrics['benchmark_annualized_return']:>11.2%} {metrics['excess_annualized_return']:>11.2%}")
    print(f"{'Annualized Volatility':<30} {metrics['annualized_volatility']:>11.2%} {metrics['benchmark_annualized_volatility']:>11.2%} {'':>12}")
    print(f"{'Sharpe Ratio':<30} {metrics['sharpe_ratio']:>11.3f} {metrics['benchmark_sharpe']:>11.3f} {'':>12}")
    print(f"{'Max Drawdown':<30} {metrics['max_drawdown']:>11.2%} {metrics['benchmark_max_drawdown']:>11.2%} {'':>12}")
    print(f"{'Calmar Ratio':<30} {metrics['calmar_ratio']:>11.3f} {'':>12} {'':>12}")
    print(f"{'Information Ratio':<30} {'':>12} {'':>12} {metrics['information_ratio']:>11.3f}")
    print(f"{'Monthly Win Rate':<30} {'':>12} {'':>12} {metrics['monthly_win_rate']:>11.1%}")
    print(f"{'Avg Monthly Excess':<30} {'':>12} {'':>12} {metrics['avg_monthly_excess']:>11.2%}")
    print(f"\n  Backtest: {metrics['n_months']} months ({metrics['n_years']:.1f} years)")


def save_results(scores, returns_df, holdings_df, metrics):
    """保存回测结果"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    scores.to_csv(os.path.join(OUTPUT_DIR, "factor_scores.csv"), index=False)
    returns_df.to_csv(os.path.join(OUTPUT_DIR, "portfolio_returns.csv"), index=False)
    holdings_df.to_csv(os.path.join(OUTPUT_DIR, "holdings_history.csv"), index=False)

    # Convert metrics for JSON
    metrics_json = {k: float(v) if isinstance(v, (np.floating, np.integer)) else v
                    for k, v in metrics.items()}
    with open(os.path.join(OUTPUT_DIR, "performance_metrics.json"), "w") as f:
        json.dump(metrics_json, f, indent=2)

    print(f"\n  Results saved to {OUTPUT_DIR}/")


def main():
    parser = argparse.ArgumentParser(description="Shenwan Sector Rotation Backtest")
    parser.add_argument("--no-fetch", action="store_true", help="Skip data fetching, use cached CSV")
    parser.add_argument("--top-n", type=int, default=5, help="Number of industries to hold (default: 5)")
    parser.add_argument("--lookback", type=int, default=12, help="Factor lookback months (default: 12)")
    parser.add_argument("--start", type=str, default="2022-06", help="Backtest start month (default: 2022-06)")
    args = parser.parse_args()

    # Step 1: Data
    if args.no_fetch:
        industry_list, daily_data, csi300 = load_cached_data()
    else:
        industry_list, daily_data, csi300 = fetch_and_save_data()

    # Step 2 & 3: Strategy + Backtest
    scores, monthly_returns, returns_df, holdings_df, metrics = run_strategy(
        daily_data, csi300, top_n=args.top_n, lookback=args.lookback, start_month=args.start
    )

    # Step 4: Results
    print_results(metrics)
    save_results(scores, returns_df, holdings_df, metrics)

    # Step 5: Charts
    generate_all_charts(returns_df, holdings_df, metrics)

    print("\n" + "=" * 60)
    print("DONE! Check output/ for results and figures.")
    print("=" * 60)


if __name__ == "__main__":
    main()
