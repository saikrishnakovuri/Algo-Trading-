Now let me build the comprehensive master MD file. This is a detailed instruction document for Gemini CLI.
Action: file_editor create /app/GEMINI_MASTER_STRATEGY_ENGINE.md --file-text "# MASTER INSTRUCTION FILE — Price Action Strategy Engine Builder

## IDENTITY & MISSION

You are a **Senior Quantitative Developer & Strategy Architect**. Your mission is to systematically read, understand, convert, test, and integrate **all 46-50 price action strategy markdown files** into a unified, production-grade **Price Action Strategy Engine** in Python.

**You will work autonomously through the night. Do NOT stop until every single MD file has been processed, tested, and integrated.**

---

## PHASE 0: ORIENTATION & SETUP

### 0.1 — Root Directory

```
C:\Users\91810\OneDrive\Desktop\AlgoTrading Options\Priceactionmdfiles\
```

### 0.2 — Folder Structure (4 Subfolders)

```
Priceactionmdfiles/
├── ADVANCED PRICE ACTION CONCEPTS/
│   ├── Break of Structure (BOS).md
│   ├── Fair Value Gaps (FVG).md
│   ├── Change of Character (CHOCH).md
│   ├── Higher High & Higher Low.md
│   ├── Liquidity Zones.md
│   ├── Lower High & Lower Low.md
│   ├── Market Structure.md
│   ├── Order Blocks.md
│   └── Supply & Demand.md
│
├── Candlestickpatterns/
│   ├── Bearish Engulfing Pattern.md
│   ├── Bullish Engulfing Pattern.md
│   ├── Dark Cloud Cover Pattern.md
│   ├── Doji Candlestick Pattern.md
│   ├── Evening Star Pattern.md
│   ├── Hammer Candlestick Pattern.md
│   ├── Morning Star Pattern.md
│   ├── Neutral Candlestick Price Action Patterns.md
│   ├── Piercing Pattern.md
│   ├── Shooting Star Pattern.md
│   └── Spinning Top Candlestick Pattern.md
│
├── Price action patterns/
│   ├── Ascending Channel Pattern.md
│   ├── Ascending Triangle Pattern.md
│   ├── Bear Flag Pattern.md
│   ├── Bull Flag Pattern.md
│   ├── Cup and Handle Pattern.md
│   ├── Descending Channel Pattern.md
│   ├── Descending Triangle Pattern.md
│   ├── Double Bottom Pattern.md
│   ├── Double Top Pattern.md
│   ├── Falling Wedge Pattern.md
│   ├── Head and Shoulders Pattern.md
│   ├── Horizontal Channel Pattern.md
│   ├── Inverse Head and Shoulders Pattern.md
│   ├── RECTANGLE ,RANGE PATTERNS.md
│   ├── Rising Wedge Pattern.md
│   ├── Standard Head and Shoulders Pattern.md
│   ├── symmetricaltrianglepattern.md
│   ├── Triple Bottom Pattern.md
│   └── Triple Top Pattern.md
│
└── Support&resistance/
    ├── Breakout → Retest → Continuation.md
    ├── Breakout Trap.md
    ├── Breakout.md
    ├── Fakeout , Liquidity Grab.md
    ├── Resistance Breakout.md
    ├── Resistance.md
    ├── Retest Entry.md
    ├── Support Breakdown.md
    └── Support.md
```

### 0.3 — Output Directory Structure (Create if not exists)

```
Priceactionmdfiles/
├── engine/                          <-- All generated Python files go here
│   ├── advanced_concepts/
│   ├── candlestick_patterns/
│   ├── price_action_patterns/
│   ├── support_resistance/
│   ├── tests/                       <-- All test files go here
│   │   ├── test_advanced_concepts/
│   │   ├── test_candlestick_patterns/
│   │   ├── test_price_action_patterns/
│   │   └── test_support_resistance/
│   ├── strategy_engine.py           <-- The FINAL unified engine
│   ├── strategy_selector.py         <-- Intelligent strategy picker
│   ├── base_strategy.py             <-- Abstract base class
│   ├── signal.py                    <-- Signal/output dataclass
│   └── __init__.py
│
├── building_strategies_using_master_md_file.txt   <-- Progress tracker
└── GEMINI_MASTER_STRATEGY_ENGINE.md               <-- THIS FILE (you are reading it)
```

---

## PHASE 1: FOUNDATION — Build the Base Architecture FIRST

Before processing any MD file, create these foundational files:

### 1.1 — `engine/signal.py`

Create a standardized signal output dataclass:

```python
\"\"\"
Standard signal output for all strategies.
Every strategy MUST return Signal objects.
\"\"\"
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List
from datetime import datetime


class SignalType(Enum):
    BUY = \"BUY\"
    SELL = \"SELL\"
    HOLD = \"HOLD\"
    STRONG_BUY = \"STRONG_BUY\"
    STRONG_SELL = \"STRONG_SELL\"


class MarketBias(Enum):
    BULLISH = \"BULLISH\"
    BEARISH = \"BEARISH\"
    NEUTRAL = \"NEUTRAL\"
    VOLATILE = \"VOLATILE\"


@dataclass
class Signal:
    signal_type: SignalType
    strategy_name: str
    confidence: float              # 0.0 to 1.0
    timeframe: str                 # \"1m\", \"5m\", \"15m\", \"1h\", \"4h\", \"1d\"
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    risk_reward_ratio: Optional[float] = None
    market_bias: MarketBias = MarketBias.NEUTRAL
    reasoning: str = \"\"
    metadata: dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            \"signal\": self.signal_type.value,
            \"strategy\": self.strategy_name,
            \"confidence\": self.confidence,
            \"timeframe\": self.timeframe,
            \"entry\": self.entry_price,
            \"sl\": self.stop_loss,
            \"tp\": self.take_profit,
            \"rr\": self.risk_reward_ratio,
            \"bias\": self.market_bias.value,
            \"reasoning\": self.reasoning,
            \"metadata\": self.metadata,
            \"timestamp\": self.timestamp.isoformat()
        }
```

