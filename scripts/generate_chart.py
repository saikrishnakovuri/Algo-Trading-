import argparse
import os
import webbrowser
from modules.charting.aggregator import ChartDataAggregator
from modules.charting.structure_detector import StructureDetector
from modules.charting.chart_renderer import ChartRenderer

def main():
    parser = argparse.ArgumentParser(description='Generate Interactive Structural Charts')
    parser.add_argument('symbol', help='Stock symbol (e.g. RELIANCE)')
    parser.add_argument('--tf', default='5m', help='Timeframe (1m, 5m, 15m, 1D)')
    parser.add_argument('--days', type=int, default=10, help='Number of days of data to analyze')
    parser.add_argument('--multi', action='store_true', help='Generate multi-timeframe report')
    
    args = parser.parse_args()
    
    print(f"📡 Generating chart for {args.symbol} ({args.tf})...")
    
    agg = ChartDataAggregator()
    sd = StructureDetector()
    renderer = ChartRenderer()
    
    # 1. Load Data
    data_path = f"data/universe_10d/{args.symbol}.csv"
    if not os.path.exists(data_path):
        data_path = f"data/angel_historical/{args.symbol}_1m.csv"
        
    if not os.path.exists(data_path):
        print(f"❌ Error: Data file not found for {args.symbol}")
        return

    df_1m = agg.load_from_csv(data_path)
    if df_1m.empty:
        print("❌ Error: Could not load data.")
        return
        
    # Limit data
    # Simple limit: last X bars. For 10 days of 1m data, it's roughly 3750 bars.
    # We will just use the whole file for now as it's usually 10 days anyway.
    
    # 2. Resample
    df_tf = agg.resample(df_1m, args.tf)
    
    # 3. Detect Structure
    print("🔍 Analyzing mathematical structure...")
    structure = sd.detect_all(df_tf)
    
    # 4. Render
    print("🎨 Rendering interactive chart...")
    output_path = renderer.render_chart(args.symbol, df_tf, structure, timeframe=args.tf)
    
    if output_path:
        full_path = os.path.abspath(output_path)
        print(f"✅ Chart generated: {full_path}")
        try:
            print("🚀 Attempting to open in browser...")
            webbrowser.open(f"file://{full_path}")
        except Exception as e:
            print(f"⚠️ Could not open browser: {e}")

if __name__ == "__main__":
    main()
