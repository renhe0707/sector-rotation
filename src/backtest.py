"""
回测引擎模块
Implements monthly sector rotation strategy and performance analytics.
"""

import pandas as pd
import numpy as np
from typing import Tuple


def run_backtest(
    scores_df: pd.DataFrame,
    monthly_returns: pd.DataFrame,
    top_n: int = 5,
    start_month: str = "2022-06",
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    执行行业轮动策略回测
    
    策略逻辑：
    - 每月末根据综合评分排名，选择前top_n个行业
    - 等权持有一个月，下月末再调仓
    - T月末评分 → T+1月持有
    
    Parameters
    ----------
    scores_df : DataFrame with columns [code, name, month, composite_score]
    monthly_returns : DataFrame with columns [code, name, month, monthly_return]
    top_n : int, number of industries to hold
    start_month : str, backtest start month
    
    Returns
    -------
    portfolio_returns : DataFrame with monthly portfolio returns
    holdings_history : DataFrame with monthly holdings detail
    """
    scores = scores_df.copy()
    returns = monthly_returns.copy()

    # Ensure month is Period type
    if not isinstance(scores["month"].iloc[0], pd.Period):
        scores["month"] = pd.PeriodIndex(scores["month"], freq="M")
    if not isinstance(returns["month"].iloc[0], pd.Period):
        returns["month"] = pd.PeriodIndex(returns["month"], freq="M")

    start_period = pd.Period(start_month, freq="M")
    available_months = sorted(scores[scores["month"] >= start_period]["month"].unique())

    portfolio_records = []
    holdings_records = []

    for i, signal_month in enumerate(available_months[:-1]):
        hold_month = available_months[i + 1]

        # 1) Get top_n industries by composite score at signal month
        month_scores = scores[scores["month"] == signal_month].copy()
        if len(month_scores) < top_n:
            continue
        top_industries = month_scores.nlargest(top_n, "composite_score")

        # 2) Get returns for hold month
        hold_returns = returns[returns["month"] == hold_month]

        # 3) Calculate equal-weight portfolio return
        selected_codes = top_industries["code"].tolist()
        selected_returns = hold_returns[hold_returns["code"].isin(selected_codes)]

        if len(selected_returns) == 0:
            continue

        port_return = selected_returns["monthly_return"].mean()

        portfolio_records.append({
            "signal_month": signal_month,
            "hold_month": hold_month,
            "portfolio_return": port_return,
            "num_holdings": len(selected_returns),
        })

        for _, row in selected_returns.iterrows():
            sc = month_scores[month_scores["code"] == row["code"]]
            holdings_records.append({
                "signal_month": signal_month,
                "hold_month": hold_month,
                "code": row["code"],
                "name": row["name"],
                "monthly_return": row["monthly_return"],
                "composite_score": sc["composite_score"].values[0] if len(sc) > 0 else np.nan,
            })

    portfolio_df = pd.DataFrame(portfolio_records)
    holdings_df = pd.DataFrame(holdings_records)

    return portfolio_df, holdings_df


def add_benchmark_returns(
    portfolio_df: pd.DataFrame,
    csi300_daily: pd.DataFrame,
) -> pd.DataFrame:
    """将沪深300基准收益率添加到回测结果中"""
    bench = csi300_daily.copy()
    bench["month"] = bench["date"].dt.to_period("M")

    # Monthly returns from daily close
    month_end = bench.groupby("month").last().reset_index()
    month_end = month_end.sort_values("month")
    month_end["benchmark_return"] = month_end["close"].pct_change()

    result = portfolio_df.merge(
        month_end[["month", "benchmark_return"]],
        left_on="hold_month",
        right_on="month",
        how="left",
    )
    if "month" in result.columns:
        result = result.drop(columns=["month"])

    return result


def compute_performance_metrics(returns_df: pd.DataFrame) -> dict:
    """
    计算策略绩效指标
    
    Returns dict with:
    - total_return, annualized_return, annualized_vol, sharpe_ratio
    - max_drawdown, calmar_ratio
    - benchmark versions of the same
    - excess_return, information_ratio
    - win_rate, avg_monthly_excess
    """
    port = returns_df["portfolio_return"].values
    bench = returns_df["benchmark_return"].values
    n_months = len(port)
    n_years = n_months / 12

    # --- Strategy ---
    cum_port = np.cumprod(1 + port)
    total_return = cum_port[-1] - 1
    ann_return = (1 + total_return) ** (1 / n_years) - 1
    ann_vol = np.std(port, ddof=1) * np.sqrt(12)
    sharpe = ann_return / ann_vol if ann_vol > 0 else 0

    # Max drawdown
    running_max = np.maximum.accumulate(cum_port)
    drawdowns = cum_port / running_max - 1
    max_dd = drawdowns.min()
    calmar = ann_return / abs(max_dd) if max_dd != 0 else 0

    # --- Benchmark ---
    cum_bench = np.cumprod(1 + bench)
    bench_total = cum_bench[-1] - 1
    bench_ann = (1 + bench_total) ** (1 / n_years) - 1
    bench_vol = np.std(bench, ddof=1) * np.sqrt(12)
    bench_sharpe = bench_ann / bench_vol if bench_vol > 0 else 0

    bench_running_max = np.maximum.accumulate(cum_bench)
    bench_dd = (cum_bench / bench_running_max - 1).min()

    # --- Excess ---
    excess = port - bench
    excess_total = total_return - bench_total
    excess_ann = ann_return - bench_ann
    tracking_error = np.std(excess, ddof=1) * np.sqrt(12)
    info_ratio = excess_ann / tracking_error if tracking_error > 0 else 0

    win_rate = np.mean(excess > 0)
    avg_monthly_excess = np.mean(excess)

    return {
        # Strategy
        "total_return": total_return,
        "annualized_return": ann_return,
        "annualized_volatility": ann_vol,
        "sharpe_ratio": sharpe,
        "max_drawdown": max_dd,
        "calmar_ratio": calmar,
        # Benchmark
        "benchmark_total_return": bench_total,
        "benchmark_annualized_return": bench_ann,
        "benchmark_annualized_volatility": bench_vol,
        "benchmark_sharpe": bench_sharpe,
        "benchmark_max_drawdown": bench_dd,
        # Excess
        "excess_total_return": excess_total,
        "excess_annualized_return": excess_ann,
        "tracking_error": tracking_error,
        "information_ratio": info_ratio,
        "monthly_win_rate": win_rate,
        "avg_monthly_excess": avg_monthly_excess,
        # Meta
        "n_months": n_months,
        "n_years": n_years,
    }


def compute_rolling_metrics(
    returns_df: pd.DataFrame, window: int = 6
) -> pd.DataFrame:
    """计算滚动绩效指标"""
    df = returns_df.copy()
    df["excess_return"] = df["portfolio_return"] - df["benchmark_return"]

    df["rolling_port_return"] = (
        (1 + df["portfolio_return"]).rolling(window).apply(np.prod, raw=True) - 1
    )
    df["rolling_bench_return"] = (
        (1 + df["benchmark_return"]).rolling(window).apply(np.prod, raw=True) - 1
    )
    df["rolling_excess"] = df["rolling_port_return"] - df["rolling_bench_return"]
    df["rolling_sharpe"] = (
        df["portfolio_return"].rolling(window).mean()
        / df["portfolio_return"].rolling(window).std()
        * np.sqrt(12)
    )

    return df