### 1.2 — `engine/base_strategy.py`

Create an abstract base class that ALL strategies must inherit:

```python
\"\"\"
Abstract Base Strategy — every price action strategy extends this.
\"\"\"
from abc import ABC, abstractmethod
from typing import List, Optional
import pandas as pd
from .signal import Signal, SignalType, MarketBias


class BaseStrategy(ABC):
    \"\"\"
    All strategies MUST implement:
      - name (property)
      - category (property)
      - detect(df, timeframe) -> List[Signal]
    
    Optional overrides:
      - required_candles -> minimum candles needed
      - supported_timeframes -> list of valid timeframes
    \"\"\"

    @property
    @abstractmethod
    def name(self) -> str:
        \"\"\"Human-readable strategy name.\"\"\"
        pass

    @property
    @abstractmethod
    def category(self) -> str:
        \"\"\"One of: 'advanced_concept', 'candlestick', 'price_action_pattern', 'support_resistance'\"\"\"
        pass

    @property
    def required_candles(self) -> int:
        \"\"\"Minimum number of candles needed for detection. Override per strategy.\"\"\"
        return 50

    @property
    def supported_timeframes(self) -> List[str]:
        \"\"\"Timeframes this strategy works on. Override if restricted.\"\"\"
        return [\"1m\", \"5m\", \"15m\", \"1h\", \"4h\", \"1d\"]

    @abstractmethod
    def detect(self, df: pd.DataFrame, timeframe: str = \"15m\") -> List[Signal]:
        \"\"\"
        Core detection method.
        
        Args:
            df: OHLCV DataFrame with columns ['open', 'high', 'low', 'close', 'volume']
                Index should be datetime. Most recent candle is LAST row.
            timeframe: Current chart timeframe string.
        
        Returns:
            List of Signal objects detected in the data.
            Return empty list if no pattern/signal found.
        \"\"\"
        pass

    def validate_dataframe(self, df: pd.DataFrame) -> bool:
        \"\"\"Check that DataFrame has required columns and enough data.\"\"\"
        required_cols = {'open', 'high', 'low', 'close', 'volume'}
        if not required_cols.issubset(set(df.columns)):
            return False
        if len(df) < self.required_candles:
            return False
        return True
```

### 1.3 — Initialize the progress tracker

Create `building_strategies_using_master_md_file.txt` with all strategies listed and empty checkboxes:

```
==============================================================
  PRICE ACTION STRATEGY ENGINE — BUILD PROGRESS TRACKER
  Started: [INSERT TIMESTAMP]
  Status: IN PROGRESS
==============================================================

Legend:
  [ ] = Not started
  [R] = MD file read & understood
  [C] = Python code written
  [T] = Tests written & passing
  [I] = Integrated into engine
  [x] = FULLY COMPLETE (Read + Coded + Tested + Integrated)

--------------------------------------------------------------
SECTION 1: ADVANCED PRICE ACTION CONCEPTS (9 strategies)
--------------------------------------------------------------
[ ] Break of Structure (BOS)
[ ] Fair Value Gaps (FVG)
[ ] Change of Character (CHOCH)
[ ] Higher High & Higher Low
[ ] Liquidity Zones
[ ] Lower High & Lower Low
[ ] Market Structure
[ ] Order Blocks
[ ] Supply & Demand

--------------------------------------------------------------
SECTION 2: CANDLESTICK PATTERNS (11 strategies)
--------------------------------------------------------------
[ ] Bearish Engulfing Pattern
[ ] Bullish Engulfing Pattern
[ ] Dark Cloud Cover Pattern
[ ] Doji Candlestick Pattern
[ ] Evening Star Pattern
[ ] Hammer Candlestick Pattern
[ ] Morning Star Pattern
[ ] Neutral Candlestick Price Action Patterns
[ ] Piercing Pattern
[ ] Shooting Star Pattern
[ ] Spinning Top Candlestick Pattern

--------------------------------------------------------------
SECTION 3: PRICE ACTION PATTERNS (19 strategies)
--------------------------------------------------------------
[ ] Ascending Channel Pattern
[ ] Ascending Triangle Pattern
[ ] Bear Flag Pattern
[ ] Bull Flag Pattern
[ ] Cup and Handle Pattern
[ ] Descending Channel Pattern
[ ] Descending Triangle Pattern
[ ] Double Bottom Pattern
[ ] Double Top Pattern
[ ] Falling Wedge Pattern
[ ] Head and Shoulders Pattern
[ ] Horizontal Channel Pattern
[ ] Inverse Head and Shoulders Pattern
[ ] RECTANGLE, RANGE PATTERNS
[ ] Rising Wedge Pattern
[ ] Standard Head and Shoulders Pattern
[ ] Symmetrical Triangle Pattern
[ ] Triple Bottom Pattern
[ ] Triple Top Pattern

--------------------------------------------------------------
SECTION 4: SUPPORT & RESISTANCE (9 strategies)
--------------------------------------------------------------
[ ] Breakout -> Retest -> Continuation
[ ] Breakout Trap
[ ] Breakout
[ ] Fakeout, Liquidity Grab
[ ] Resistance Breakout
[ ] Resistance
[ ] Retest Entry
[ ] Support Breakdown
[ ] Support

--------------------------------------------------------------
TOTAL: 0 / 48 strategies completed
--------------------------------------------------------------

==============================================================
  DETAILED LOG
==============================================================
[Append detailed logs here as you process each strategy]
```

