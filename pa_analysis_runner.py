from modules.data_layer import DataLayer
from modules.indicator_engine import IndicatorEngine
from modules.price_action_engine import PriceActionEngine
from modules import option_chain
import json

if __name__ == '__main__':
    dl = DataLayer()
    df = dl.fetch_nifty_data(interval='15m')
    if df is None:
        print('No market data available')
        exit(1)

    df = IndicatorEngine.add_indicators(df)

    # Run full price-action evaluation
    analysis = PriceActionEngine.evaluate_price_action(df)

    # Get raw supports/resistances and run trading pipeline
    supports, resistances = PriceActionEngine.find_support_resistance(df)

    # Fetch option chain (deterministic fallback if NSE blocked)
    option_df = option_chain.fetch_option_chain(underlying_price=PriceActionEngine._safe_float(df.iloc[-1]['Close']), use_nse_api=False)
    option_sig = option_chain.option_chain_signal(option_df)

    tp = PriceActionEngine.trading_pipeline(df, supports, resistances, option_df=option_df)

    print('--- Price Action Analysis ---')
    print(json.dumps(analysis, indent=2, default=str))
    print('\n--- Trading Pipeline Recommendation ---')
    print(json.dumps(tp, indent=2, default=str))
    print('\n--- Option Chain Signal ---')
    print(json.dumps(option_sig, indent=2, default=str))
