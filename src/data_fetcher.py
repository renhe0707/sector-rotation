"""
数据获取模块
Fetches Shenwan Level-1 industry index data and CSI 300 benchmark data via AKShare.
"""

import akshare as ak
import pandas as pd
import numpy as np
import os
import time

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")


def get_sw_industry_list() -> pd.DataFrame:
    """获取申万一级行业列表及当前估值数据"""
    df = ak.sw_index_first_info()
    df.columns = [
        "code", "name", "num_stocks", "pe_static", "pe_ttm", "pb", "div_yield"
    ]
    df["code"] = df["code"].str.replace(".SI", "", regex=False)
    return df


def get_sw_industry_monthly(code: str) -> pd.DataFrame:
    """获取单个申万行业指数月线数据"""
    df = ak.index_hist_sw(symbol=code, period="month")
    df.columns = ["code", "date", "close", "open", "high", "low", "volume", "amount"]
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)
    return df


def get_sw_industry_daily(code: str) -> pd.DataFrame:
    """获取单个申万行业指数日线数据"""
    df = ak.index_hist_sw(symbol=code, period="day")
    df.columns = ["code", "date", "close", "open", "high", "low", "volume", "amount"]
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)
    return df


def get_csi300_daily(start_date: str = "20220101", end_date: str = "20260318") -> pd.DataFrame:
    """获取沪深300指数日线数据"""
    df = ak.stock_zh_index_hist_csindex(
        symbol="000300", start_date=start_date, end_date=end_date
    )
    df = df.rename(columns={
        "日期": "date", "收盘": "close", "开盘": "open",
        "最高": "high", "最低": "low", "成交量": "volume",
        "成交金额": "amount", "滚动市盈率": "pe_ttm"
    })
    df["date"] = pd.to_datetime(df["date"])
    df = df[["date", "close", "open", "high", "low", "volume", "amount", "pe_ttm"]]
    df = df.sort_values("date").reset_index(drop=True)
    return df


def fetch_all_industry_monthly(industry_list: pd.DataFrame, start_date: str = "2022-01-01") -> pd.DataFrame:
    """批量获取所有申万一级行业月线数据"""
    all_data = []
    for _, row in industry_list.iterrows():
        code, name = row["code"], row["name"]
        try:
            df = get_sw_industry_monthly(code)
            df["name"] = name
            df = df[df["date"] >= start_date]
            all_data.append(df)
            time.sleep(0.3)
        except Exception as e:
            print(f"  [WARN] Failed to fetch {name} ({code}): {e}")
    result = pd.concat(all_data, ignore_index=True)
    return result


def fetch_all_industry_daily(industry_list: pd.DataFrame, start_date: str = "2022-01-01") -> pd.DataFrame:
    """批量获取所有申万一级行业日线数据"""
    all_data = []
    for _, row in industry_list.iterrows():
        code, name = row["code"], row["name"]
        try:
            df = get_sw_industry_daily(code)
            df["name"] = name
            df = df[df["date"] >= start_date]
            all_data.append(df)
            time.sleep(0.3)
        except Exception as e:
            print(f"  [WARN] Failed to fetch {name} ({code}): {e}")
    result = pd.concat(all_data, ignore_index=True)
    return result


def compute_monthly_returns(daily_data: pd.DataFrame) -> pd.DataFrame:
    """从日线数据计算月度收益率"""
    daily_data = daily_data.copy()
    daily_data["month"] = daily_data["date"].dt.to_period("M")

    # 取每月最后一个交易日的收盘价
    month_end = daily_data.groupby(["code", "name", "month"]).last().reset_index()
    month_end = month_end.sort_values(["code", "month"])
    month_end["monthly_return"] = month_end.groupby("code")["close"].pct_change()

    return month_end[["code", "name", "month", "date", "close", "monthly_return"]].dropna()


def compute_fundamental_scores(daily_data: pd.DataFrame, lookback_months: int = 12) -> pd.DataFrame:
    """
    构建行业景气度评分体系
    
    由于akshare免费接口无法获取历史PE/ROE月度面板数据，
    我们使用价格动量 + 波动率 + 成交额变化作为景气度代理指标：
    
    1. 动量得分 (Momentum): 过去N个月收益率，越高越好
    2. 波动调整动量 (Risk-Adj Momentum): 收益/波动率，类似夏普
    3. 成交额变化 (Turnover Trend): 成交额增速，资金关注度
    """
    df = daily_data.copy()
    df["month"] = df["date"].dt.to_period("M")

    records = []
    industries = df["code"].unique()
    months = sorted(df["month"].unique())

    for m in months:
        m_end = m.to_timestamp() + pd.offsets.MonthEnd(0)
        m_start = (m - lookback_months).to_timestamp()

        for ind in industries:
            ind_data = df[(df["code"] == ind) & (df["date"] >= m_start) & (df["date"] <= m_end)]
            if len(ind_data) < 20:
                continue

            ind_name = ind_data["name"].iloc[0]
            close_series = ind_data["close"]
            amount_series = ind_data["amount"]

            # 1) Momentum: cumulative return over lookback
            momentum = close_series.iloc[-1] / close_series.iloc[0] - 1

            # 2) Volatility: annualized daily return std
            daily_ret = close_series.pct_change().dropna()
            vol = daily_ret.std() * np.sqrt(252) if len(daily_ret) > 5 else np.nan

            # 3) Risk-adjusted momentum
            risk_adj_mom = momentum / vol if vol and vol > 0 else 0

            # 4) Turnover trend: recent 3mo avg amount / prior period avg amount
            if len(amount_series) > 60:
                recent_amt = amount_series.iloc[-60:].mean()
                prior_amt = amount_series.iloc[:-60].mean()
                turnover_trend = recent_amt / prior_amt - 1 if prior_amt > 0 else 0
            else:
                turnover_trend = 0

            records.append({
                "code": ind,
                "name": ind_name,
                "month": m,
                "momentum": momentum,
                "volatility": vol,
                "risk_adj_momentum": risk_adj_mom,
                "turnover_trend": turnover_trend,
            })

    scores_df = pd.DataFrame(records)

    # 每月截面标准化为百分位排名 (0~1)
    for col in ["momentum", "risk_adj_momentum", "turnover_trend"]:
        scores_df[f"{col}_rank"] = scores_df.groupby("month")[col].rank(pct=True)

    # 综合评分 = 等权平均
    scores_df["composite_score"] = (
        scores_df["momentum_rank"]
        + scores_df["risk_adj_momentum_rank"]
        + scores_df["turnover_trend_rank"]
    ) / 3

    return scores_df


if __name__ == "__main__":
    print("Fetching Shenwan industry list...")
    industry_list = get_sw_industry_list()
    print(f"Found {len(industry_list)} industries")
    industry_list.to_csv(os.path.join(DATA_DIR, "sw_industry_list.csv"), index=False)

    print("\nFetching daily data for all industries (since 2022)...")
    daily_data = fetch_all_industry_daily(industry_list, start_date="2021-01-01")
    daily_data.to_csv(os.path.join(DATA_DIR, "sw_industry_daily.csv"), index=False)
    print(f"Saved {len(daily_data)} rows")

    print("\nFetching CSI 300 data...")
    csi300 = get_csi300_daily(start_date="20210101")
    csi300.to_csv(os.path.join(DATA_DIR, "csi300_daily.csv"), index=False)
    print(f"Saved {len(csi300)} rows")

    print("\nDone!")
