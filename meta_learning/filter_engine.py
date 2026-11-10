from .analyzer import compute_metrics

def filter_entities(stats):
    """Filters stocks and setups that have a positive expectancy and a minimum trade sample."""
    selected_stocks = []
    selected_setups = []

    # 1. STOCK FILTER: Remove noise (trades < 20) and keep only positive expectancy
    stock_metrics = []
    for stock, pnls in stats["by_stock"].items():
        m = compute_metrics(pnls)
        if m["trades"] >= 20: # Minimum trade count filter (Institutional Grade)
            stock_metrics.append({"symbol": stock, "expectancy": m["expectancy"]})

    # Sort by expectancy and keep top 30%
    stock_metrics.sort(key=lambda x: x["expectancy"], reverse=True)
    keep_count = max(1, int(len(stock_metrics) * 0.3))
    selected_stocks = [s["symbol"] for s in stock_metrics[:keep_count] if s["expectancy"] > 0]

    # 2. SETUP FILTER: Keep only profitable ones
    for setup, pnls in stats["by_setup"].items():
        m = compute_metrics(pnls)
        if m["expectancy"] > 0:
            selected_setups.append(setup)

    return selected_stocks, selected_setups
