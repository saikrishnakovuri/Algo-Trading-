import React, { useState, useEffect } from 'react';
import { api } from '../api';

const ConfigsTab = () => {
  const [configList, setConfigList] = useState([]);
  const [selectedConfig, setSelectedConfig] = useState(null);
  const [content, setContent] = useState({});

  useEffect(() => {
    const fetchList = async () => {
      try {
        const data = await api.configs.list();
        setConfigList(data?.configs || []);
      } catch (err) {
        console.error("Failed to fetch configs:", err);
        setConfigList([]);
      }
    };
    fetchList();
  }, []);

  const loadConfig = async (name) => {
    try {
      const data = await api.configs.get(name);
      setSelectedConfig(name);
      setContent(data?.data || {});
    } catch (err) {
      console.error("Failed to load config:", err);
    }
  };

  const saveConfig = async () => {
    try {
      await api.configs.save(selectedConfig, content);
      alert("Saved!");
    } catch (err) {
      alert("Failed to save: " + err.message);
    }
  };

  return (
    <div className="configs-tab">
      <h2>Configurations</h2>
      <div className="layout" style={{ display: 'flex', gap: '20px' }}>
        <div className="list" style={{ minWidth: '200px', display: 'flex', flexDirection: 'column', gap: '5px' }}>
          {(configList || []).map(name => (
            <button 
              key={name} 
              className={selectedConfig === name ? 'active' : ''}
              onClick={() => loadConfig(name)}
              style={{
                textAlign: 'left', padding: '10px', borderRadius: '4px',
                backgroundColor: selectedConfig === name ? '#00bcd4' : '#1e2130',
                color: 'white', border: 'none', cursor: 'pointer'
              }}
            >
              {name}
            </button>
          ))}
          {configList.length === 0 && <p style={{ color: '#787b86' }}>No configs found.</p>}
        </div>
        <div className="editor card" style={{ flex: 1 }}>
          {selectedConfig ? (
            <>
              <h3>Editing: {selectedConfig}</h3>
              <textarea 
                value={JSON.stringify(content, null, 2)} 
                onChange={e => {
                  try { setContent(JSON.parse(e.target.value)) } catch {}
                }}
                rows={20}
                style={{ width: '100%', backgroundColor: '#000', color: '#0f0', fontFamily: 'monospace', padding: '10px', borderRadius: '4px' }}
              />
              <div style={{ marginTop: '10px' }}>
                <button className="primary" onClick={saveConfig}>Save Changes</button>
              </div>
            </>
          ) : <p style={{ color: '#787b86' }}>Select a configuration file from the left to edit its parameters.</p>}
        </div>
      </div>
    </div>
  );
};

export default ConfigsTab;
