import React, { useState, useEffect } from 'react';
import { api } from '../api';

const DocsTab = () => {
  const [docs, setDocs] = useState([]);
  const [selectedDoc, setSelectedDoc] = useState(null);
  const [content, setContent] = useState('');

  useEffect(() => {
    const fetchDocs = async () => {
      const data = await api.docs.list();
      setDocs(data.docs);
    };
    fetchDocs();
  }, []);

  const loadDoc = async (name) => {
    const data = await api.docs.get(name);
    setSelectedDoc(name);
    setContent(data.content);
  };

  return (
    <div className="docs-tab">
      <h2>Documentation</h2>
      <div className="layout" style={{ display: 'flex', gap: '20px' }}>
        <div className="list" style={{ width: '250px' }}>
          {docs.map(name => (
            <button key={name} onClick={() => loadDoc(name)} style={{ display: 'block', width: '100%', marginBottom: '5px' }}>{name}</button>
          ))}
        </div>
        <div className="viewer card" style={{ flex: 1 }}>
          {selectedDoc ? (
            <>
              <h3>{selectedDoc}</h3>
              <pre style={{ whiteSpace: 'pre-wrap' }}>{content}</pre>
            </>
          ) : <p>Select a document to view</p>}
        </div>
      </div>
    </div>
  );
};

export default DocsTab;
