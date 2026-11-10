import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import App from './App';

const rootElement = document.getElementById('root');
if (!rootElement) {
    console.error("Failed to find the root element");
} else {
    const root = ReactDOM.createRoot(rootElement);
    root.render(<App />);
}
