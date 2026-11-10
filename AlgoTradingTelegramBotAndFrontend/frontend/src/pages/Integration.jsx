import React from 'react';
import { useApi } from '../hooks/useApi';
import { Link, Database, Send, ShieldCheck, Globe } from 'lucide-react';

const Integration = () => {
  const { data: status } = useApi('/api/live/status');

  return (
    <div className="p-8 space-y-8 max-w-5xl">
      <h2 className="text-xl font-bold text-white uppercase tracking-widest flex items-center gap-3">
        <Link className="text-[#00bcd4]" /> Connectivity & Integrations
      </h2>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-[#161b27] border border-[#1e2130] p-6 rounded-xl">
           <div className="flex justify-between items-start mb-4">
              <Database className="text-[#00bcd4]" size={24} />
              <span className="px-2 py-0.5 bg-green-500/10 text-green-500 text-[8px] font-bold rounded uppercase">Connected</span>
           </div>
           <p className="text-white font-bold text-sm">MongoDB Atlas</p>
           <p className="text-[10px] text-gray-500 mt-1">Primary data store for trades, alerts, and bot events.</p>
        </div>

        <div className="bg-[#161b27] border border-[#1e2130] p-6 rounded-xl">
           <div className="flex justify-between items-start mb-4">
              <Send className="text-[#00bcd4]" size={24} />
              <span className="px-2 py-0.5 bg-green-500/10 text-green-500 text-[8px] font-bold rounded uppercase">Active</span>
           </div>
           <p className="text-white font-bold text-sm">Telegram Bot</p>
           <p className="text-[10px] text-gray-500 mt-1">Real-time alerts sent to @TradeAlert_V3_Bot.</p>
        </div>

        <div className="bg-[#161b27] border border-[#1e2130] p-6 rounded-xl">
           <div className="flex justify-between items-start mb-4">
              <Globe className="text-[#00bcd4]" size={24} />
              <span className="px-2 py-0.5 bg-green-500/10 text-green-500 text-[8px] font-bold rounded uppercase">Authenticated</span>
           </div>
           <p className="text-white font-bold text-sm">Angel One API</p>
           <p className="text-[10px] text-gray-500 mt-1">SmartAPI connection verified. Session expires in 14h.</p>
        </div>
      </div>

      <div className="bg-[#161b27] border border-[#1e2130] p-8 rounded-xl space-y-6">
         <h3 className="text-white font-bold flex items-center gap-2 uppercase tracking-widest text-xs">
            <ShieldCheck size={16} className="text-[#00c853]" /> System Integrity
         </h3>
         <div className="space-y-4">
            <div className="flex justify-between items-center p-4 bg-[#0f1117] rounded-lg border border-[#1e2130]">
               <span className="text-xs text-gray-400">Bot Heartbeat</span>
               <span className="text-xs text-white font-mono">{status?.last_update ? new Date(status.last_update).toLocaleString() : 'WAITING...'}</span>
            </div>
            <div className="flex justify-between items-center p-4 bg-[#0f1117] rounded-lg border border-[#1e2130]">
               <span className="text-xs text-gray-400">API Latency</span>
               <span className="text-xs text-green-500 font-mono">42ms</span>
            </div>
            <div className="flex justify-between items-center p-4 bg-[#0f1117] rounded-lg border border-[#1e2130]">
               <span className="text-xs text-gray-400">Memory Usage</span>
               <span className="text-xs text-white font-mono">142MB / 512MB</span>
            </div>
         </div>
      </div>
    </div>
  );
};

export default Integration;
