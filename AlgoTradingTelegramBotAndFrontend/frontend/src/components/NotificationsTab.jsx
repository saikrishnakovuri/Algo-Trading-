import React, { useState, useEffect } from 'react';
import { api } from '../api';

const NotificationsTab = () => {
  const [subs, setSubs] = useState({});

  useEffect(() => {
    const fetchSubs = async () => {
      try {
        const data = await api.notifications.subscriptions();
        setSubs(data || {});
      } catch (err) {
        console.error("Failed to fetch notification settings:", err);
      }
    };
    fetchSubs();
  }, []);

  return (
    <div className="notifications-tab">
      <h2>Notifications</h2>
      <div className="card">
        <h3>Telegram</h3>
        <p>Status: {subs?.telegram?.enabled ? 'ENABLED' : 'DISABLED'}</p>
        <p>Chat ID: {subs?.telegram?.chat_id || 'N/A'}</p>
        <button className="primary" onClick={() => api.notifications.test()}>Send Test Message</button>
      </div>
    </div>
  );
};

export default NotificationsTab;
