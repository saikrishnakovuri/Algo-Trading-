import React from 'react';
import { useApi } from '../hooks/useApi';
import { Bell, ShieldAlert, CheckCircle, XCircle } from 'lucide-react';

const AlertLogs = () => {
  const { data: alerts, loading } = useApi('/api/alerts?limit=50', 5000);

  return (
    <div className="p-8 space-y-6">
      <h2 className="text-xl font-bold text-white uppercase tracking-widest">System Alerts & Notifications</h2>
      
      <div className="bg-[#161b27] border border-[#1e2130] rounded-xl overflow-hidden">
        <table className="w-full text-left border-collapse font-mono text-sm">
          <thead>
            <tr className="bg-[#1e2130] text-gray-400 uppercase text-[10px] tracking-widest">
              <th className="px-6 py-4 font-bold">Time</th>
              <th className="px-6 py-4 font-bold">Type</th>
              <th className="px-6 py-4 font-bold">Message</th>
              <th className="px-6 py-4 font-bold">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#1e2130]">
            {alerts?.map((a, i) => (
              <tr key={i} className="hover:bg-[#1e2130]/30 transition-colors">
                <td className="px-6 py-4 text-gray-500 text-xs whitespace-nowrap">{new Date(a.created_at).toLocaleTimeString()}</td>
                <td className="px-6 py-4">
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                    a.event_type === 'TRADE_OPEN' ? 'text-green-500' :
                    a.event_type === 'TRADE_CLOSE' ? 'text-[#00bcd4]' : 'text-gray-400'
                  }`}>
                    {a.event_type}
                  </span>
                </td>
                <td className="px-6 py-4 text-gray-300 text-xs">{a.message}</td>
                <td className="px-6 py-4">
                  {a.status === 'sent' ? (
                    <CheckCircle className="text-green-500" size={16} />
                  ) : (
                    <XCircle className="text-red-500" size={16} />
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default AlertLogs;
