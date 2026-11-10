import traceback
from modules.data_layer import DataLayer
from modules.indicator_engine import IndicatorEngine
from modules.price_action_engine import PriceActionEngine
from modules.momentum_engine import MomentumBreakoutEngine
from modules.ai_analysis import AIAnalysisLayer
from modules.decision_engine import DecisionEngine
from modules.learning import LearningSystem


class Orchestrator:
    def __init__(self):
        self.data_layer = DataLayer()
        self.indicator = IndicatorEngine()
        self.pa = PriceActionEngine()
        self.momentum = MomentumBreakoutEngine()
        self.ai = AIAnalysisLayer()
        self.decision_engine = DecisionEngine()
        self.learning = LearningSystem()

    def run_cycle(self, mock_market_summary: str = None, dry_run: bool = True, strategy='momentum'):
        """Run a single analysis cycle. 
        `strategy`: 'pa' (Price Action) or 'momentum' (Momentum Breakout)
        """
        try:
            if mock_market_summary:
                market_summary = mock_market_summary
            else:
                # Fetch multi-timeframe data
                mtf = self.data_layer.get_multi_timeframe_data()
                if not mtf or mtf.get('15m') is None or mtf.get('5m') is None or mtf.get('1m') is None:
                    return "Trade: NO TRADE\nConfidence: 0%\nReason: Multi-timeframe data unavailable\nEntry: -\nStop Loss: -\nTarget 1: -\nTarget 2: -\n"

                # Option chain
                try:
                    from modules import option_chain
                    option_df = option_chain.fetch_option_chain(underlying_price=PriceActionEngine._safe_float(mtf['15m']['Close'].iloc[-1]), use_nse_api=False)
                except Exception:
                    option_df = None

                if strategy == 'momentum':
                    # Use Momentum Engine
                    final_dict = self.momentum.generate_signal(mtf['1m'], symbol="LIVE")
                    # Map momentum fields to orchestrator format
                    final_dict['trade'] = final_dict.get('signal', 'NO TRADE')
                    if final_dict['trade'] == 'BUY': final_dict['trade'] = 'CE'
                    elif final_dict['trade'] == 'SELL': final_dict['trade'] = 'PE'
                    final_dict['confidence'] = min(100, int(final_dict.get('score', 0) * 10))
                else:
                    # Default: Price Action Engine
                    tf_15 = self.pa.analyze_timeframe(mtf['15m'])
                    tf_5 = self.pa.analyze_timeframe(mtf['5m'])
                    tf_1 = self.pa.analyze_timeframe(mtf['1m'])
                    mtf_analyses = {'15m': tf_15, '5m': tf_5, '1m': tf_1}
                    final_dict = self.pa.final_trading_decision(mtf_analyses, option_df, mtf['5m'])

                # Build strict-format decision text
                entry_str = f"{final_dict.get('entry'):.2f}" if final_dict.get('entry') is not None else "-"
                sl_str = f"{final_dict.get('sl') or final_dict.get('stop_loss'):.2f}" if (final_dict.get('sl') or final_dict.get('stop_loss')) is not None else "-"
                t1_str = f"{final_dict.get('target1'):.2f}" if final_dict.get('target1') is not None else "-"
                t2_str = f"{final_dict.get('target2'):.2f}" if final_dict.get('target2') is not None else "-"

                market_summary = f"""
    MultiTF Decision Summary
    Trade: {final_dict.get('trade')}
    Confidence: {final_dict.get('confidence')}%
    Reasons: {'; '.join(final_dict.get('reasons') or [])}
    Entry: {entry_str}
    Stop Loss: {sl_str}
    Target 1: {t1_str}
    Target 2: {t2_str}
    Option Signal: {option_df is not None}
    """

            # Use the generated strict-format summary as the decision payload
            ai_text = market_summary

            # Evaluate via Decision Engine (provide 15m trend for context if available)
            trend_ctx = None
            try:
                trend_ctx = mtf_analyses.get('15m', {}).get('trend') if 'mtf_analyses' in locals() else None
            except Exception:
                trend_ctx = None

            final = self.decision_engine.evaluate(ai_text, market_context={'trend': trend_ctx})

            # Publish to gateway
            if not final.startswith('Trade: NO TRADE'):
                from market_gateway.event_stream import event_stream
                event_stream.publish_signal("LIVE", final.split('\n')[0], final.split('\n')[2])

            # If trade approved, log it (best-effort parsing)
            if not final.startswith('Trade: NO TRADE'):
                parsed = self.decision_engine.parse_ai_output(ai_text)
                trade_record = {
                    'trade_type': parsed.get('trade'),
                    'entry': parsed.get('entry'),
                    'sl': parsed.get('sl'),
                    't1': parsed.get('t1'),
                    't2': parsed.get('t2'),
                    'confidence': parsed.get('confidence'),
                    'reason': parsed.get('reason'),
                    'result': None,
                    'pnl': None,
                    'meta': {'ai_text': ai_text}
                }
                if not dry_run:
                    self.learning.log_trade(trade_record)

            return final

        except Exception as e:
            traceback.print_exc()
            return ("Trade: NO TRADE\nConfidence: 0%\nReason: Exception during analysis: " + str(e) + "\n"
                    "Entry: -\nStop Loss: -\nTarget 1: -\nTarget 2: -\n")
