import React, { useState, useEffect, useRef } from 'react';
import { WSClient } from '../ws';
import { api } from '../api';

const LogsTab = () => {
  const [logs, setLogs] = useState([]);
  const logEndRef = useRef(null);

  useEffect(() => {
    const fetchInitial = async () => {
      try {
        const data = await api.logs.tail(100);
        setLogs(data?.logs || []);
      } catch (err) {
        console.error("Failed to fetch initial logs:", err);
        setLogs(["Error fetching initial logs."]);
      }
    };
    fetchInitial();

    const ws = new WSClient('/api/logs/ws/logs');
    ws.onMessage = (line) => setLogs(prev => [...(prev || []).slice(-1000), line]);
    ws.connect();
    return () => ws.close();
  }, []);

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  return (
    <div className="logs-tab">
      <h2>System Logs</h2>
      <div className="log-container" style={{ backgroundColor: '#000', color: '#0f0', padding: '10px', height: '500px', overflowY: 'scroll', fontFamily: 'monospace', borderRadius: '4px' }}>
        {(logs || []).map((line, i) => (
          <div key={i}>{line}</div>
        ))}
        {(!logs || logs.length === 0) && <div style={{ color: '#555' }}>Streaming logs...</div>}
        <div ref={logEndRef} />
      </div>
    </div>
  );
};

export default LogsTab;