---

## PHASE 2: THE PROCESSING LOOP — Read, Code, Test, Integrate

**For EACH of the 48 MD files, execute the following steps IN ORDER.**

### STEP 2.1 — READ the MD file

```
ACTION: Open and read the MD file completely.
PATH:   C:\Users\91810\OneDrive\Desktop\AlgoTrading Options\Priceactionmdfiles\{SUBFOLDER}\{FILENAME}.md

EXTRACT:
  - Pattern/concept name
  - Entry conditions (LONG and SHORT)
  - Exit conditions / Stop loss rules
  - Confirmation indicators (if any)
  - Timeframe recommendations
  - Key price levels / zones to identify
  - Visual structure (higher highs, lower lows, breakout levels, etc.)
  - Risk management notes
  - Any edge cases or false signal warnings
```

### STEP 2.2 — WRITE the Python file

```
ACTION: Create a Python file in the correct engine subfolder.
FILE:   engine/{category_folder}/{sanitized_filename}.py

RULES:
  1. Class MUST inherit from BaseStrategy
  2. Class MUST implement: name, category, detect(df, timeframe)
  3. detect() MUST return List[Signal]
  4. Use pandas and numpy ONLY (no TA-Lib unless absolutely necessary)
  5. Include detailed docstrings explaining the strategy logic
  6. Handle edge cases (not enough data, flat market, etc.)
  7. Confidence score (0.0-1.0) based on how many confirmations are met
  8. Calculate entry_price, stop_loss, take_profit where applicable
  9. Include risk_reward_ratio calculation
  10. The file name should match the MD file name with .py extension
      Example: \"Break of Structure (BOS).md\" -> \"break_of_structure_bos.py\"
```

**Python File Template:**

```python
\"\"\"
Strategy: {STRATEGY_NAME}
Category: {CATEGORY}
Source: {MD_FILE_PATH}

Description:
  {Brief description from the MD file}

Entry Conditions:
  LONG: {conditions}
  SHORT: {conditions}

Exit Conditions:
  {conditions}
\"\"\"
import pandas as pd
import numpy as np
from typing import List
from ..base_strategy import BaseStrategy
from ..signal import Signal, SignalType, MarketBias


class {ClassName}(BaseStrategy):
    
    @property
    def name(self) -> str:
        return \"{Strategy Name}\"
    
    @property
    def category(self) -> str:
        return \"{category_string}\"
    
    @property
    def required_candles(self) -> int:
        return {N}  # Based on what this strategy needs
    
    def detect(self, df: pd.DataFrame, timeframe: str = \"15m\") -> List[Signal]:
        if not self.validate_dataframe(df):
            return []
        
        signals = []
        # ... FULL IMPLEMENTATION based on MD file logic ...
        return signals
```

### STEP 2.3 — WRITE Tests

```
ACTION: Create test file in engine/tests/{test_category_folder}/
FILE:   test_{sanitized_filename}.py

TEST TYPES TO INCLUDE:

1. SMOKE TESTS (Does it run at all?)
   - Can the class be instantiated?
   - Does detect() return a list?
   - Does it handle empty DataFrame without crashing?
   - Does it handle DataFrame with insufficient rows?

2. UNIT TESTS (Does the logic work?)
   - Feed known bullish pattern data -> expect BUY signal
   - Feed known bearish pattern data -> expect SELL signal
   - Feed flat/no-pattern data -> expect HOLD or empty list
   - Verify confidence score is between 0.0 and 1.0
   - Verify stop_loss is set correctly relative to entry
   - Verify take_profit is set correctly relative to entry
   - Verify risk_reward_ratio calculation

3. EDGE CASE TESTS (Does it handle weird inputs?)
   - All same price candles (flat line)
   - Extreme volatility (huge wicks)
   - Single candle DataFrame
   - Missing volume data (should still work or gracefully fail)
   - NaN values in DataFrame

4. INTEGRATION READINESS TESTS
   - Does the class properly inherit BaseStrategy?
   - Does it have all required properties (name, category)?
   - Are returned Signals valid Signal objects?
   - Does to_dict() work on returned signals?
```

**Test Template:**

