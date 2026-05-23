import yfinance as yf
import pandas as pd
import numpy as np


def fetch_all(ticker: str) -> dict:
    t = yf.Ticker(ticker)

    info = t.info or {}
    hist = t.history(period="5y", interval="1d")

    quarterly_income = _safe_df(t.quarterly_income_stmt)
    quarterly_balance = _safe_df(t.quarterly_balance_sheet)
    quarterly_cashflow = _safe_df(t.quarterly_cashflow)

    annual_income = _safe_df(t.income_stmt)
    annual_balance = _safe_df(t.balance_sheet)
    annual_cashflow = _safe_df(t.cashflow)

    return {
        "info": info,
        "history": hist,
        "quarterly_income": quarterly_income,
        "quarterly_balance": quarterly_balance,
        "quarterly_cashflow": quarterly_cashflow,
        "annual_income": annual_income,
        "annual_balance": annual_balance,
        "annual_cashflow": annual_cashflow,
    }


def _safe_df(df) -> pd.DataFrame:
    if df is None or (isinstance(df, pd.DataFrame) and df.empty):
        return pd.DataFrame()
    return df


def _get(df: pd.DataFrame, *row_keys, col_idx: int = 0, default=np.nan):
    if df.empty:
        return default
    for key in row_keys:
        if key in df.index:
            val = df.iloc[df.index.get_loc(key), col_idx]
            if pd.notna(val):
                return float(val)
    return default
