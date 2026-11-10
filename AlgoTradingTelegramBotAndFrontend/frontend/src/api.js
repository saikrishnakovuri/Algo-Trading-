const API_BASE = "http://localhost:8000/api";

export const fetchApi = async (endpoint, options = {}) => {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });
  if (!response.ok) {
    throw new Error(`API Error: ${response.statusText}`);
  }
  return response.json();
};

export const api = {
  configs: {
    list: () => fetchApi("/configs/list"),
    get: (name) => fetchApi(`/configs/${name}`),
    save: (name, data) => fetchApi(`/configs/${name}`, { method: "POST", body: JSON.stringify({ data }) }),
    revert: (name) => fetchApi(`/configs/${name}/revert`, { method: "POST" }),
  },
  backtest: {
    run: (config) => fetchApi("/backtest/run", { method: "POST", body: JSON.stringify(config) }),
    status: (id) => fetchApi(`/backtest/status/${id}`),
    result: (id) => fetchApi(`/backtest/result/${id}`),
    history: () => fetchApi("/backtest/history"),
  },
  trades: {
    live: () => fetchApi("/trades/live"),
    history: (from, to) => fetchApi(`/trades/history?from_date=${from || ''}&to_date=${to || ''}`),
  },
  system: {
    status: () => fetchApi("/system/status"),
    start: () => fetchApi("/system/start", { method: "POST" }),
    stop: () => fetchApi("/system/stop", { method: "POST" }),
    killSwitch: () => fetchApi("/system/kill-switch", { method: "POST" }),
  },
  logs: {
    tail: (lines) => fetchApi(`/logs/tail?lines=${lines}`),
  },
  strategies: {
    list: () => fetchApi("/strategies/list"),
    toggle: (regime, strategy, enabled) => fetchApi("/strategies/toggle", { method: "POST", body: JSON.stringify({ regime, strategy, enabled }) }),
    setMinConfidence: (regime, strategy, min_confidence) => fetchApi("/strategies/min_confidence", { method: "POST", body: JSON.stringify({ regime, strategy, min_confidence }) }),
  },
  riskguard: {
    state: () => fetchApi("/riskguard/state"),
    reset: () => fetchApi("/riskguard/reset", { method: "POST" }),
  },
  regime: {
    current: () => fetchApi("/regime/current"),
    history: () => fetchApi("/regime/history"),
  },
  notifications: {
    subscriptions: () => fetchApi("/notifications/subscriptions"),
    test: () => fetchApi("/notifications/test-send", { method: "POST" }),
  },
  candles: {
    history: (symbol, timeframe, limit) => fetchApi(`/candles/history?symbol=${symbol}&timeframe=${timeframe}&limit=${limit || 500}`),
  },
  docs: {
    list: () => fetchApi("/docs/list"),
    get: (name) => fetchApi(`/docs/${name}`),
  }
};