```python
\"\"\"Tests for {Strategy Name}\"\"\"
import pytest
import pandas as pd
import numpy as np
from engine.{category}.{module_name} import {ClassName}
from engine.signal import Signal, SignalType


@pytest.fixture
def strategy():
    return {ClassName}()


@pytest.fixture
def sample_bullish_df():
    \"\"\"Create a DataFrame that should trigger a bullish signal.\"\"\"
    # ... Generate realistic OHLCV data showing the pattern ...
    pass


@pytest.fixture
def sample_bearish_df():
    \"\"\"Create a DataFrame that should trigger a bearish signal.\"\"\"
    pass


@pytest.fixture
def sample_flat_df():
    \"\"\"Create a flat/no-pattern DataFrame.\"\"\"
    pass


class TestSmoke:
    def test_instantiation(self, strategy):
        assert strategy is not None
        assert strategy.name != \"\"
        assert strategy.category != \"\"

    def test_detect_returns_list(self, strategy, sample_flat_df):
        result = strategy.detect(sample_flat_df)
        assert isinstance(result, list)

    def test_handles_empty_df(self, strategy):
        empty_df = pd.DataFrame(columns=['open', 'high', 'low', 'close', 'volume'])
        result = strategy.detect(empty_df)
        assert result == []


class TestDetection:
    def test_bullish_detection(self, strategy, sample_bullish_df):
        signals = strategy.detect(sample_bullish_df)
        assert len(signals) > 0
        assert any(s.signal_type in [SignalType.BUY, SignalType.STRONG_BUY] for s in signals)

    def test_bearish_detection(self, strategy, sample_bearish_df):
        signals = strategy.detect(sample_bearish_df)
        assert len(signals) > 0
        assert any(s.signal_type in [SignalType.SELL, SignalType.STRONG_SELL] for s in signals)

    def test_confidence_range(self, strategy, sample_bullish_df):
        signals = strategy.detect(sample_bullish_df)
        for s in signals:
            assert 0.0 <= s.confidence <= 1.0


class TestEdgeCases:
    def test_flat_market(self, strategy, sample_flat_df):
        signals = strategy.detect(sample_flat_df)
        # Should return HOLD or empty — no false signals
        for s in signals:
            assert s.signal_type == SignalType.HOLD

    def test_insufficient_data(self, strategy):
        small_df = pd.DataFrame({
            'open': [100], 'high': [101], 'low': [99],
            'close': [100.5], 'volume': [1000]
        })
        result = strategy.detect(small_df)
        assert result == []
```

### STEP 2.4 — RUN Tests & Fix

```
ACTION: Run the tests for this specific strategy.
COMMAND: pytest engine/tests/{test_category_folder}/test_{filename}.py -v

IF TESTS FAIL:
  1. Read the error output carefully
  2. Fix the strategy code (NOT the tests, unless test logic is wrong)
  3. Re-run tests
  4. Repeat until ALL tests pass

DO NOT move to the next strategy until ALL tests for the current one pass.
```

### STEP 2.5 — Update Progress Tracker

```
ACTION: Open building_strategies_using_master_md_file.txt
UPDATE: Change the checkbox for this strategy from [ ] to [x]
APPEND to DETAILED LOG section:

[TIMESTAMP] {Strategy Name}
  - MD File: {path}
  - Python File: engine/{path}.py
  - Test File: engine/tests/{path}.py
  - Tests Run: {N} total | {N} passed | {N} failed
  - Status: COMPLETE ✅
  - Notes: {any observations, edge cases found, etc.}
```

### STEP 2.6 — Return to this master file, find the NEXT MD file, REPEAT from Step 2.1

---

## PROCESSING ORDER

Process strategies in this EXACT order (folder by folder):

### Batch 1: ADVANCED PRICE ACTION CONCEPTS
Process these FIRST because other strategies depend on these concepts:

```
1.  C:\...\ADVANCED PRICE ACTION CONCEPTS\Market Structure.md
2.  C:\...\ADVANCED PRICE ACTION CONCEPTS\Higher High & Higher Low.md
3.  C:\...\ADVANCED PRICE ACTION CONCEPTS\Lower High & Lower Low.md
4.  C:\...\ADVANCED PRICE ACTION CONCEPTS\Break of Structure (BOS).md
5.  C:\...\ADVANCED PRICE ACTION CONCEPTS\Change of Character (CHOCH).md
6.  C:\...\ADVANCED PRICE ACTION CONCEPTS\Order Blocks.md
7.  C:\...\ADVANCED PRICE ACTION CONCEPTS\Fair Value Gaps (FVG).md
8.  C:\...\ADVANCED PRICE ACTION CONCEPTS\Supply & Demand.md
9.  C:\...\ADVANCED PRICE ACTION CONCEPTS\Liquidity Zones.md
```

### Batch 2: CANDLESTICK PATTERNS
These are self-contained pattern recognizers:

```
10. C:\...\Candlestickpatterns\Doji Candlestick Pattern.md
11. C:\...\Candlestickpatterns\Hammer Candlestick Pattern.md
12. C:\...\Candlestickpatterns\Shooting Star Pattern.md
13. C:\...\Candlestickpatterns\Spinning Top Candlestick Pattern.md
14. C:\...\Candlestickpatterns\Bullish Engulfing Pattern.md
15. C:\...\Candlestickpatterns\Bearish Engulfing Pattern.md
16. C:\...\Candlestickpatterns\Morning Star Pattern.md
17. C:\...\Candlestickpatterns\Evening Star Pattern.md
18. C:\...\Candlestickpatterns\Piercing Pattern.md
19. C:\...\Candlestickpatterns\Dark Cloud Cover Pattern.md
20. C:\...\Candlestickpatterns\Neutral Candlestick Price Action Patterns.md
```

