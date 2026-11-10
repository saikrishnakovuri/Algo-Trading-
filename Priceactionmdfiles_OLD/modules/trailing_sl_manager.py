"""
Trailing Stop-Loss Manager with Graduated Partial Profit Booking
====================================================================

Manages the exit side of trades:
- Tracks multiple target levels per trade
- Executes partial exits at each target (configurable %)
- Moves SL to previous target level after each partial exit
- Works in both PAPER and LIVE modes

This module does NOT:
- Generate signals (that's the engines' job)
- Decide entry timing (that's the strategy selector's job)
- Handle position sizing for entry (that's the risk engine's job)

Usage:
    from modules.trailing_sl_manager import TrailingSLManager

    tsl = TrailingSLManager(config_path="config/trailing_sl.yaml")

    # When a new trade opens:
    trade = tsl.create_trade(
        symbol="RELIANCE", direction="CE", entry_price=1000.0,
        sl_price=980.0, original_qty=1000, strategy="MEAN_REVERSION"
    )

    # On each scan cycle, check for exits:
    exits = tsl.check_exits(trade, current_high=1025.0, current_low=1018.0, current_close=1022.0)
    # exits = [{'type': 'PARTIAL_T1', 'qty': 200, 'price': 1020.0, 'new_sl': 1000.0}, ...]
"""

import yaml
import math
import logging
from datetime import datetime
from typing import Optional, List, Dict
from dataclasses import dataclass, field

logger = logging.getLogger('live_trader')


@dataclass
class ManagedTrade:
    """
    Represents a trade managed by the TSL system.
    This replaces the simple dict in active_trades.
    """
    symbol: str
    direction: str              # "CE" (LONG) or "PE" (SHORT)
    entry_price: float
    original_sl: float          # never changes - the initial SL
    current_sl: float           # moves up/down as targets are hit
    original_qty: int           # total qty at entry
    remaining_qty: int          # qty still in the trade
    strategy: str               # "MEAN_REVERSION", "MOMENTUM", etc.
    pattern: str                # pattern name from signal
    score: float                # signal score
    confidence: float           # signal confidence
    start_time: datetime = field(default_factory=datetime.now)

    # Target tracking
    risk_per_share: float = 0.0         # |entry - original_sl|
    targets_hit: List[int] = field(default_factory=list)  # indices of targets already hit
    partial_exits: List[Dict] = field(default_factory=list)  # log of each partial exit
    custom_partials: Optional[List[Dict]] = None # [{r_multiple, exit_pct}, ...]

    # State
    is_closed: bool = False
    close_reason: str = ""
    total_pnl: float = 0.0

    def to_dict(self) -> dict:
        """Convert to dict for JSON serialization (active_trades.json)."""
        return {
            'symbol': self.symbol,
            'direction': self.direction,
            'entry': self.entry_price,
            'original_sl': self.original_sl,
            'current_sl': self.current_sl,
            'original_qty': self.original_qty,
            'remaining_qty': self.remaining_qty,
            'strategy': self.strategy,
            'pattern': self.pattern,
            'score': self.score,
            'confidence': self.confidence,
            'start_time': self.start_time.strftime('%Y-%m-%d %H:%M:%S'),
            'risk_per_share': self.risk_per_share,
            'targets_hit': self.targets_hit,
            'partial_exits': self.partial_exits,
            'is_closed': self.is_closed,
            'close_reason': self.close_reason,
            'total_pnl': self.total_pnl,
        }

    @classmethod
    def from_dict(cls, d: dict) -> 'ManagedTrade':
        """Recreate from dict (loading from active_trades.json)."""
        trade = cls(
            symbol=d['symbol'],
            direction=d['direction'],
            entry_price=d['entry'],
            original_sl=d['original_sl'],
            current_sl=d['current_sl'],
            original_qty=d['original_qty'],
            remaining_qty=d['remaining_qty'],
            strategy=d.get('strategy', ''),
            pattern=d.get('pattern', ''),
            score=d.get('score', 0),
            confidence=d.get('confidence', 0),
        )
        trade.risk_per_share = d.get('risk_per_share', abs(d['entry'] - d['original_sl']))
        trade.targets_hit = d.get('targets_hit', [])
        trade.partial_exits = d.get('partial_exits', [])
        trade.is_closed = d.get('is_closed', False)
        trade.close_reason = d.get('close_reason', '')
        trade.total_pnl = d.get('total_pnl', 0.0)
        try:
            trade.start_time = datetime.strptime(d['start_time'], '%Y-%m-%d %H:%M:%S')
        except (KeyError, ValueError):
            trade.start_time = datetime.now()
        return trade


