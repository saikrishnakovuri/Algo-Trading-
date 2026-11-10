import React, { useState, useEffect } from 'react';
import { 
  Settings, 
  FileCode, 
  Save, 
  RefreshCw,
  AlertTriangle
} from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8000';
const API_BASE = `${BACKEND_URL}/api/config`;

export default function ConfigExplorer() {
    const [files, setFiles] = useState([]);
    const [selected, setSelected] = useState('');
    const [content, setContent] = useState('');
    const [loading, setLoading] = useState(false);
    const [saving, setSaving] = useState(false);

    useEffect(() => {
        fetch(`${API_BASE}/files`).then(res => res.json()).then(setFiles);
    }, []);

    const loadFile = async (name) => {
        setLoading(true);
        setSelected(name);
        try {
            const res = await fetch(`${API_BASE}/content/${name}`);
            const data = await res.json();
            setContent(data.content);
        } catch (err) {
            alert(err.message);
        }
        setLoading(false);
    };

    const handleSave = async () => {
        setSaving(true);
        try {
            const res = await fetch(`${API_BASE}/content/${selected}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ content })
            });
            if (res.ok) alert('File saved successfully');
            else {
                const err = await res.json();
                alert(`Error: ${err.detail}`);
            }
        } catch (err) {
            alert(err.message);
        }
        setSaving(false);
    };

    return (
        <div className="p-8 space-y-8 text-gray-100">
             <div className="flex justify-between items-center">
                <h1 className="text-2xl font-bold text-white uppercase tracking-widest flex items-center gap-3">
                    <Settings size={28} className="text-[#00bcd4]" /> Advanced Config Explorer
                </h1>
                <div className="flex gap-4">
                    <button 
                        onClick={handleSave}
                        disabled={!selected || saving}
                        className="bg-[#00bcd4] disabled:opacity-30 text-black font-bold px-6 py-2 rounded-lg flex items-center gap-2 hover:bg-[#00acc1] text-xs"
                    >
                        <Save size={16} /> {saving ? 'SAVING...' : 'SAVE CHANGES'}
                    </button>
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
                {/* File List */}
                <div className="bg-[#161b27] p-6 rounded-2xl border border-[#1e2130] h-fit">
                    <h2 className="text-xs font-bold text-gray-500 uppercase tracking-widest mb-6 flex items-center gap-2">
                        <FileCode size={14} className="text-[#00bcd4]" /> Config Files
                    </h2>
                    <div className="space-y-2">
                        {files.map(f => (
                            <button 
                                key={f} 
                                onClick={() => loadFile(f)}
                                className={`w-full text-left px-4 py-2 rounded-lg text-xs font-bold transition-all border ${selected === f ? 'bg-[#00bcd4]/10 border-[#00bcd4] text-[#00bcd4]' : 'bg-[#0f1117] border-[#1e2130] text-gray-500 hover:text-white'}`}
                            >
                                {f}
                            </button>
                        ))}
                    </div>
                </div>

                {/* Editor Area */}
                <div className="lg:col-span-3 bg-[#161b27] rounded-2xl border border-[#1e2130] overflow-hidden flex flex-col h-[700px]">
                    <div className="p-4 bg-[#1c212e] border-b border-[#1e2130] flex justify-between items-center">
                         <span className="text-xs font-mono text-[#00bcd4]">{selected || 'Select a file to edit'}</span>
                         {loading && <RefreshCw size={14} className="animate-spin text-gray-500" />}
                    </div>
                    <textarea 
                        className="flex-1 bg-[#0f1117] p-8 text-sm font-mono text-gray-400 outline-none resize-none"
                        value={content}
                        onChange={(e) => setContent(e.target.value)}
                        placeholder="# Configuration content will appear here..."
                        spellCheck="false"
                    />
                    <div className="p-4 bg-[#1c212e]/50 flex items-center gap-3 text-xs text-orange-400">
                        <AlertTriangle size={14} />
                        <span>Warning: Direct edits to YAML files can crash the bot if syntax is invalid.</span>
                    </div>
                </div>
            </div>
        </div>
    );
}