### Batch 3: PRICE ACTION PATTERNS
Chart patterns — these may reference advanced concepts:

```
21. C:\...\Price action patterns\Double Bottom Pattern.md
22. C:\...\Price action patterns\Double Top Pattern.md
23. C:\...\Price action patterns\Triple Bottom Pattern.md
24. C:\...\Price action patterns\Triple Top Pattern.md
25. C:\...\Price action patterns\Head and Shoulders Pattern.md
26. C:\...\Price action patterns\Standard Head and Shoulders Pattern.md
27. C:\...\Price action patterns\Inverse Head and Shoulders Pattern.md
28. C:\...\Price action patterns\Ascending Triangle Pattern.md
29. C:\...\Price action patterns\Descending Triangle Pattern.md
30. C:\...\Price action patterns\symmetricaltrianglepattern.md
31. C:\...\Price action patterns\Bull Flag Pattern.md
32. C:\...\Price action patterns\Bear Flag Pattern.md
33. C:\...\Price action patterns\Ascending Channel Pattern.md
34. C:\...\Price action patterns\Descending Channel Pattern.md
35. C:\...\Price action patterns\Horizontal Channel Pattern.md
36. C:\...\Price action patterns\Cup and Handle Pattern.md
37. C:\...\Price action patterns\Rising Wedge Pattern.md
38. C:\...\Price action patterns\Falling Wedge Pattern.md
39. C:\...\Price action patterns\RECTANGLE ,RANGE PATTERNS.md
```

### Batch 4: SUPPORT & RESISTANCE
These are the tactical execution strategies:

```
40. C:\...\Support&resistance\Support.md
41. C:\...\Support&resistance\Resistance.md
42. C:\...\Support&resistance\Breakout.md
43. C:\...\Support&resistance\Resistance Breakout.md
44. C:\...\Support&resistance\Support Breakdown.md
45. C:\...\Support&resistance\Breakout → Retest → Continuation.md
46. C:\...\Support&resistance\Retest Entry.md
47. C:\...\Support&resistance\Breakout Trap.md
48. C:\...\Support&resistance\Fakeout , Liquidity Grab.md
```

---

## PHASE 3: BUILD THE UNIFIED STRATEGY ENGINE

After ALL 48 strategies are coded and tested, build the master engine.

### 3.1 — `engine/strategy_registry.py`

```python
\"\"\"
Strategy Registry — Auto-discovers and registers all strategies.
\"\"\"
from typing import Dict, List, Type
from .base_strategy import BaseStrategy


class StrategyRegistry:
    \"\"\"Central registry of all available strategies.\"\"\"
    
    _strategies: Dict[str, BaseStrategy] = {}
    
    @classmethod
    def register(cls, strategy_class: Type[BaseStrategy]):
        \"\"\"Register a strategy class.\"\"\"
        instance = strategy_class()
        cls._strategies[instance.name] = instance
        return strategy_class
    
    @classmethod
    def get_all(cls) -> Dict[str, BaseStrategy]:
        return cls._strategies
    
    @classmethod
    def get_by_category(cls, category: str) -> List[BaseStrategy]:
        return [s for s in cls._strategies.values() if s.category == category]
    
    @classmethod
    def get_by_name(cls, name: str) -> BaseStrategy:
        return cls._strategies.get(name)
    
    @classmethod
    def get_names(cls) -> List[str]:
        return list(cls._strategies.keys())
```

### 3.2 — `engine/strategy_selector.py` — The Brain

This is the INTELLIGENT strategy selector. It analyzes market conditions and picks the best strategies:

