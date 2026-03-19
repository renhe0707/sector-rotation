"""
可视化模块 v2
Professional charts with high contrast colors, no label overlap, clean design.
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as mticker
import matplotlib.font_manager as fm
import numpy as np
import pandas as pd
import os

# ── Font Setup ──
_cjk_font_path = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
if os.path.exists(_cjk_font_path):
    fm.fontManager.addfont(_cjk_font_path)
    fm._load_fontmanager(try_read_cache=False)
    _cjk = "Noto Sans CJK JP"
else:
    _cjk = "DejaVu Sans"

plt.rcParams.update({
    "figure.facecolor": "white",
    "axes.facecolor": "#FAFAFA",
    "axes.grid": True,
    "grid.alpha": 0.25,
    "grid.linestyle": "-",
    "grid.color": "#E0E0E0",
    "font.size": 11,
    "axes.titlesize": 15,
    "axes.labelsize": 12,
    "legend.fontsize": 10,
    "figure.dpi": 150,
    "savefig.dpi": 150,
    "font.family": [_cjk, "DejaVu Sans", "sans-serif"],
    "axes.unicode_minus": False,
    "axes.spines.top": False,
    "axes.spines.right": False,
})

# ── High-contrast color palette ──
C_STRATEGY = "#1565C0"
C_BENCH    = "#E53935"
C_POS      = "#2E7D32"
C_NEG      = "#C62828"

SECTOR_COLORS = [
    "#1565C0", "#E53935", "#2E7D32", "#F9A825", "#7B1FA2",
    "#00838F", "#EF6C00", "#AD1457", "#37474F", "#558B2F",
    "#4527A0", "#00695C", "#D84315", "#6A1B9A", "#1B5E20",
    "#FF6F00", "#283593", "#880E4F", "#004D40", "#BF360C",
]

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output", "figures")


def _save(fig, name):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    path = os.path.join(OUTPUT_DIR, name)
    fig.savefig(path, bbox_inches="tight", dpi=150, facecolor="white")
    plt.close(fig)
    print(f"  Saved: {name}")


def plot_cumulative_returns(returns_df):
    df = returns_df.copy()
    dates = df["hold_month"].apply(lambda x: x.to_timestamp()).values
    cum_port = np.cumprod(1 + df["portfolio_return"].values)
    cum_bench = np.cumprod(1 + df["benchmark_return"].values)
    start_date = df["hold_month"].iloc[0].to_timestamp() - pd.offsets.MonthEnd(1)
    dates = np.insert(dates, 0, start_date)
    cum_port = np.insert(cum_port, 0, 1.0)
    cum_bench = np.insert(cum_bench, 0, 1.0)

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8), height_ratios=[3, 1],
                                    gridspec_kw={"hspace": 0.3})

    ax1.plot(dates, cum_port, color=C_STRATEGY, linewidth=2.5, label="Strategy 策略")
    ax1.plot(dates, cum_bench, color=C_BENCH, linewidth=2, linestyle="--", label="CSI 300 沪深300")
    ax1.fill_between(dates, cum_port, cum_bench, where=cum_port >= cum_bench, color=C_POS, alpha=0.08)
    ax1.fill_between(dates, cum_port, cum_bench, where=cum_port < cum_bench, color=C_NEG, alpha=0.08)
    ax1.annotate(f"{cum_port[-1]:.2f}", xy=(dates[-1], cum_port[-1]),
                 xytext=(10, 5), textcoords="offset points", fontsize=10, fontweight="bold", color=C_STRATEGY)
    ax1.annotate(f"{cum_bench[-1]:.2f}", xy=(dates[-1], cum_bench[-1]),
                 xytext=(10, -12), textcoords="offset points", fontsize=10, fontweight="bold", color=C_BENCH)
    ax1.set_ylabel("Cumulative NAV 累计净值")
    ax1.set_title("Sector Rotation Strategy vs CSI 300\n行业轮动策略 vs 沪深300", fontsize=16, fontweight="bold")
    ax1.legend(loc="upper left", framealpha=0.9)

    running_max = np.maximum.accumulate(cum_port)
    drawdown = cum_port / running_max - 1
    ax2.fill_between(dates, drawdown, 0, color=C_NEG, alpha=0.3)
    ax2.plot(dates, drawdown, color=C_NEG, linewidth=1)
    ax2.set_ylabel("Drawdown 回撤")
    ax2.yaxis.set_major_formatter(mticker.PercentFormatter(1.0))
    min_idx = np.argmin(drawdown)
    ax2.annotate(f"Max: {drawdown[min_idx]:.1%}", xy=(dates[min_idx], drawdown[min_idx]),
                 xytext=(20, -5), textcoords="offset points", fontsize=9, color=C_NEG, fontweight="bold",
                 arrowprops=dict(arrowstyle="->", color=C_NEG, lw=1))

    for ax in [ax1, ax2]:
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=4))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=30, ha="right", fontsize=9)

    _save(fig, "01_cumulative_returns.png")


def plot_monthly_excess_returns(returns_df):
    df = returns_df.copy()
    excess = df["portfolio_return"].values - df["benchmark_return"].values
    dates = df["hold_month"].apply(lambda x: x.to_timestamp()).values

    fig, ax = plt.subplots(figsize=(14, 5))
    colors = [C_POS if e >= 0 else C_NEG for e in excess]
    bar_width = pd.Timedelta(days=20)
    ax.bar(pd.to_datetime(dates), excess, width=bar_width, color=colors,
           alpha=0.85, edgecolor="white", linewidth=0.5)
    ax.axhline(0, color="#333333", linewidth=0.8)
    ax.set_ylabel("Monthly Excess Return 月超额收益")
    ax.set_title("Monthly Excess Return vs CSI 300\n月度超额收益 vs 沪深300", fontsize=15, fontweight="bold")
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(1.0))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=4))
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=30, ha="right", fontsize=9)

    win_rate = np.mean(excess > 0) * 100
    avg_excess = np.mean(excess) * 100
    ax.text(0.02, 0.95, f"Win Rate 胜率: {win_rate:.0f}%  |  Avg Excess 平均超额: {avg_excess:+.2f}%/mo",
            transform=ax.transAxes, fontsize=10, verticalalignment="top",
            bbox=dict(boxstyle="round,pad=0.4", facecolor="white", edgecolor="#CCCCCC", alpha=0.9))

    _save(fig, "02_monthly_excess_returns.png")


def plot_holdings_heatmap(holdings_df, top_n=10):
    df = holdings_df.copy()
    freq = df["name"].value_counts().head(top_n).index.tolist()
    df_filtered = df[df["name"].isin(freq)]
    pivot = df_filtered.pivot_table(index="name", columns="hold_month",
                                     values="monthly_return", aggfunc="first")
    pivot = pivot.reindex(freq)

    fig, ax = plt.subplots(figsize=(18, 7))
    im = ax.imshow(pivot.values, aspect="auto", cmap="RdYlGn", vmin=-0.12, vmax=0.12)
    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels(pivot.index, fontsize=11, fontweight="bold")

    cols = [str(c) for c in pivot.columns]
    step = max(1, len(cols) // 12)
    ax.set_xticks(range(0, len(cols), step))
    ax.set_xticklabels([cols[i] for i in range(0, len(cols), step)], rotation=35, ha="right", fontsize=9)

    ax.set_title(f"Top {top_n} Industries — Monthly Return Heatmap\n持仓最多的{top_n}个行业 — 月度收益热力图",
                 fontsize=15, fontweight="bold", pad=15)
    cbar = fig.colorbar(im, ax=ax, shrink=0.75, pad=0.02)
    cbar.set_label("Monthly Return 月收益", fontsize=10)
    cbar.ax.yaxis.set_major_formatter(mticker.PercentFormatter(1.0))

    fig.tight_layout()
    _save(fig, "03_holdings_heatmap.png")


def plot_sector_allocation_over_time(holdings_df):
    df = holdings_df.copy()
    weight = df.groupby("hold_month")["code"].transform("count")
    df["weight"] = 1.0 / weight
    pivot = df.pivot_table(index="hold_month", columns="name", values="weight",
                           aggfunc="sum", fill_value=0)
    col_order = pivot.sum().sort_values(ascending=False).index
    pivot = pivot[col_order]

    fig, ax = plt.subplots(figsize=(16, 7))
    n = len(pivot.columns)
    colors = SECTOR_COLORS[:n] if n <= len(SECTOR_COLORS) else (SECTOR_COLORS * 3)[:n]
    pivot.plot.area(ax=ax, stacked=True, alpha=0.85, linewidth=0.3, color=colors)
    ax.set_ylabel("Portfolio Weight 组合权重")
    ax.set_title("Sector Allocation Over Time\n行业配置变迁", fontsize=15, fontweight="bold")
    ax.set_ylim(0, 1.05)
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(1.0))
    ax.legend(bbox_to_anchor=(1.01, 1), loc="upper left", fontsize=8, ncol=2,
              framealpha=0.9, title="Industry 行业", title_fontsize=9)
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=30, ha="right", fontsize=9)
    fig.tight_layout()
    _save(fig, "04_sector_allocation.png")


def plot_performance_summary_table(metrics):
    fig, ax = plt.subplots(figsize=(11, 7))
    ax.axis("off")
    rows = [
        ["Metric 指标", "Strategy 策略", "CSI 300 沪深300", "Excess 超额"],
        ["Total Return 总收益", f"{metrics['total_return']:.2%}", f"{metrics['benchmark_total_return']:.2%}", f"{metrics['excess_total_return']:.2%}"],
        ["Ann. Return 年化收益", f"{metrics['annualized_return']:.2%}", f"{metrics['benchmark_annualized_return']:.2%}", f"{metrics['excess_annualized_return']:.2%}"],
        ["Ann. Vol 年化波动", f"{metrics['annualized_volatility']:.2%}", f"{metrics['benchmark_annualized_volatility']:.2%}", "—"],
        ["Sharpe 夏普", f"{metrics['sharpe_ratio']:.3f}", f"{metrics['benchmark_sharpe']:.3f}", "—"],
        ["Max DD 最大回撤", f"{metrics['max_drawdown']:.2%}", f"{metrics['benchmark_max_drawdown']:.2%}", "—"],
        ["Calmar 卡玛", f"{metrics['calmar_ratio']:.3f}", "—", "—"],
        ["Info Ratio 信息比", "—", "—", f"{metrics['information_ratio']:.3f}"],
        ["Win Rate 月胜率", "—", "—", f"{metrics['monthly_win_rate']:.1%}"],
        ["Period 区间", f"{metrics['n_months']}mo ({metrics['n_years']:.1f}yr)", "", ""],
    ]
    table = ax.table(cellText=rows[1:], colLabels=rows[0], loc="center", cellLoc="center")
    table.auto_set_font_size(False)
    table.set_fontsize(11)
    table.scale(1.2, 1.7)
    for j in range(4):
        table[0, j].set_facecolor(C_STRATEGY)
        table[0, j].set_text_props(color="white", fontweight="bold", fontsize=11)
    for i in range(1, len(rows)):
        bg = "#EEF2F7" if i % 2 == 0 else "white"
        for j in range(4):
            table[i, j].set_facecolor(bg)
            table[i, j].set_edgecolor("#DDDDDD")
    ax.set_title("Performance Summary 绩效汇总", fontsize=16, fontweight="bold", pad=25)
    _save(fig, "05_performance_summary.png")


def plot_annual_returns_comparison(returns_df):
    df = returns_df.copy()
    df["year"] = df["hold_month"].apply(lambda x: x.year)
    annual = df.groupby("year").apply(
        lambda g: pd.Series({
            "strategy": (1 + g["portfolio_return"]).prod() - 1,
            "benchmark": (1 + g["benchmark_return"]).prod() - 1,
        })
    ).reset_index()

    fig, ax = plt.subplots(figsize=(11, 6))
    x = np.arange(len(annual))
    w = 0.32
    bars1 = ax.bar(x - w/2, annual["strategy"], w, label="Strategy 策略",
                   color=C_STRATEGY, alpha=0.9, edgecolor="white", linewidth=0.5)
    bars2 = ax.bar(x + w/2, annual["benchmark"], w, label="CSI 300 沪深300",
                   color=C_BENCH, alpha=0.9, edgecolor="white", linewidth=0.5)
    ax.set_xticks(x)
    ax.set_xticklabels(annual["year"].astype(str), fontsize=12)
    ax.set_ylabel("Annual Return 年度收益")
    ax.set_title("Annual Return Comparison\n年度收益对比", fontsize=15, fontweight="bold")
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(1.0))
    ax.legend(loc="best", framealpha=0.9)
    ax.axhline(0, color="#333333", linewidth=0.8)

    for bar in bars1:
        h = bar.get_height()
        offset = 0.008 if h >= 0 else -0.008
        va = "bottom" if h >= 0 else "top"
        ax.text(bar.get_x() + bar.get_width()/2, h + offset, f"{h:.1%}",
                ha="center", va=va, fontsize=9, fontweight="bold", color=C_STRATEGY)
    for bar in bars2:
        h = bar.get_height()
        offset = 0.008 if h >= 0 else -0.008
        va = "bottom" if h >= 0 else "top"
        ax.text(bar.get_x() + bar.get_width()/2, h + offset, f"{h:.1%}",
                ha="center", va=va, fontsize=9, fontweight="bold", color=C_BENCH)

    _save(fig, "06_annual_returns.png")


def generate_all_charts(returns_df, holdings_df, metrics):
    print("\nGenerating charts (v2)...")
    plot_cumulative_returns(returns_df)
    plot_monthly_excess_returns(returns_df)
    plot_holdings_heatmap(holdings_df)
    plot_sector_allocation_over_time(holdings_df)
    plot_performance_summary_table(metrics)
    plot_annual_returns_comparison(returns_df)
    print("All charts generated!")
