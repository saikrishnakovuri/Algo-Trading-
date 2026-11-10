import React, { useState, useEffect } from 'react';
import { api } from '../api';

const BacktestTab = () => {
  const [config, setConfig] = useState({
    start_date: '2025-11-01',
    end_date: '2026-04-30',
    symbol: 'NIFTY',
    capital: 100000,
    risk_pct: 1.0
  });
  const [history, setHistory] = useState([]);

  useEffect(() => {
    const fetchHistory = async () => {
      try {
        const data = await api.backtest.history();
        setHistory(data?.history || []);
      } catch (err) {
        console.error("Failed to fetch backtest history:", err);
        setHistory([]);
      }
    };
    fetchHistory();
  }, []);

  const runBacktest = async () => {
    try {
      await api.backtest.run(config);
      alert("Backtest started!");
    } catch (err) {
      alert("Failed to start backtest: " + err.message);
    }
  };

  return (
    <div className="backtest-tab">
      <h2>Backtesting</h2>
      <div className="card">
        <h3>Run New Backtest</h3>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', maxWidth: '300px' }}>
          <label>Start Date: <input type="date" value={config.start_date} onChange={e => setConfig({...config, start_date: e.target.value})} style={{ width: '100%' }} /></label>
          <label>End Date: <input type="date" value={config.end_date} onChange={e => setConfig({...config, end_date: e.target.value})} style={{ width: '100%' }} /></label>
          <button className="primary" onClick={runBacktest}>Run Backtest</button>
        </div>
      </div>
      <div className="card">
        <h3>History</h3>
        {history && history.length > 0 ? (
          <ul style={{ listStyle: 'none', padding: 0 }}>
            {history.map(h => (
              <li key={h.job_id} style={{ padding: '10px', borderBottom: '1px solid #333' }}>
                {h.timestamp} - <span style={{ color: h.status === 'COMPLETED' ? '#4caf50' : '#00bcd4' }}>{h.status}</span> ({h.job_id})
              </li>
            ))}
          </ul>
        ) : (
          <p style={{ color: '#787b86' }}>No backtest history found.</p>
        )}
      </div>
    </div>
  );
};

export default BacktestTab;
