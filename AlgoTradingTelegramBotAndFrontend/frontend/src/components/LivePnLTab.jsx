import React, { useEffect, useState } from 'react';
import { WSClient } from '../ws';

const LivePnLTab = () => {
  const [pnlData, setPnlData] = useState({
    current_pnl: 0,
    daily_pnl: 0,
    trades_today: 0
  });

  useEffect(() => {
    try {
      const ws = new WSClient('/ws/live-pnl');
      ws.onMessage = (data) => setPnlData(data || {});
      ws.connect();
      return () => ws.close();
    } catch (err) {
      console.error("WebSocket connection error in LivePnLTab:", err);
    }
  }, []);

  return (
    <div className="live-pnl-tab">
      <h2>Live P&L</h2>
      <div className="card">
        <h3>Floating P&L</h3>
        <p className={(pnlData?.current_pnl || 0) >= 0 ? 'green' : 'red'} style={{ fontSize: '2em', fontWeight: 'bold' }}>
          ₹{pnlData?.current_pnl || 0}
        </p>
      </div>
      <div className="card">
        <h3>Daily Stats</h3>
        <div style={{ display: 'flex', gap: '20px' }}>
          <p>PnL: <span style={{ color: (pnlData?.daily_pnl || 0) >= 0 ? '#4caf50' : '#f44336' }}>₹{pnlData?.daily_pnl || 0}</span></p>
          <p>Trades: {pnlData?.trades_today || 0}</p>
        </div>
      </div>

      <div className="card" style={{ marginTop: '20px' }}>
        <h3>Active Positions</h3>
        {(pnlData?.active_trades || []).length > 0 ? (
          <table style={{ width: '100%', borderCollapse: 'collapse', marginTop: '10px' }}>
            <thead>
              <tr style={{ textAlign: 'left', borderBottom: '1px solid #333' }}>
                <th>Symbol</th>
                <th>Dir</th>
                <th>Qty</th>
                <th>Entry</th>
                <th>PnL</th>
              </tr>
            </thead>
            <tbody>
              {pnlData.active_trades.map((t, i) => (
                <tr key={i} style={{ borderBottom: '1px solid #222' }}>
                  <td style={{ padding: '8px 0' }}>{t.symbol}</td>
                  <td>{t.direction}</td>
                  <td>{t.qty}</td>
                  <td>{t.entry}</td>
                  <td style={{ color: t.pnl >= 0 ? '#4caf50' : '#f44336' }}>₹{t.pnl}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p style={{ color: '#787b86', marginTop: '10px' }}>No active positions.</p>
        )}
      </div>
    </div>
  );
};

export default LivePnLTab;