```python
\"\"\"
Strategy Selector — The Brain of the Engine.

Analyzes current market conditions and selects the most appropriate
strategies to run. This avoids running all 48 strategies blindly.

Selection Logic:
  1. Determine market regime (trending up, trending down, ranging, volatile)
  2. Check timeframe compatibility
  3. Score strategy relevance for current conditions
  4. Return top-N most relevant strategies
  5. Run them and aggregate signals
\"\"\"
import pandas as pd
import numpy as np
from typing import List, Tuple, Optional
from .base_strategy import BaseStrategy
from .strategy_registry import StrategyRegistry
from .signal import Signal, SignalType, MarketBias


class MarketRegime:
    \"\"\"Detect current market regime from price data.\"\"\"
    
    @staticmethod
    def detect(df: pd.DataFrame) -> dict:
        \"\"\"
        Returns market regime analysis:
        {
            'trend': 'uptrend' | 'downtrend' | 'sideways',
            'volatility': 'low' | 'medium' | 'high',
            'momentum': float (-1 to 1),
            'strength': float (0 to 1),
            'recent_bos': bool,
            'at_support': bool,
            'at_resistance': bool
        }
        \"\"\"
        # Implementation: Use ADX, ATR, moving averages, recent swing structure
        pass


class StrategySelector:
    \"\"\"
    Intelligent strategy selector that picks the right tools for the job.
    \"\"\"
    
    # Strategy relevance mapping per market condition
    REGIME_STRATEGY_MAP = {
        'uptrend': {
            'preferred': [
                'candlestick',           # Continuation patterns
                'price_action_pattern',   # Bull flags, ascending triangles
                'support_resistance',     # Breakout entries
            ],
            'boost_strategies': [
                'Bull Flag Pattern', 'Ascending Triangle Pattern',
                'Ascending Channel Pattern', 'Cup and Handle Pattern',
                'Bullish Engulfing Pattern', 'Morning Star Pattern',
                'Hammer Candlestick Pattern', 'Breakout',
                'Higher High & Higher Low', 'Break of Structure (BOS)',
            ]
        },
        'downtrend': {
            'preferred': [
                'candlestick',
                'price_action_pattern',
                'support_resistance',
            ],
            'boost_strategies': [
                'Bear Flag Pattern', 'Descending Triangle Pattern',
                'Descending Channel Pattern', 'Bearish Engulfing Pattern',
                'Evening Star Pattern', 'Shooting Star Pattern',
                'Support Breakdown', 'Lower High & Lower Low',
                'Change of Character (CHOCH)',
            ]
        },
        'sideways': {
            'preferred': [
                'support_resistance',
                'advanced_concept',
                'candlestick',
            ],
            'boost_strategies': [
                'Horizontal Channel Pattern', 'RECTANGLE, RANGE PATTERNS',
                'Double Bottom Pattern', 'Double Top Pattern',
                'Support', 'Resistance', 'Fakeout, Liquidity Grab',
                'Order Blocks', 'Supply & Demand', 'Liquidity Zones',
                'Retest Entry', 'Breakout Trap',
            ]
        }
    }
    
    def select_strategies(
        self,
        df: pd.DataFrame,
        timeframe: str = \"15m\",
        max_strategies: int = 15,
        market_type: Optional[str] = None
    ) -> List[BaseStrategy]:
        \"\"\"
        Select the most relevant strategies for current market conditions.
        
        Args:
            df: OHLCV DataFrame
            timeframe: Current timeframe
            max_strategies: Maximum strategies to run
            market_type: Override auto-detection ('uptrend', 'downtrend', 'sideways')
        
        Returns:
            Ranked list of strategies to execute
        \"\"\"
        pass
    
    def run_selected(
        self,
        df: pd.DataFrame,
        timeframe: str = \"15m\",
        max_strategies: int = 15,
        market_type: Optional[str] = None
    ) -> List[Signal]:
        \"\"\"
        Select strategies AND run them. Returns aggregated signals.
        \"\"\"
        pass


class SignalAggregator:
    \"\"\"
    Aggregates signals from multiple strategies into a final recommendation.
    
    Confluence Logic:
      - Multiple strategies agreeing = higher confidence
      - Conflicting signals = reduce confidence or HOLD
      - Weight by strategy category relevance to current regime
    \"\"\"
    
    @staticmethod
    def aggregate(signals: List[Signal], regime: dict) -> Signal:
        \"\"\"
        Produce a single final signal from multiple strategy outputs.
        
        Scoring:
          - Each BUY signal adds +confidence to bull score
          - Each SELL signal adds +confidence to bear score
          - Strategies matching current regime get 1.5x weight
          - Final signal = direction with highest weighted score
          - Final confidence = (winning_score - losing_score) / total_score
        \"\"\"
        pass
```

### 3.3 — `engine/strategy_engine.py` — The Main Entry Point

