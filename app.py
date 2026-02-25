# app.py
import streamlit as st
import pandas as pd
import yfinance as yf
from io import BytesIO, StringIO
import requests

# -----------------------------
# Fetch live S&P 500 tickers
# -----------------------------
@st.cache_data
def get_sp500_tickers():
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/115.0.0.0 Safari/537.36"
    }
    
    r = requests.get(url, headers=headers)
    r.raise_for_status()
    
    table = pd.read_html(StringIO(r.text))[0]
    return table['Symbol'].tolist()

# -----------------------------
# Screener function
# -----------------------------
@st.cache_data
def peaceful_sleep_screener(tickers, filters):
    qualified_stocks = []

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

            if any(v in [None, 0, 999] for v in [beta, debt_to_equity, pe_ratio]):
                continue

            if (beta <= filters['beta_max'] and
                debt_to_equity <= filters['de_ratio_max'] and
                pe_ratio <= filters['pe_max'] and
                roe >= filters['roe_min'] and
                dividend_yield >= filters['dividend_min'] and
                fcf >= filters['fcf_min']):

                score = (
                    (1 - beta/filters['beta_max']) * 20 +
                    (1 - debt_to_equity/filters['de_ratio_max']) * 20 +
                    (roe/filters['roe_max']) * 20 +
                    (dividend_yield/filters['dividend_max']) * 20 +
                    (fcf/filters['fcf_max']) * 20
                )

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
                    'Quality Score': round(score, 2)
                })

        except Exception:
            continue

    df = pd.DataFrame(qualified_stocks)
    if not df.empty:
        df = df.sort_values(by='Quality Score', ascending=False)
    return df

# -----------------------------
# Excel download
# -----------------------------
def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Peaceful Sleep')
    return output.getvalue()

# -----------------------------
# Streamlit Layout
# -----------------------------
st.set_page_config(page_title="Peaceful Sleep Stock Screener", layout="wide")
st.title("🌙 Peaceful Sleep Stock Screener")

st.markdown("""
Scan the **S&P 500** for low-risk, high-quality stocks.
Adjust the sliders to filter based on Beta, P/E, ROE, Dividend, Free Cash Flow.
""")

# Sidebar filters
st.sidebar.header("Filters")
beta_max = st.sidebar.slider("Maximum Beta", 0.0, 2.0, 0.85)
de_ratio_max = st.sidebar.slider("Maximum D/E Ratio", 0, 200, 50)
pe_max = st.sidebar.slider("Maximum P/E Ratio", 0, 100, 25)
roe_min = st.sidebar.slider("Minimum ROE (%)", 0.0, 0.5, 0.12)
dividend_min = st.sidebar.slider("Minimum Dividend Yield (%)", 0.0, 10.0, 0.0)
fcf_min = st.sidebar.number_input("Minimum Free Cash Flow ($M)", 0.0, 50000.0, 0.0)

filters = {
    'beta_max': beta_max,
    'de_ratio_max': de_ratio_max,
    'pe_max': pe_max,
    'roe_min': roe_min,
    'roe_max': 0.5,
    'dividend_min': dividend_min / 100,
    'dividend_max': 0.1,
    'fcf_min': fcf_min*1e6,
    'fcf_max': 5e10
}

# Run screener
if st.button("Run Screener"):
    with st.spinner("Fetching live S&P 500 tickers and scanning stocks..."):
        tickers = get_sp500_tickers()
        results_df = peaceful_sleep_screener(tickers, filters)

    if not results_df.empty:
        st.success(f"Found {len(results_df)} stocks matching your criteria")
        st.dataframe(results_df)

        excel_data = to_excel(results_df)
        st.download_button(
            label="📥 Download Excel",
            data=excel_data,
            file_name="peaceful_sleep_stocks.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.warning("No stocks matched your criteria today.")