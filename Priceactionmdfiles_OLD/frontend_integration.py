import os
import re

FRONTEND_DIR = '../AlgoTradingTelegramBotAndFrontend/frontend/src'

PA_DASHBOARD_CODE = """import React, { useState, useEffect } from 'react';

const API_BASE = 'http://localhost:8000/api/pa'; // Adjust if needed

function SaveButton({ onClick, label = "Save" }) {
    return <button onClick={onClick} className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded text-white font-bold">{label}</button>;
}

export default function PADashboard() {
    const [activeTab, setActiveTab] = useState('strategies');
    const [toast, setToast] = useState(null);

    const showToast = (msg, type = 'success') => {
        setToast({ msg, type });
        setTimeout(() => setToast(null), 3000);
    };

    async function saveToBackend(endpoint, data) {
        try {
            const response = await fetch(`${API_BASE}${endpoint}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            const result = await response.json();
            showToast(result.status === 'saved' || result.action ? 'Saved successfully!' : 'Save failed: ' + result.error, result.error ? 'error' : 'success');
        } catch (err) {
            showToast('Save error: ' + err.message, 'error');
        }
    }

    return (
        <div className="p-6">
            <h1 className="text-2xl font-bold mb-4">Price Action Engine Dashboard</h1>
            
            {toast && (
                <div className={`fixed top-4 right-4 p-4 rounded text-white ${toast.type === 'error' ? 'bg-red-600' : 'bg-green-600'}`}>
                    {toast.msg}
                </div>
            )}

            <div className="flex border-b border-gray-700 mb-6">
                {['strategies', 'config', 'edge', 'montecarlo', 'backtest'].map(tab => (
                    <button 
                        key={tab}
                        onClick={() => setActiveTab(tab)}
                        className={`px-4 py-2 ${activeTab === tab ? 'border-b-2 border-blue-500 text-blue-400' : 'text-gray-400 hover:text-white'}`}
                    >
                        {tab.toUpperCase()}
                    </button>
                ))}
            </div>

            {activeTab === 'strategies' && <PAStrategyManager saveToBackend={saveToBackend} />}
            {activeTab === 'config' && <PAConfigEditor saveToBackend={saveToBackend} />}
            {activeTab === 'edge' && <PAEdgeMonitor />}
            {activeTab === 'montecarlo' && <PAMonteCarlo />}
            {activeTab === 'backtest' && <PABacktestResults />}
        </div>
    );
}

function PAStrategyManager({ saveToBackend }) {
    const [strategies, setStrategies] = useState([]);

    useEffect(() => {
        fetch(`${API_BASE}/strategies`).then(res => res.json()).then(setStrategies).catch(console.error);
    }, []);

    const toggle = async (name) => {
        await saveToBackend(`/strategies/${name}/toggle`, {});
        fetch(`${API_BASE}/strategies`).then(res => res.json()).then(setStrategies);
    };

    return (
        <div>
            <div className="flex justify-between mb-4">
                <h2 className="text-xl font-semibold">Strategy Manager</h2>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {strategies.map(s => (
                    <div key={s.name} className="p-4 bg-gray-800 rounded flex justify-between items-center">
                        <div>
                            <div className="font-bold">{s.name}</div>
                            <div className="text-sm text-gray-400">PF: {s.profit_factor} | Conf: {s.confidence} | Dir: {s.direction}</div>
                        </div>
                        <button onClick={() => toggle(s.name)} className={`px-4 py-1 rounded ${s.active ? 'bg-green-600' : 'bg-gray-600'}`}>
                            {s.active ? 'ON' : 'OFF'}
                        </button>
                    </div>
                ))}
            </div>
        </div>
    );
}

function PAConfigEditor({ saveToBackend }) {
    const [schedule, setSchedule] = useState({ allowed_hours: [], allowed_days: [], sl_method: '' });
    const [risk, setRisk] = useState({});

    useEffect(() => {
        fetch(`${API_BASE}/schedule`).then(res => res.json()).then(setSchedule);
        fetch(`${API_BASE}/risk`).then(res => res.json()).then(setRisk);
    }, []);

    const handleSave = () => {
        saveToBackend('/schedule', schedule);
        saveToBackend('/risk', risk);
    };

    return (
        <div>
            <div className="flex justify-between mb-4">
                <h2 className="text-xl font-semibold">Config Editor</h2>
                <SaveButton onClick={handleSave} />
            </div>
            <div className="space-y-4">
                <div className="p-4 bg-gray-800 rounded">
                    <h3 className="font-bold mb-2">Schedule</h3>
                    <div>Hours: {schedule.allowed_hours?.join(', ')}</div>
                    <div>Days: {schedule.allowed_days?.join(', ')}</div>
                    <div>SL Method: {schedule.sl_method}</div>
                    <div className="text-sm text-gray-400 mt-2">(Basic view; fully functional via API)</div>
                </div>
                <div className="p-4 bg-gray-800 rounded">
                    <h3 className="font-bold mb-2">Risk Management</h3>
                    <pre className="text-sm">{JSON.stringify(risk, null, 2)}</pre>
                </div>
            </div>
        </div>
    );
}

function PAEdgeMonitor() {
    const [edge, setEdge] = useState(null);

    useEffect(() => {
        fetch(`${API_BASE}/edge`).then(res => res.json()).then(setEdge);
    }, []);

    if (!edge) return <div>Loading...</div>;

    return (
        <div>
            <div className="flex justify-between mb-4">
                <h2 className="text-xl font-semibold">Edge Monitor</h2>
            </div>
            <div className="p-4 bg-gray-800 rounded">
                <div className={`text-xl font-bold mb-4 ${edge.status === 'GREEN' ? 'text-green-500' : 'text-red-500'}`}>STATUS: {edge.status}</div>
                <pre className="text-sm overflow-auto max-h-[600px] bg-gray-900 p-4 rounded">
                    {JSON.stringify(edge, null, 2)}
                </pre>
            </div>
        </div>
    );
}

function PAMonteCarlo() {
    const [mc, setMc] = useState(null);

    useEffect(() => {
        fetch(`${API_BASE}/montecarlo`).then(res => res.json()).then(setMc);
    }, []);

    if (!mc) return <div>Loading...</div>;

    return (
        <div>
            <div className="flex justify-between mb-4">
                <h2 className="text-xl font-semibold">Monte Carlo Stress Test</h2>
            </div>
            <div className="p-4 bg-gray-800 rounded overflow-auto max-h-[600px]">
                 <pre className="text-sm bg-gray-900 p-4 rounded">
                    {JSON.stringify(mc, null, 2)}
                </pre>
            </div>
        </div>
    );
}

function PABacktestResults() {
    const [files, setFiles] = useState([]);
    const [selected, setSelected] = useState(null);

    useEffect(() => {
        fetch(`${API_BASE}/backtest/files`).then(res => res.json()).then(setFiles);
    }, []);

    const loadFile = (name) => {
        fetch(`${API_BASE}/backtest/${name}`).then(res => res.json()).then(setSelected);
    };

    return (
        <div>
            <div className="flex justify-between mb-4">
                <h2 className="text-xl font-semibold">Backtest Results</h2>
            </div>
            <div className="flex gap-4 mb-4">
                {files.map(f => (
                    <button key={f.name} onClick={() => loadFile(f.name)} className="px-4 py-2 bg-gray-800 hover:bg-gray-700 rounded">
                        {f.name} ({f.size_kb}KB)
                    </button>
                ))}
            </div>
            {selected && (
                <div className="p-4 bg-gray-800 rounded overflow-auto max-h-[600px]">
                     <pre className="text-sm bg-gray-900 p-4 rounded">
                        {JSON.stringify(selected, null, 2)}
                    </pre>
                </div>
            )}
        </div>
    );
}
"""

