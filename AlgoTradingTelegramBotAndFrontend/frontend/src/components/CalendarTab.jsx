import React from 'react';

const CalendarTab = () => {
  return (
    <div className="calendar-tab">
      <h2>Trading Calendar</h2>
      <div className="card">
        <h3>No-Trade Dates</h3>
        <ul>
          <li>2026-01-26 (Republic Day)</li>
          <li>2026-03-06 (Holi)</li>
        </ul>
        <button className="primary">Add Date</button>
      </div>
    </div>
  );
};

export default CalendarTab;
