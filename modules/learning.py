import sqlite3
import os
import json
from datetime import datetime
import pandas as pd
from typing import Dict, Any, List, Optional

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'trades.db')

class LearningSystem:
    """
    Module 7: Meta-Learning Engine
    Handles trade persistence, LLM forensics, and feedback-driven confidence adjustments.
    """
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self._ensure_db()

    def _ensure_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT,
                    symbol TEXT,
                    direction TEXT,
                    setup_type TEXT,
                    entry REAL,
                    sl REAL,
                    t1 REAL,
                    t2 REAL,
                    confidence INTEGER,
                    score REAL,
                    regime TEXT,
                    reason TEXT,
                    result TEXT,
                    pnl REAL,
                    r_multiple REAL,
                    trade_dna TEXT,        -- JSON blob of all module scores/states
                    llm_feedback TEXT,     -- Analysis from LLM
                    resolution TEXT,       -- Actionable fix (e.g., "Skip in Low Vol")
                    meta TEXT
                )
            ''')
            
            # Check if new columns exist (migration for existing DBs)
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(trades)")
            columns = [info[1] for row, info in enumerate(cursor.fetchall())]
            
            new_cols = {
                "symbol": "TEXT", "direction": "TEXT", "setup_type": "TEXT", 
                "score": "REAL", "regime": "TEXT", "r_multiple": "REAL",
                "trade_dna": "TEXT", "llm_feedback": "TEXT", "resolution": "TEXT"
            }
            
            for col, col_type in new_cols.items():
                if col not in columns:
                    conn.execute(f"ALTER TABLE trades ADD COLUMN {col} {col_type}")

    def log_trade(self, trade_data: Dict[str, Any], dna: Dict[str, Any]):
        """
        Records the start of a trade with its full 'DNA'.
        """
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute('''
                INSERT INTO trades (
                    ts, symbol, direction, setup_type, entry, sl, t1, t2, 
                    confidence, score, regime, reason, result, trade_dna, meta
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                datetime.utcnow().isoformat(),
                trade_data.get('symbol'),
                trade_data.get('direction'),
                trade_data.get('setup_type'),
                trade_data.get('entry'),
                trade_data.get('sl'),
                trade_data.get('target1'),
                trade_data.get('target2'),
                int(trade_data.get('confidence') or 0),
                trade_data.get('score'),
                trade_data.get('regime'),
                trade_data.get('reason'),
                'OPEN',
                json.dumps(dna),
                json.dumps(trade_data.get('meta') or {})
            ))
            return cur.lastrowid

    def update_trade_outcome(self, trade_id: int, result: str, pnl: float, r_multiple: float):
        """Updates trade results upon exit."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                UPDATE trades SET result = ?, pnl = ?, r_multiple = ? WHERE id = ?
            ''', (result, pnl, r_multiple, trade_id))

    def add_llm_forensics(self, trade_id: int, feedback: str, resolution: str):
        """Stores LLM generated analysis and future resolution."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                UPDATE trades SET llm_feedback = ?, resolution = ? WHERE id = ?
            ''', (feedback, resolution, trade_id))

    def get_similar_feedback(self, setup_type: str, symbol: str, regime: str, limit: int = 5) -> pd.DataFrame:
        """
        The 'Mirror' Check: Returns recent performance and feedback for this setup.
        """
        query = """
            SELECT result, llm_feedback, resolution, r_multiple 
            FROM trades 
            WHERE setup_type = ? AND (symbol = ? OR regime = ?) AND result != 'OPEN'
            ORDER BY ts DESC LIMIT ?
        """
        with sqlite3.connect(self.db_path) as conn:
            return pd.read_sql_query(query, conn, params=(setup_type, symbol, regime, limit))

    def get_stats(self):
        with sqlite3.connect(self.db_path) as conn:
            df = pd.read_sql_query("SELECT result, pnl FROM trades", conn)
        if df.empty: return {'total_trades': 0, 'wins': 0, 'win_rate': 0, 'pnl': 0}
        
        total = len(df)
        wins = len(df[df['result'] == 'win'])
        pnl = df['pnl'].sum()
        return {
            'total_trades': total,
            'wins': wins,
            'win_rate': (wins / total * 100) if total > 0 else 0,
            'pnl': pnl
        }