def integrate_frontend():
    # 1. Write the PADashboard component
    pad_path = os.path.join(FRONTEND_DIR, 'pages', 'PADashboard.js')
    with open(pad_path, 'w') as f:
        f.write(PA_DASHBOARD_CODE)
    
    # 2. Update App.js
    app_path = os.path.join(FRONTEND_DIR, 'App.js')
    if os.path.exists(app_path):
        with open(app_path, 'r') as f:
            app_code = f.read()
            
        if 'PADashboard' not in app_code:
            # Insert import
            app_code = app_code.replace("import Settings from './pages/Settings';", "import Settings from './pages/Settings';\nimport PADashboard from './pages/PADashboard';")
            
            # Insert Route
            app_code = app_code.replace('<Route path="/settings" element={<Settings />} />', '<Route path="/settings" element={<Settings />} />\n              <Route path="/pa-engine" element={<PADashboard />} />')
            
            with open(app_path, 'w') as f:
                f.write(app_code)
                
    # 3. Update Sidebar.js
    sidebar_path = os.path.join(FRONTEND_DIR, 'components', 'Sidebar.js')
    if os.path.exists(sidebar_path):
        with open(sidebar_path, 'r') as f:
            sidebar_code = f.read()
            
        if '/pa-engine' not in sidebar_code:
            # We inject the NavLink for /pa-engine before /settings
            # Find the string <NavLink to="/settings"
            inject_str = '<NavLink to="/pa-engine" className={({isActive}) => `flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${isActive ? "bg-[#00bcd4]/10 text-[#00bcd4]" : "text-gray-400 hover:text-gray-200 hover:bg-gray-800/50"}`}><span className="text-xl">⚙️</span><span className="font-medium">PA Engine</span></NavLink>\n          '
            if '<NavLink to="/settings"' in sidebar_code:
                sidebar_code = sidebar_code.replace('<NavLink to="/settings"', inject_str + '<NavLink to="/settings"')
                with open(sidebar_path, 'w') as f:
                    f.write(sidebar_code)
                
if __name__ == "__main__":
    integrate_frontend()
    print("Frontend integration complete.")
