import React, { useState, useEffect } from 'react';
import { api } from '../api';

const RegimeTab = () => {
  const [current, setCurrent] = useState({
    regime: 'INITIALIZING',
    confidence: 0
  });
  const [history, setHistory] = useState([]);

  useEffect(() => {
    const fetchRegime = async () => {
      try {
        const curr = await api.regime.current();
        setCurrent(curr || { regime: 'UNKNOWN', confidence: 0 });
        const hist = await api.regime.history();
        setHistory(hist?.history || []);
      } catch (err) {
        console.error("Failed to fetch regime data:", err);
      }
    };
    fetchRegime();
  }, []);

  return (
    <div className="regime-tab">
      <h2 style={{ color: 'white' }}>Market Regime Detection</h2>
      <div className="card">
        <h3>Current Regime: <span style={{ color: '#00bcd4' }}>{current?.regime || 'FETCHING...'}</span></h3>
        <p>Confidence: <span style={{ fontWeight: 'bold' }}>{((current?.confidence || 0) * 100).toFixed(1)}%</span></p>
      </div>
      <div className="card" style={{ marginTop: '20px' }}>
        <h3>Regime History</h3>
        {(history || []).length > 0 ? (
          <ul style={{ listStyle: 'none', padding: 0 }}>
            {history.map((h, i) => (
              <li key={i} style={{ padding: '10px', borderBottom: '1px solid #333', display: 'flex', justifyContent: 'space-between' }}>
                <span>{h?.timestamp || 'N/A'}</span>
                <span style={{ fontWeight: 'bold', color: '#2962ff' }}>{h?.regime}</span>
                <span>{((h?.confidence || 0) * 100).toFixed(1)}%</span>
              </li>
            ))}
          </ul>
        ) : (
          <p style={{ color: '#787b86' }}>No regime history recorded yet.</p>
        )}
      </div>
    </div>
  );
};

export default RegimeTab;