```python
\"\"\"
PRICE ACTION STRATEGY ENGINE
============================
The unified entry point for all price action analysis.

Usage:
    from engine.strategy_engine import PriceActionEngine
    
    engine = PriceActionEngine()
    
    # Auto-select and run best strategies
    result = engine.analyze(df, timeframe=\"15m\")
    
    # Run specific category
    result = engine.analyze(df, category=\"candlestick\")
    
    # Run specific strategy
    result = engine.run_strategy(\"Double Bottom Pattern\", df)
    
    # Get detailed report
    report = engine.full_report(df, timeframe=\"15m\")

Integration with existing trading bot:
    The engine exposes a simple API:
    - engine.analyze(df) -> Signal (single best recommendation)
    - engine.get_all_signals(df) -> List[Signal] (all detected patterns)
    - engine.full_report(df) -> dict (comprehensive analysis)
    
    Connect this to your existing strategy engine by:
    1. Importing PriceActionEngine
    2. Feeding it your OHLCV data
    3. Using the returned Signal objects for trade decisions
\"\"\"
import pandas as pd
from typing import List, Optional, Dict
from .strategy_registry import StrategyRegistry
from .strategy_selector import StrategySelector, SignalAggregator, MarketRegime
from .signal import Signal, SignalType
from .base_strategy import BaseStrategy

# Import all strategy modules to trigger registration
from .advanced_concepts import *
from .candlestick_patterns import *
from .price_action_patterns import *
from .support_resistance import *


class PriceActionEngine:
    \"\"\"
    Main engine that orchestrates all price action strategies.
    
    Features:
      - Intelligent strategy selection based on market regime
      - Confluence-based signal aggregation
      - Configurable for different timeframes and market types
      - Detailed reporting with reasoning
      - Easy integration with existing trading bots
    \"\"\"
    
    def __init__(self):
        self.registry = StrategyRegistry
        self.selector = StrategySelector()
        self.aggregator = SignalAggregator()
        self.regime_detector = MarketRegime()
    
    def analyze(
        self,
        df: pd.DataFrame,
        timeframe: str = \"15m\",
        market_type: Optional[str] = None
    ) -> Signal:
        \"\"\"
        PRIMARY METHOD — Analyze price data and return best signal.
        
        This is what your trading bot should call.
        
        Args:
            df: OHLCV DataFrame (columns: open, high, low, close, volume)
            timeframe: \"1m\", \"5m\", \"15m\", \"1h\", \"4h\", \"1d\"
            market_type: Optional override for market regime
        
        Returns:
            Single Signal object with the best recommendation
        \"\"\"
        pass
    
    def get_all_signals(
        self,
        df: pd.DataFrame,
        timeframe: str = \"15m\"
    ) -> List[Signal]:
        \"\"\"
        Run ALL strategies and return every signal found.
        Useful for debugging and analysis.
        \"\"\"
        pass
    
    def run_strategy(
        self,
        strategy_name: str,
        df: pd.DataFrame,
        timeframe: str = \"15m\"
    ) -> List[Signal]:
        \"\"\"Run a specific strategy by name.\"\"\"
        pass
    
    def run_category(
        self,
        category: str,
        df: pd.DataFrame,
        timeframe: str = \"15m\"
    ) -> List[Signal]:
        \"\"\"Run all strategies in a category.\"\"\"
        pass
    
    def full_report(
        self,
        df: pd.DataFrame,
        timeframe: str = \"15m\"
    ) -> Dict:
        \"\"\"
        Generate comprehensive analysis report.
        
        Returns:
        {
            \"timestamp\": \"...\",
            \"timeframe\": \"15m\",
            \"market_regime\": { ... },
            \"final_signal\": { ... },
            \"strategies_run\": 15,
            \"total_signals\": 8,
            \"bullish_signals\": [ ... ],
            \"bearish_signals\": [ ... ],
            \"neutral_signals\": [ ... ],
            \"confluence_score\": 0.72,
            \"top_strategies\": [ ... ],
            \"detailed_signals\": [ ... ],
            \"reasoning\": \"Strong bullish confluence: 6 of 8 signals bullish with avg confidence 0.78...\"
        }
        \"\"\"
        pass
    
    def list_strategies(self) -> Dict[str, List[str]]:
        \"\"\"List all available strategies grouped by category.\"\"\"
        pass

    # =========================================================
    # INTEGRATION HELPERS — Connect to your existing trading bot
    # =========================================================
    
    def connect_to_bot(self, bot_interface):
        \"\"\"
        Connect this engine to an existing trading bot.
        
        Expected bot_interface methods:
          - bot.get_ohlcv(symbol, timeframe, limit) -> pd.DataFrame
          - bot.place_order(signal: Signal) -> order_id
          - bot.get_position(symbol) -> position_info
        
        If your bot has a different interface, adapt this method.
        \"\"\"
        self.bot = bot_interface
    
    def auto_analyze_symbol(self, symbol: str, timeframe: str = \"15m\"):
        \"\"\"
        If connected to a bot, fetch data and analyze automatically.
        \"\"\"
        if not hasattr(self, 'bot'):
            raise RuntimeError(\"No bot connected. Call connect_to_bot() first.\")
        df = self.bot.get_ohlcv(symbol, timeframe, limit=200)
        return self.analyze(df, timeframe)
```

---

## PHASE 4: INTEGRATION TESTING

After building the engine, run comprehensive integration tests:

### 4.1 — Test Strategy Registration
```
- All 48 strategies are registered in the registry
- Each has a unique name
- Categories are correct
- No import errors
```

### 4.2 — Test Strategy Selection
```
- Uptrend data -> bullish strategies selected
- Downtrend data -> bearish strategies selected
- Sideways data -> range-bound strategies selected
- Timeframe filtering works
```

### 4.3 — Test Signal Aggregation
```
- Multiple BUY signals -> aggregated BUY with high confidence
- Mixed signals -> reduced confidence or HOLD
- Single strategy signal -> passed through correctly
```

### 4.4 — Test Full Pipeline
```
- Feed realistic OHLCV data through engine.analyze()
- Verify Signal object is valid
- Verify full_report() returns complete dict
- Test with multiple timeframes
- Test with different market conditions
```

### 4.5 — Performance Test
```
- engine.analyze() completes in < 2 seconds for 500 candles
- All 48 strategies run in < 10 seconds
- No memory leaks on repeated calls
```

---

## PHASE 5: FINAL OUTPUT & REPORTING

### 5.1 — Update Progress Tracker

The `building_strategies_using_master_md_file.txt` should now show:

```
TOTAL: 48 / 48 strategies completed ✅

ENGINE STATUS: COMPLETE ✅
  - strategy_engine.py: BUILT & TESTED
  - strategy_selector.py: BUILT & TESTED
  - signal_aggregator: BUILT & TESTED
  - All integration tests: PASSING
```

### 5.2 — Generate Final Summary Report

Create `engine/FINAL_REPORT.md` with:

