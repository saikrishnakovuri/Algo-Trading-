import React, { useState, useEffect } from 'react';
import { api } from '../api';

const StrategiesTab = () => {
  const [strategies, setStrategies] = useState({});

  useEffect(() => {
    const fetchStrats = async () => {
      try {
        const data = await api.strategies.list();
        setStrategies(data?.strategies || {});
      } catch (err) {
        console.error("Failed to fetch strategies:", err);
        setStrategies({});
      }
    };
    fetchStrats();
  }, []);

  return (
    <div className="strategies-tab">
      <h2 style={{ color: 'white' }}>Master Strategy Registry</h2>
      {Object.keys(strategies || {}).length > 0 ? (
        Object.keys(strategies).map(regime => (
          <div key={regime} className="card" style={{ marginBottom: '20px' }}>
            <h3 style={{ color: '#00bcd4', borderBottom: '1px solid #333', paddingBottom: '10px' }}>{regime}</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '15px', marginTop: '15px' }}>
              {(strategies[regime] || []).map((strat, i) => (
                <div key={i} style={{ padding: '10px', background: '#0a0e17', borderRadius: '4px', borderLeft: '4px solid #2962ff' }}>
                  <div style={{ fontWeight: 'bold', marginBottom: '5px' }}>{strat?.name || 'Unknown'}</div>
                  <div style={{ fontSize: '0.8em', color: '#787b86' }}>
                    <div>Priority: {strat?.priority}</div>
                    <div>Min Confidence: {strat?.min_confidence}%</div>
                    <div>Risk Multiplier: {strat?.risk_multiplier}x</div>
                    <div style={{ marginTop: '5px', fontStyle: 'italic' }}>"{strat?.rationale}"</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))
      ) : (
        <p style={{ color: '#787b86' }}>No strategies found in the registry.</p>
      )}
    </div>
  );
};

export default StrategiesTab;
