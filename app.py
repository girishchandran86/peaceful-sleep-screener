# app.py (optimized price fetching)
import streamlit as st
import pandas as pd
import yfinance as yf
import requests
from io import StringIO

# -----------------------------
# Index ticker fetcher
# -----------------------------
@st.cache_data
def get_index_tickers(index_name):
    if index_name == "S&P 500":
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers)
        r.raise_for_status()
        table = pd.read_html(StringIO(r.text))[0]
        return table['Symbol'].tolist()
    
    elif index_name == "NIFTY 100":
        url = "https://www1.nseindia.com/content/indices/ind_nifty100list.csv"
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers)
        r.raise_for_status()
        table = pd.read_csv(StringIO(r.text))
        return table['Symbol'].tolist()
    
    else:
        st.warning("Index not supported")
        return []

# -----------------------------
# Screener function (optimized)
# -----------------------------
@st.cache_data
def peaceful_sleep_screener(tickers, filters):
    qualified_stocks = []

    # Fetch all tickers' info in one go
    tickers_str = " ".join(tickers)
    all_data = yf.download(tickers_str, period="1y", interval="1d", group_by='ticker', threads=True, progress=False)

    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            info = stock.info

            beta = info.get('beta', 999)
            debt_to_equity = info.get('debtToEquity', 999)
            pe_ratio = info.get('trailingPE', 999)
            roe = info.get('returnOnEquity', 0)
            dividend_yield = info.get('dividendYield', 0)
            fcf = info.get('freeCashflow', 0)
            price = info.get('currentPrice', 0)

            if any(v in [None, 0, 999] for v in [beta, debt_to_equity, pe_ratio, price]):
                continue

            if (beta <= filters['beta_max'] and
                debt_to_equity <= filters['de_ratio_max'] and
                pe_ratio <= filters['pe_max'] and
                roe >= filters['roe_min'] and
                dividend_yield >= filters['dividend_min'] and
                fcf >= filters['fcf_min']):

                # Quality score
                score = (
                    (1 - beta/filters['beta_max']) * 20 +
                    (1 - debt_to_equity/filters['de_ratio_max']) * 20 +
                    (roe/filters['roe_max']) * 20 +
                    (dividend_yield/filters['dividend_max']) * 20 +
                    (fcf/filters['fcf_max']) * 20
                )

                # Price change calculations from bulk data
                price_changes = {}
                periods = {
                    '1D': 1,
                    '1W': 5,
                    '1M': 22,
                    '6M': 130,
                    '1Y': 260
                }

                if ticker in all_data.columns.levels[0]:
                    hist = all_data[ticker]['Close'].dropna()
                    for label, days in periods.items():
                        if len(hist) >= days:
                            old_price = hist.iloc[-days]
                            price_changes[label] = round((price - old_price)/old_price*100, 2)
                        else:
                            price_changes[label] = None
                else:
                    for label in periods:
                        price_changes[label] = None

                qualified_stocks.append({
                    'Ticker': ticker,
                    'Company': info.get('shortName', 'N/A'),
                    'Sector': info.get('sector', 'N/A'),
                    'Beta': round(beta, 2),
                    'D/E Ratio': round(debt_to_equity, 2),
                    'P/E': round(pe_ratio, 2),
                    'ROE (%)': round(roe*100, 2),
                    'Dividend (%)': round(dividend_yield*100, 2),
                    'FCF ($M)': round(fcf/1e6, 2),
                    'Price ($)': price,
                    '1D (%)': price_changes['1D'],
                    '1W (%)': price_changes['1W'],
                    '1M (%)': price_changes['1M'],
                    '6M (%)': price_changes['6M'],
                    '1Y (%)': price_changes['1Y'],
                    'Quality Score': round(score, 2)
                })

        except Exception:
            continue

    df = pd.DataFrame(qualified_stocks)
    if not df.empty:
        df = df.sort_values(by='Quality Score', ascending=False)
    return df