```markdown
# Price Action Strategy Engine — Final Report

## Summary
- Total strategies implemented: 48
- Total test cases: {N}
- All tests passing: Yes/No
- Engine status: OPERATIONAL

## Strategy Breakdown
| Category | Count | All Tests Pass |
|----------|-------|----------------|
| Advanced Concepts | 9 | ✅ |
| Candlestick Patterns | 11 | ✅ |
| Price Action Patterns | 19 | ✅ |
| Support & Resistance | 9 | ✅ |

## Quick Start
```python
from engine.strategy_engine import PriceActionEngine
engine = PriceActionEngine()
signal = engine.analyze(your_ohlcv_dataframe, timeframe=\"15m\")
print(signal.to_dict())
```

## Integration with Your Trading Bot
{Instructions on how to connect to existing bot}

## Known Limitations
{Any strategies that couldn't be fully automated}

## Recommendations
{Suggestions for improvement, backtesting, etc.}
```

---

## CRITICAL RULES — DO NOT VIOLATE

1. **DO NOT SKIP ANY MD FILE.** Process ALL 48 files. Every. Single. One.
2. **DO NOT move to the next file** until the current one is coded AND tested AND passing.
3. **DO NOT write placeholder/stub code.** Every `detect()` method must have REAL implementation logic extracted from the MD file.
4. **DO NOT hardcode signals.** Detection must be based on actual price data analysis.
5. **UPDATE the progress tracker** after EVERY strategy. This is your checkpoint system.
6. **If a test fails**, fix the code, don't delete the test.
7. **If an MD file is ambiguous**, implement the most common/standard interpretation of that pattern and document your assumptions.
8. **Confidence scores MUST be meaningful** — higher confidence = more confirmations met.
9. **ALWAYS include stop_loss and take_profit** where the strategy logic allows.
10. **The engine MUST be importable** and usable with a single import statement.

---

## EMERGENCY RECOVERY

If you crash, get disconnected, or need to resume:

1. Open `building_strategies_using_master_md_file.txt`
2. Find the LAST strategy marked with `[x]`
3. Start from the NEXT unmarked strategy
4. Continue the loop

---

## QUICK REFERENCE — File Naming Convention

| MD File Name | Python Module Name |
|---|---|
| Break of Structure (BOS).md | break_of_structure_bos.py |
| Fair Value Gaps (FVG).md | fair_value_gaps_fvg.py |
| Change of Character (CHOCH).md | change_of_character_choch.py |
| Higher High & Higher Low.md | higher_high_and_higher_low.py |
| Liquidity Zones.md | liquidity_zones.py |
| Lower High & Lower Low.md | lower_high_and_lower_low.py |
| Market Structure.md | market_structure.py |
| Order Blocks.md | order_blocks.py |
| Supply & Demand.md | supply_and_demand.py |
| Bearish Engulfing Pattern.md | bearish_engulfing_pattern.py |
| Bullish Engulfing Pattern.md | bullish_engulfing_pattern.py |
| Dark Cloud Cover Pattern.md | dark_cloud_cover_pattern.py |
| Doji Candlestick Pattern.md | doji_candlestick_pattern.py |
| Evening Star Pattern.md | evening_star_pattern.py |
| Hammer Candlestick Pattern.md | hammer_candlestick_pattern.py |
| Morning Star Pattern.md | morning_star_pattern.py |
| Neutral Candlestick Price Action Patterns.md | neutral_candlestick_price_action_patterns.py |
| Piercing Pattern.md | piercing_pattern.py |
| Shooting Star Pattern.md | shooting_star_pattern.py |
| Spinning Top Candlestick Pattern.md | spinning_top_candlestick_pattern.py |
| Ascending Channel Pattern.md | ascending_channel_pattern.py |
| Ascending Triangle Pattern.md | ascending_triangle_pattern.py |
| Bear Flag Pattern.md | bear_flag_pattern.py |
| Bull Flag Pattern.md | bull_flag_pattern.py |
| Cup and Handle Pattern.md | cup_and_handle_pattern.py |
| Descending Channel Pattern.md | descending_channel_pattern.py |
| Descending Triangle Pattern.md | descending_triangle_pattern.py |
| Double Bottom Pattern.md | double_bottom_pattern.py |
| Double Top Pattern.md | double_top_pattern.py |
| Falling Wedge Pattern.md | falling_wedge_pattern.py |
| Head and Shoulders Pattern.md | head_and_shoulders_pattern.py |
| Horizontal Channel Pattern.md | horizontal_channel_pattern.py |
| Inverse Head and Shoulders Pattern.md | inverse_head_and_shoulders_pattern.py |
| RECTANGLE ,RANGE PATTERNS.md | rectangle_range_patterns.py |
| Rising Wedge Pattern.md | rising_wedge_pattern.py |
| Standard Head and Shoulders Pattern.md | standard_head_and_shoulders_pattern.py |
| symmetricaltrianglepattern.md | symmetrical_triangle_pattern.py |
| Triple Bottom Pattern.md | triple_bottom_pattern.py |
| Triple Top Pattern.md | triple_top_pattern.py |
| Breakout -> Retest -> Continuation.md | breakout_retest_continuation.py |
| Breakout Trap.md | breakout_trap.py |
| Breakout.md | breakout.py |
| Fakeout , Liquidity Grab.md | fakeout_liquidity_grab.py |
| Resistance Breakout.md | resistance_breakout.py |
| Resistance.md | resistance.py |
| Retest Entry.md | retest_entry.py |
| Support Breakdown.md | support_breakdown.py |
| Support.md | support.py |

---

## YOU HAVE YOUR ORDERS. BEGIN WITH PHASE 0. DO NOT STOP UNTIL PHASE 5 IS COMPLETE.

**Start time: [GEMINI INSERTS TIMESTAMP]**
**Target: ALL 48 strategies processed, tested, integrated, and engine operational.**

GO.
"
Observation: Create successful: /app/GEMINI_MASTER_STRATEGY_ENGINE.md