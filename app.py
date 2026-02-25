import streamlit as st
import yfinance as yf
import pandas as pd

st.title("Peaceful Sleep Stock Screener")

ticker = st.text_input("Enter Stock Ticker", "AAPL")

if st.button("Analyze"):

    stock = yf.Ticker(ticker)
    info = stock.get_info()

    data = {
        "Company": info.get("shortName"),
        "Sector": info.get("sector"),
        "Beta": info.get("beta"),
        "PE Ratio": info.get("trailingPE"),
        "ROE": info.get("returnOnEquity"),
        "Dividend Yield": info.get("dividendYield"),
        "Free Cash Flow": info.get("freeCashflow")
    }

    st.write(pd.DataFrame(data, index=[0]))
