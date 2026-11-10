import React, { useEffect, useState } from 'react';
import { api } from '../api';

const DashboardTab = ({ onSwitchToV2 }) => {
  const [status, setStatus] = useState({});

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const data = await api.system.status();
        setStatus(data);
      } catch (err) {
        console.error("Dashboard status fetch error:", err);
      }
    };
    fetchStatus();
    const interval = setInterval(fetchStatus, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="dashboard-tab">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <h2 style={{ color: 'white' }}>Trading Dashboard</h2>
        <button 
          className="primary" 
          onClick={onSwitchToV2}
          style={{ padding: '8px 16px', fontWeight: 'bold' }}
        >
          Open V2 Terminal
        </button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '20px' }}>
        <div className="card">
          <h3>Bot Status</h3>
          <p style={{ color: status.live_trader_running ? '#4caf50' : '#f44336', fontWeight: 'bold' }}>
            {status.live_trader_running ? 'RUNNING' : 'STOPPED'}
          </p>
          <div style={{ display: 'flex', gap: '10px', marginTop: '10px' }}>
            <button className="primary" onClick={() => api.system.start()}>Start</button>
            <button className="danger" onClick={() => api.system.stop()}>Stop</button>
          </div>
        </div>
        
        <div className="card">
          <h3>Capital</h3>
          <p style={{ fontSize: '1.5em', color: '#00bcd4' }}>₹{status.capital || 0}</p>
        </div>

        <div className="card">
          <h3>Daily PnL</h3>
          <p style={{ fontSize: '1.5em', color: (status.daily_pnl || 0) >= 0 ? '#4caf50' : '#f44336' }}>
            ₹{status.daily_pnl || 0}
          </p>
        </div>

        <div className="card">
          <h3>Activity</h3>
          <p>Trades: {status.trades_today || 0} / 4</p>
          <p>Regime: {status.regime || 'UNKNOWN'}</p>
        </div>
      </div>

      <div className="card" style={{ marginTop: '20px' }}>
        <h3>Market Connection</h3>
        <p>Backend: http://localhost:8000</p>
        <p>Status: {status.live_trader_running ? 'Connected to Bot' : 'Waiting...'}</p>
      </div>
    </div>
  );
};

export default DashboardTab;
