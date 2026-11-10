import React, { useState, useEffect } from 'react';
import { api } from '../api';

const RiskGuardTab = () => {
  const [state, setState] = useState({
    daily_pnl: 0,
    trades_today: 0,
    consecutive_losses: 0
  });

  useEffect(() => {
    const fetchState = async () => {
      try {
        const data = await api.riskguard.state();
        setState(data || {});
      } catch (err) {
        console.error("Failed to fetch RiskGuard state:", err);
      }
    };
    fetchState();
  }, []);

  const handleReset = async () => {
    try {
      await api.riskguard.reset();
      alert("RiskGuard state reset!");
      // Refresh state
      const data = await api.riskguard.state();
      setState(data || {});
    } catch (err) {
      alert("Failed to reset: " + err.message);
    }
  };

  return (
    <div className="riskguard-tab">
      <h2 style={{ color: 'white' }}>RiskGuard State</h2>
      <div className="card">
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', fontSize: '1.1em' }}>
          <p>Daily PnL: <span style={{ color: (state?.daily_pnl || 0) >= 0 ? '#4caf50' : '#f44336', fontWeight: 'bold' }}>₹{state?.daily_pnl || 0}</span></p>
          <p>Trades Today: <span style={{ color: '#00bcd4', fontWeight: 'bold' }}>{state?.trades_today || 0}</span></p>
          <p>Consecutive Losses: <span style={{ color: (state?.consecutive_losses || 0) > 2 ? '#f44336' : '#787b86' }}>{state?.consecutive_losses || 0}</span></p>
        </div>
        <div style={{ marginTop: '20px' }}>
          <button className="danger" onClick={handleReset} style={{ padding: '10px 20px', fontWeight: 'bold' }}>
            RESET RISK LIMITS
          </button>
        </div>
      </div>
      
      <div className="card" style={{ marginTop: '20px', borderLeft: '4px solid #f44336' }}>
        <h3 style={{ color: '#f44336' }}>Active Restrictions</h3>
        <p style={{ color: '#787b86' }}>
          {(state?.trades_today || 0) >= 4 ? 'MAX TRADES REACHED' : 'No active trade-count restrictions.'}
        </p>
      </div>
    </div>
  );
};

export default RiskGuardTab;
