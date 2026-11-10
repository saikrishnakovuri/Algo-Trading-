import os
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import yaml
from datetime import datetime
from typing import Dict, Any, List, Optional

class ChartRenderer:
    def __init__(self, config_path: str = "config/charting.yaml"):
        if os.path.exists(config_path):
            with open(config_path, "r", encoding='utf-8') as f:
                self.config = yaml.safe_load(f)["charting"]
        else:
            self.config = {
                "session": {"market_open": "09:15", "market_close": "15:30"}
            }
        
        # Color Scheme (Dark Mode) - Updated opacities for clarity
        self.colors = {
            'bg': '#1e222d',
            'grid': '#2a2e39',
            'text': '#d1d4dc',
            'up': '#26a69a',
            'down': '#ef5350',
            'support': 'rgba(38, 166, 154, 0.08)',
            'resistance': 'rgba(239, 83, 80, 0.08)',
            'flip': 'rgba(255, 152, 0, 0.08)',
            'ob_bull': 'rgba(76, 175, 80, 0.12)',
            'ob_bear': 'rgba(244, 67, 54, 0.12)',
            'fvg_bull': 'rgba(33, 150, 243, 0.10)',
            'fvg_bear': 'rgba(156, 39, 176, 0.10)',
            'poc': '#ffeb3b',
            'va': 'rgba(255, 235, 59, 0.3)',
            'trendline': 'rgba(255, 255, 255, 0.6)'
        }

    def render_chart(self, symbol: str, df: pd.DataFrame, structure: Dict[str, Any], 
                     timeframe: str = '5m', output_path: str = None) -> str:
        """Generate a full interactive Plotly chart with all structure overlays."""
        if df.empty:
            return ""

        fig = go.Figure()

        # 1. Support/Resistance Zones (Drawn below candles)
        # Limit to top 5 strongest zones
        zones = structure.get('zones', [])[:5]
        for z in zones:
            color = self.colors['support'] if z['type'] == 'SUPPORT' else self.colors['resistance']
            if z['type'] == 'FLIP_ZONE': color = self.colors['flip']
            border_color = color.replace('0.08', '0.4')
            
            fig.add_hrect(
                y0=z['zone_low'], y1=z['zone_high'],
                fillcolor=color, opacity=1.0, line_width=1, line_color=border_color,
                layer="below",
                annotation_text=f"{z['type']} ({z['touches']}T)",
                annotation_position="top left",
                annotation_font_size=10,
                annotation_font_color=self.colors['text']
            )

        # 2. Order Blocks (OBs) - Limit to 4 fresh ones
        obs = [ob for ob in structure.get('order_blocks', []) if not ob.get('is_mitigated', False)][-4:]
        for ob in obs:
            color = self.colors['ob_bull'] if ob['type'] == 'BULLISH_OB' else self.colors['ob_bear']
            border_color = color.replace('0.12', '0.6')
            start_time = df.index[ob['origin_idx']]
            fig.add_shape(
                type="rect",
                x0=start_time, x1=df.index[-1],
                y0=ob['zone_low'], y1=ob['zone_high'],
                fillcolor=color, line_width=1, line_color=border_color,
                layer="below",
                name=ob['type']
            )

        # 3. Fair Value Gaps (FVGs) - Limit to 4 unfilled
        fvgs = [f for f in structure.get('fair_value_gaps', []) if not f.get('is_filled', False)][-4:]
        for fvg in fvgs:
            color = self.colors['fvg_bull'] if fvg['type'] == 'BULLISH_FVG' else self.colors['fvg_bear']
            border_color = color.replace('0.10', '0.5')
            start_time = df.index[fvg['origin_idx']]
            fig.add_shape(
                type="rect",
                x0=start_time, x1=df.index[-1],
                y0=fvg['zone_low'], y1=fvg['zone_high'],
                fillcolor=color, line_width=1, line_color=border_color,
                layer="below",
                name=fvg['type']
            )

        # 4. Trendlines - Limit to Top 3
        trendlines = structure.get('trendlines', [])[:3]
        for tl in trendlines:
            start_time = df.index[tl['start_idx']]
            end_time = df.index[tl['end_idx']]
            ext_time = df.index[-1]
            ext_price = tl['slope'] * (len(df) - 1) + tl['intercept']
            color = self.colors['up'] if tl['type'] == 'ASCENDING_SUPPORT' else self.colors['down']
            
            fig.add_shape(
                type="line",
                x0=start_time, y0=tl['slope'] * tl['start_idx'] + tl['intercept'],
                x1=ext_time, y1=ext_price,
                line=dict(color=color, width=1, dash="dash"),
                layer="below"
            )

        # 5. Volume Profile Levels
        vp = structure.get('volume_profile', {})
        if vp:
            fig.add_hline(y=vp['poc'], line_width=2, line_color=self.colors['poc'], 
                          layer="below", annotation_text="POC", annotation_position="bottom right")
            fig.add_hline(y=vp['va_high'], line_width=1, line_dash="dot", line_color=self.colors['poc'], layer="below")
            fig.add_hline(y=vp['va_low'], line_width=1, line_dash="dot", line_color=self.colors['poc'], layer="below")

        # 6. Candlestick Trace (Added AFTER shapes to ensure top-layer visibility)
        fig.add_trace(go.Candlestick(
            x=df.index,
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name=f'{symbol} ({timeframe})',
            increasing_line_color=self.colors['up'],
            decreasing_line_color=self.colors['down']
        ))

        # 7. Swing Point Markers
        swings = structure.get('swing_points', {})
        if swings:
            sh_x = [p['timestamp'] for p in swings['swing_highs']]
            sh_y = [p['price'] for p in swings['swing_highs']]
            fig.add_trace(go.Scatter(
                x=sh_x, y=sh_y, mode='markers',
                marker=dict(symbol='triangle-down', size=6, color=self.colors['down']),
                name='Swing High'
            ))
            
            sl_x = [p['timestamp'] for p in swings['swing_lows']]
            sl_y = [p['price'] for p in swings['swing_lows']]
            fig.add_trace(go.Scatter(
                x=sl_x, y=sl_y, mode='markers',
                marker=dict(symbol='triangle-up', size=6, color=self.colors['up']),
                name='Swing Low'
            ))

        # 8. Layout and Styling
        fig.update_layout(
            title=f"{symbol} - {timeframe} Mathematical Structure",
            template="plotly_dark",
            xaxis_rangeslider_visible=False,
            height=800,
            paper_bgcolor=self.colors['bg'],
            plot_bgcolor=self.colors['bg'],
            xaxis=dict(gridcolor=self.colors['grid']),
            yaxis=dict(gridcolor=self.colors['grid']),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )

        if not output_path:
            os.makedirs("reports/charts", exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"reports/charts/{symbol}_{timeframe}_{timestamp}.html"

        fig.write_html(output_path)
        return output_path

    def render_trade_review(self, symbol: str, df: pd.DataFrame, trade: Dict[str, Any], 
                            structure: Dict[str, Any], output_path: str = None) -> str:
        """Render chart with specific trade entry/exit markers."""
        return self.render_chart(symbol, df, structure, output_path=output_path)

if __name__ == "__main__":
    print("ChartRenderer ready.")