class TrailingSLManager:
    """
    Manages graduated partial exits and trailing stop-loss.

    Flow per scan cycle:
    1. For each active ManagedTrade, call check_exits()
    2. check_exits() returns a list of exit events (can be 0, 1, or multiple)
    3. Each exit event has: type, qty, price, new_sl
    4. The caller (live_trader_v1.py) handles execution (paper log or real order)
    """

    def __init__(self, config_path: str = "config/trailing_sl.yaml", config: dict = None):
        if config:
            self.config = config
        else:
            with open(config_path, 'r') as f:
                self.config = yaml.safe_load(f)

        self.enabled = self.config.get('enabled', True)
        self.exit_schedule = self.config.get('partial_exits', [])
        self.min_remaining_qty = self.config.get('min_remaining_qty', 1)
        self.round_qty_to = self.config.get('round_qty_to', 1)
        self.use_high_low = self.config.get('paper_mode', {}).get('use_high_low_for_exits', True)
        self.same_bar_conflict = self.config.get('paper_mode', {}).get('same_bar_conflict', 'conservative')

    def create_trade(self, symbol: str, direction: str, entry_price: float,
                     sl_price: float, original_qty: int, strategy: str = "",
                     pattern: str = "", score: float = 0, confidence: float = 0,
                     start_time: datetime = None) -> ManagedTrade:
        """
        Create a new ManagedTrade with target levels calculated from entry and SL.
        """
        risk_per_share = abs(entry_price - sl_price)
        st = start_time if start_time else datetime.now()

        trade = ManagedTrade(
            symbol=symbol,
            direction=direction,
            entry_price=entry_price,
            original_sl=sl_price,
            current_sl=sl_price,
            original_qty=original_qty,
            remaining_qty=original_qty,
            strategy=strategy,
            pattern=pattern,
            score=score,
            confidence=confidence,
            risk_per_share=risk_per_share,
            start_time=st
        )

        target_list = [f"T{i+1}={self._target_price(trade, level['r_multiple']):.2f}" for i, level in enumerate(self.exit_schedule)]
        logger.info(
            f"TSL TRADE CREATED: {symbol} | {direction} | {st.strftime('%Y-%m-%d %H:%M')} | Entry={entry_price} | "
            f"SL={sl_price} | Qty={original_qty} | Risk/share={risk_per_share:.2f} | "
            f"Targets: {target_list}"
        )

        return trade

    def _target_price(self, trade: ManagedTrade, r_multiple: float) -> float:
        """Calculate target price for a given R-multiple."""
        if trade.direction == "CE":
            return trade.entry_price + (trade.risk_per_share * r_multiple)
        else:  # PE
            return trade.entry_price - (trade.risk_per_share * r_multiple)

    def _calc_partial_qty(self, trade: ManagedTrade, exit_pct: float) -> int:
        """
        Calculate how many shares to exit.
        exit_pct is percentage of ORIGINAL quantity.
        Round DOWN to nearest round_qty_to.
        """
        raw_qty = (exit_pct / 100.0) * trade.original_qty
        qty = int(raw_qty // self.round_qty_to) * self.round_qty_to

        # Don't exit more than remaining
        qty = min(qty, trade.remaining_qty)

        # If remaining after this exit would be below minimum, exit all
        if (trade.remaining_qty - qty) < self.min_remaining_qty and (trade.remaining_qty - qty) > 0:
            qty = trade.remaining_qty

        return qty

    def check_exits(self, trade: ManagedTrade, current_high: float,
                    current_low: float, current_close: float) -> List[Dict]:
        """
        Check if any exits should trigger for this trade.
        """
        if not self.enabled or trade.is_closed or trade.remaining_qty <= 0:
            return []

        exits = []

        # Use custom schedule if available
        schedule = trade.custom_partials if trade.custom_partials is not None else self.exit_schedule

        # -- STEP 1: Check SL FIRST (conservative) --
        sl_hit = False
        if trade.direction == "CE":
            if self.use_high_low:
                sl_hit = current_low <= trade.current_sl
            else:
                sl_hit = current_close <= trade.current_sl
        else:  # PE
            if self.use_high_low:
                sl_hit = current_high >= trade.current_sl
            else:
                sl_hit = current_close >= trade.current_sl

        # -- STEP 2: Check targets --
        targets_hit_this_bar = []

        if not sl_hit or self.same_bar_conflict != "conservative":
            for i, level in enumerate(schedule):
                if i in trade.targets_hit:
                    continue  # already hit this target

                target_price = self._target_price(trade, level['r_multiple'])

                target_reached = False
                if trade.direction == "CE":
                    if self.use_high_low:
                        target_reached = current_high >= target_price
                    else:
                        target_reached = current_close >= target_price
                else:  # PE
                    if self.use_high_low:
                        target_reached = current_low <= target_price
                    else:
                        target_reached = current_close <= target_price

                if target_reached:
                    targets_hit_this_bar.append(i)

        # -- STEP 3: Handle same-bar conflict --
        if sl_hit and targets_hit_this_bar and self.same_bar_conflict == "conservative":
            targets_hit_this_bar = []

        # -- STEP 4: Process target hits --
        for target_idx in sorted(targets_hit_this_bar):
            level = schedule[target_idx]
            target_price = self._target_price(trade, level['r_multiple'])
            exit_qty = self._calc_partial_qty(trade, level['exit_pct'])

            if exit_qty <= 0:
                continue

            # Calculate P&L for this partial
            if trade.direction == "CE":
                pnl = (target_price - trade.entry_price) * exit_qty
            else:
                pnl = (trade.entry_price - target_price) * exit_qty

            r_achieved = level['r_multiple']

            # Determine new SL: moves to PREVIOUS target level (Relaxed: BE only at T2)
            if target_idx == 0:
                new_sl = trade.original_sl  # T1 hit - SL remains at initial SL (relaxed)
            elif target_idx == 1:
                new_sl = trade.entry_price  # T2 hit - SL moves to entry (breakeven)
            else:
                prev_r = schedule[target_idx - 1]['r_multiple']
                new_sl = self._target_price(trade, prev_r)  # SL - previous target

            # Record the exit
            exit_event = {
                'type': f'PARTIAL_T{target_idx + 1}',
                'qty': exit_qty,
                'price': round(target_price, 2),
                'new_sl': round(new_sl, 2),
                'pnl': round(pnl, 2),
                'r_multiple': r_achieved,
                'target_idx': target_idx,
            }
            exits.append(exit_event)

            # Update trade state
            trade.targets_hit.append(target_idx)
            trade.remaining_qty -= exit_qty
            trade.current_sl = new_sl
            trade.total_pnl += pnl

            trade.partial_exits.append({
                'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'type': exit_event['type'],
                'qty': exit_qty,
                'price': target_price,
                'new_sl': new_sl,
                'pnl': round(pnl, 2),
                'r_multiple': r_achieved,
            })

            logger.info(
                f"TSL PARTIAL EXIT: {trade.symbol} | {exit_event['type']} | "
                f"Sold {exit_qty} @ {target_price:.2f} | PnL={pnl:+.2f} | "
                f"SL moved to {new_sl:.2f} | Remaining={trade.remaining_qty}"
            )

            # If no qty remaining, trade is fully closed
            if trade.remaining_qty <= 0:
                trade.is_closed = True
                trade.close_reason = f"ALL_TARGETS_HIT (last: T{target_idx + 1})"
                logger.info(
                    f"TSL TRADE COMPLETE: {trade.symbol} | All targets hit | "
                    f"Total PnL={trade.total_pnl:+.2f}"
                )
                return exits

        # -- STEP 5: If SL hit and still has remaining qty --
        if sl_hit and trade.remaining_qty > 0 and not trade.is_closed:
            sl_exit_qty = trade.remaining_qty

            if trade.direction == "CE":
                pnl = (trade.current_sl - trade.entry_price) * sl_exit_qty
            else:
                pnl = (trade.entry_price - trade.current_sl) * sl_exit_qty

            r_achieved = (trade.current_sl - trade.entry_price) / trade.risk_per_share if trade.direction == "CE" and trade.risk_per_share > 0 else 0
            if trade.direction == "PE" and trade.risk_per_share > 0:
                r_achieved = (trade.entry_price - trade.current_sl) / trade.risk_per_share

            if len(trade.targets_hit) > 0:
                last_target = max(trade.targets_hit) + 1
                sl_type = f"TRAILING_SL_AT_T{last_target}" if last_target > 0 else "BREAKEVEN_SL"
            else:
                sl_type = "INITIAL_SL_HIT"

            exit_event = {
                'type': sl_type,
                'qty': sl_exit_qty,
                'price': round(trade.current_sl, 2),
                'new_sl': trade.current_sl,
                'pnl': round(pnl, 2),
                'r_multiple': round(r_achieved, 2),
            }
            exits.append(exit_event)

            trade.remaining_qty = 0
            trade.total_pnl += pnl
            trade.is_closed = True
            trade.close_reason = sl_type

            logger.info(
                f"TSL SL EXIT: {trade.symbol} | {sl_type} | "
                f"Closed {sl_exit_qty} @ {trade.current_sl:.2f} | PnL={pnl:+.2f} | "
                f"Total Trade PnL={trade.total_pnl:+.2f}"
            )

        return exits

    def force_close(self, trade: ManagedTrade, exit_price: float) -> List[Dict]:
        """
        Force close a trade.
        """
        if trade.is_closed or trade.remaining_qty <= 0:
            return []

        qty = trade.remaining_qty

        if trade.direction == "CE":
            pnl = (exit_price - trade.entry_price) * qty
            r_achieved = (exit_price - trade.entry_price) / trade.risk_per_share
        else:
            pnl = (trade.entry_price - exit_price) * qty
            r_achieved = (trade.entry_price - exit_price) / trade.risk_per_share

        exit_event = {
            'type': 'FORCE_CLOSE',
            'qty': qty,
            'price': round(exit_price, 2),
            'new_sl': trade.current_sl,
            'pnl': round(pnl, 2),
            'r_multiple': round(r_achieved, 2),
        }

        trade.remaining_qty = 0
        trade.total_pnl += pnl
        trade.is_closed = True
        trade.close_reason = "FORCE_CLOSE (Market Close)"

        trade.partial_exits.append({
            'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'type': 'FORCE_CLOSE',
            'qty': qty,
            'price': exit_price,
            'pnl': round(pnl, 2),
            'r_multiple': round(r_achieved, 2),
        })

        logger.info(
            f"TSL FORCE CLOSE: {trade.symbol} | Closed {qty} @ {exit_price:.2f} | "
            f"PnL={pnl:+.2f} | Total={trade.total_pnl:+.2f}"
        )

        return [exit_event]
