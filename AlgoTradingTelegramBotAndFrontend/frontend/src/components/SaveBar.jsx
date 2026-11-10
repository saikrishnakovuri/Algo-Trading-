import React from 'react';

const SaveBar = ({ onSave, onRevert, isDirty }) => {
  if (!isDirty) return null;

  return (
    <div className="save-bar" style={{ position: 'fixed', bottom: 0, left: '200px', right: 0, backgroundColor: '#1e2130', padding: '10px', borderTop: '1px solid #accent', display: 'flex', justifyContent: 'center', gap: '20px' }}>
      <span>You have unsaved changes</span>
      <button className="primary" onClick={onSave}>Save Changes</button>
      <button onClick={onRevert}>Revert</button>
    </div>
  );
};

export default SaveBar;
