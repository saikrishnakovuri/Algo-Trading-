import React from 'react';
import { api } from '../api';

const KillSwitch = () => {
  const handleKill = async () => {
    if (window.confirm("ARE YOU SURE? This will stop the bot and close all positions!")) {
      try {
        await api.system.killSwitch();
        alert("KILL SWITCH ACTIVATED");
      } catch (err) {
        alert("Failed to activate kill switch: " + err.message);
      }
    }
  };

  return (
    <button 
      className="danger" 
      onClick={handleKill}
      style={{ fontWeight: 'bold', padding: '10px 20px' }}
    >
      EMERGENCY KILL SWITCH
    </button>
  );
};

export default KillSwitch;
