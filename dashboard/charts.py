import matplotlib.pyplot as plt
import pandas as pd

def equity_curve(df):
    """Generates an equity curve based on cumulative profit."""
    if df.empty: return plt.figure()
    df = df.sort_values("date")
    df["equity"] = df["pnl"].cumsum()

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(df["equity"], marker='o', linestyle='-')
    ax.set_title("📈 Equity Curve (Cumulative PnL)")
    ax.set_xlabel("Trades Count")
    ax.set_ylabel("PnL (₹)")
    ax.grid(True)
    return fig

def win_loss_pie(df):
    """Generates a win-loss distribution pie chart."""
    if df.empty: return plt.figure()
    wins = len(df[df["pnl"] > 0])
    losses = len(df[df["pnl"] <= 0])

    fig, ax = plt.subplots()
    ax.pie([wins, losses], labels=["Wins", "Losses"], autopct="%1.1f%%", colors=["#4CAF50", "#F44336"])
    ax.set_title("📊 Win/Loss Distribution")
    return fig
