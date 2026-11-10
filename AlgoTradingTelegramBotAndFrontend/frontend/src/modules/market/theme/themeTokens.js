/**
 * @file themeTokens.js
 * @description Centralized Tailwind/CSS theme tokens for the trading terminal.
 */

export const themeTokens = {
  colors: {
    background: '#0a0e17', // Very deep dark background
    panelBg: '#131722',   // TradingView standard panel color
    border: '#2a2e39',    // Subtle borders
    textPrimary: '#d1d4dc',
    textSecondary: '#787b86',
    
    // Trading colors
    bullish: '#26a69a',
    bearish: '#ef5350',
    bullishMuted: 'rgba(38, 166, 154, 0.2)',
    bearishMuted: 'rgba(239, 83, 80, 0.2)',
    
    // Status colors
    warning: '#f57c00',
    info: '#2962ff',
    
    // Highlights
    hover: '#1e222d',
    active: '#2a2e39'
  },
  spacing: {
    xs: '4px',
    sm: '8px',
    md: '16px',
    lg: '24px'
  }
};
