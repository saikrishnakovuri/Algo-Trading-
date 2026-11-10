import React, { useState, useEffect } from 'react';
import api, { useApi } from '../hooks/useApi';
import { Save, ShieldAlert, Cpu, Globe } from 'lucide-react';

const Settings = () => {
  const { data: currentSettings, loading } = useApi('/api/settings');
  const [settings, setSettings] = useState(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (currentSettings) setSettings(currentSettings);
  }, [currentSettings]);

  const handleSave = async () => {
    setSaving(true);
    try {
      await api.put('/api/settings', settings);
      alert('Settings updated successfully');
    } catch (err) {
      alert(`Save failed: ${err.message}`);
    }
    setSaving(false);
  };

  if (!settings) return <div className="p-8 text-gray-500 animate-pulse">Loading configurations...</div>;

  return (
    <div className="p-8 max-w-4xl space-y-8">
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-bold text-white uppercase tracking-widest">Global Settings</h2>
        <button 
          onClick={handleSave}
          disabled={saving}
          className="bg-[#00bcd4] hover:bg-[#00acc1] text-black font-bold px-8 py-2 rounded-lg transition-all flex items-center gap-2"
        >
          {saving ? <div className="w-4 h-4 border-2 border-black border-t-transparent rounded-full animate-spin"></div> : <Save size={18} />}
          SAVE CHANGES
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        {/* Risk Management */}
        <div className="bg-[#161b27] border border-[#1e2130] p-6 rounded-xl space-y-6">
          <h3 className="text-white font-bold flex items-center gap-2 uppercase tracking-widest text-xs">
            <ShieldAlert size={16} className="text-red-500" /> Risk Controls
          </h3>
          <div className="space-y-4">
            <div className="space-y-1">
              <label className="text-[10px] text-gray-500 uppercase font-bold">Max Daily Loss (₹)</label>
              <input 
                type="number" 
                className="w-full bg-[#0f1117] border border-[#1e2130] rounded-lg p-3 text-white focus:border-[#00bcd4] outline-none font-mono"
                value={settings.max_daily_loss || 30000}
                onChange={(e) => setSettings({...settings, max_daily_loss: parseInt(e.target.value)})}
              />
            </div>
            <div className="space-y-1">
              <label className="text-[10px] text-gray-500 uppercase font-bold">Risk Per Trade (%)</label>
              <input 
                type="number" step="0.1"
                className="w-full bg-[#0f1117] border border-[#1e2130] rounded-lg p-3 text-white focus:border-[#00bcd4] outline-none font-mono"
                value={settings.risk_per_trade || 1.0}
                onChange={(e) => setSettings({...settings, risk_per_trade: parseFloat(e.target.value)})}
              />
            </div>
            <div className="space-y-1">
              <label className="text-[10px] text-gray-500 uppercase font-bold">Max Trades per Day</label>
              <input 
                type="number" 
                className="w-full bg-[#0f1117] border border-[#1e2130] rounded-lg p-3 text-white focus:border-[#00bcd4] outline-none font-mono"
                value={settings.max_trades_day || 5}
                onChange={(e) => setSettings({...settings, max_trades_day: parseInt(e.target.value)})}
              />
            </div>
          </div>
        </div>

        {/* Execution Mode */}
        <div className="bg-[#161b27] border border-[#1e2130] p-6 rounded-xl space-y-6">
          <h3 className="text-white font-bold flex items-center gap-2 uppercase tracking-widest text-xs">
            <Cpu size={16} className="text-[#00c853]" /> Bot Execution
          </h3>
          <div className="space-y-6">
            <div className="flex justify-between items-center p-4 bg-[#0f1117] rounded-xl border border-[#1e2130]">
              <div>
                <p className="text-white font-bold text-sm">Bot Mode</p>
                <p className="text-[10px] text-gray-500">Paper mode uses simulated orders</p>
              </div>
              <div className="flex bg-[#1e2130] p-1 rounded-lg border border-[#30364d]">
                <button 
                  className={`px-4 py-1.5 rounded-md text-[10px] font-bold transition-all ${settings.bot_mode === 'PAPER' ? 'bg-[#00c853] text-black' : 'text-gray-500'}`}
                  onClick={() => setSettings({...settings, bot_mode: 'PAPER'})}
                >PAPER</button>
                <button 
                  className={`px-4 py-1.5 rounded-md text-[10px] font-bold transition-all ${settings.bot_mode === 'LIVE' ? 'bg-red-500 text-white' : 'text-gray-500'}`}
                  onClick={() => {
                    if(window.confirm('WARNING: Live mode will use REAL money. Are you sure?')) 
                      setSettings({...settings, bot_mode: 'LIVE'})
                  }}
                >LIVE</button>
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-[10px] text-gray-500 uppercase font-bold">Active Indices</label>
              <div className="flex flex-wrap gap-2">
                {['NIFTY', 'BANKNIFTY', 'FINNIFTY', 'SENSEX'].map(index => (
                   <button 
                    key={index}
                    onClick={() => {
                      const current = settings.active_indices || ['NIFTY', 'BANKNIFTY'];
                      const updated = current.includes(index) ? current.filter(i => i !== index) : [...current, index];
                      setSettings({...settings, active_indices: updated});
                    }}
                    className={`px-3 py-1.5 rounded-lg text-[10px] font-bold border transition-all ${
                      (settings.active_indices || ['NIFTY', 'BANKNIFTY']).includes(index)
                      ? 'bg-[#00bcd4]/10 border-[#00bcd4] text-[#00bcd4]'
                      : 'bg-[#0f1117] border-[#1e2130] text-gray-500'
                    }`}
                   >{index}</button>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* API Credentials */}
        <div className="bg-[#161b27] border border-[#1e2130] p-6 rounded-xl space-y-6 md:col-span-2">
          <h3 className="text-white font-bold flex items-center gap-2 uppercase tracking-widest text-xs">
            <Globe size={16} className="text-[#00bcd4]" /> Broker API Configuration
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
             <div className="space-y-1">
                <label className="text-[10px] text-gray-500 uppercase font-bold">SmartAPI Key</label>
                <input 
                  type="password" 
                  className="w-full bg-[#0f1117] border border-[#1e2130] rounded-lg p-3 text-white focus:border-[#00bcd4] outline-none font-mono text-xs"
                  value={settings.api_key || '****************'}
                  onChange={(e) => setSettings({...settings, api_key: e.target.value})}
                />
              </div>
              <div className="space-y-1">
                <label className="text-[10px] text-gray-500 uppercase font-bold">Client Code</label>
                <input 
                  type="text" 
                  className="w-full bg-[#0f1117] border border-[#1e2130] rounded-lg p-3 text-white focus:border-[#00bcd4] outline-none font-mono text-xs"
                  value={settings.client_code || 'S123456'}
                  onChange={(e) => setSettings({...settings, client_code: e.target.value})}
                />
              </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Settings;
