import React, { useEffect, useState } from 'react';
import { api } from '../api';

const TradesTab = () => {
  const [trades, setTrades] = useState([]);

  useEffect(() => {
    const fetchTrades = async () => {
      try {
        const data = await api.trades.history();
        setTrades(data?.trades || []);
      } catch (err) {
        console.error("Failed to fetch trade history:", err);
        setTrades([]);
      }
    };
    fetchTrades();
  }, []);

  return (
    <div className="trades-tab">
      <h2>Trade History</h2>
      {trades && trades.length > 0 ? (
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ textAlign: 'left', borderBottom: '2px solid #333' }}>
              <th style={{ padding: '10px' }}>ID</th>
              <th>Symbol</th>
              <th>Dir</th>
              <th>Entry</th>
              <th>Exit</th>
              <th>PnL</th>
              <th>Reason</th>
              <th>Time</th>
            </tr>
          </thead>
          <tbody>
            {trades.map((t) => (
              <tr key={t.trade_id} style={{ borderBottom: '1px solid #333' }}>
                <td style={{ padding: '10px' }}>{t.trade_id}</td>
                <td>{t.symbol}</td>
                <td>{t.direction}</td>
                <td>{t.entry_price}</td>
                <td>{t.exit_price || '-'}</td>
                <td style={{ color: (t.pnl || 0) >= 0 ? '#4caf50' : '#f44336' }}>{t.pnl || '-'}</td>
                <td>{t.reason || t.exit_reason || '-'}</td>
                <td>{t.entry_time}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <p style={{ color: '#787b86' }}>No trade history found.</p>
      )}
    </div>
  );
};

export default TradesTab;
