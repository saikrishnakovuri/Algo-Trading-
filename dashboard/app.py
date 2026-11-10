import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from loader import load_data
from charts import equity_curve, win_loss_pie

# Set wide layout
st.set_page_config(layout="wide", page_title="📈 AI AlgoTrading Dashboard")

st.title("📊 AI Trading Intelligence Dashboard")
st.markdown("---")

df = load_data()

if df.empty:
    st.error("No trade data found in meta_db.json. Run a massive backtest first.")
else:
    # --- KPIs ---
    total_trades = len(df)
    total_profit = df["pnl"].sum()
    win_rate = len(df[df["pnl"] > 0]) / total_trades * 100
    avg_pnl = df["pnl"].mean()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Trades", total_trades)
    col2.metric("Total Profit", f"₹ {total_profit:,.2f}")
    col3.metric("Win Rate %", f"{win_rate:.2f}%")
    col4.metric("Avg PnL per Trade", f"₹ {avg_pnl:.2f}")

    # --- Charts Section ---
    st.markdown("### 📊 Overall Performance")
    col_chart1, col_chart2 = st.columns([2, 1])

    with col_chart1:
        st.pyplot(equity_curve(df))

    with col_chart2:
        st.pyplot(win_loss_pie(df))

    # --- Detailed Breakdowns ---
    st.markdown("### 🔍 Meta-Analysis Insights")
    col_stk, col_setup, col_time = st.columns(3)

    with col_stk:
        st.subheader("🏙️ Top Stocks")
        st.bar_chart(df.groupby("symbol")["pnl"].sum().sort_values(ascending=False).head(10))

    with col_setup:
        st.subheader("🎯 Best Setups")
        st.bar_chart(df.groupby("setup")["pnl"].sum().sort_values(ascending=False))

    with col_time:
        st.subheader("⏰ Best Hours")
        # Extract hour if time field exists or from date
        df["hour"] = df["date"].dt.hour
        st.bar_chart(df.groupby("hour")["pnl"].sum())

    # --- Drawdown Section ---
    st.markdown("### 📉 Risk Analysis")
    df = df.sort_values("date")
    df["equity"] = df["pnl"].cumsum()
    df["peak"] = df["equity"].cummax()
    df["drawdown"] = df["peak"] - df["equity"]
    
    st.area_chart(df["drawdown"])
    st.caption("Trailing Drawdown from Equity Peak")

    # --- Trade Log ---
    st.markdown("### 📜 Detailed Trade Log")
    st.dataframe(df.sort_values(by="date", ascending=False), use_container_width=True)

st.sidebar.title("Configuration")
st.sidebar.info("This dashboard reads data from meta_db.json to visualize the AI's learning progress.")
