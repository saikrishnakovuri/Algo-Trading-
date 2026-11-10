import React, { useState, useEffect } from 'react';
import { api } from '../api';

const SystemSettingsTab = () => {
  const [settings, setSettings] = useState({
    TOTAL_CAPITAL: 100000,
    MAX_TRADES_PER_DAY: 4,
    DAILY_LOSS_LIMIT_PCT: 0.025
  });

  return (
    <div className="system-settings-tab">
      <h2>System Settings (v3_utils)</h2>
      <div className="card">
        <div style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
          <label style={{ display: 'flex', justifyContent: 'space-between', maxWidth: '400px' }}>
            TOTAL_CAPITAL: <input type="number" value={settings.TOTAL_CAPITAL} readOnly style={{ backgroundColor: '#0a0e17', color: '#787b86', border: '1px solid #333' }} />
          </label>
          <label style={{ display: 'flex', justifyContent: 'space-between', maxWidth: '400px' }}>
            MAX_TRADES_PER_DAY: <input type="number" value={settings.MAX_TRADES_PER_DAY} readOnly style={{ backgroundColor: '#0a0e17', color: '#787b86', border: '1px solid #333' }} />
          </label>
          <label style={{ display: 'flex', justifyContent: 'space-between', maxWidth: '400px' }}>
            DAILY_LOSS_LIMIT_PCT: <input type="number" value={settings.DAILY_LOSS_LIMIT_PCT} readOnly style={{ backgroundColor: '#0a0e17', color: '#787b86', border: '1px solid #333' }} />
          </label>
        </div>
        <p className="text-secondary" style={{ marginTop: '20px', color: '#787b86', fontStyle: 'italic' }}>
          Note: Manual edits to v3_utils.py are disabled via the UI to maintain system integrity.
        </p>
      </div>
    </div>
  );
};

export default SystemSettingsTab;
