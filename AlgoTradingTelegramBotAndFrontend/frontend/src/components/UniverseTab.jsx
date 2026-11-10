import React from 'react';

const UniverseTab = () => {
  return (
    <div className="universe-tab">
      <h2>Trading Universe</h2>
      <div className="card">
        <h3>Current Scrips</h3>
        <ul>
          <li>NIFTY</li>
          <li>BANKNIFTY</li>
          <li>FINNIFTY</li>
        </ul>
        <button className="primary">Add Scrip</button>
      </div>
    </div>
  );
};

export default UniverseTab;
