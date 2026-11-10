import React, { Suspense } from 'react';
import { BrowserRouter as Router, Routes, Route, useNavigate, useLocation } from 'react-router-dom';
import KillSwitch from './components/KillSwitch';
import './styles/theme.css';

// Lazy load ALL tabs to isolate errors
const DashboardTab = React.lazy(() => import('./components/DashboardTab'));
const LivePnLTab = React.lazy(() => import('./components/LivePnLTab'));
const TradesTab = React.lazy(() => import('./components/TradesTab'));
const BacktestTab = React.lazy(() => import('./components/BacktestTab'));
const ConfigsTab = React.lazy(() => import('./components/ConfigsTab'));
const SystemSettingsTab = React.lazy(() => import('./components/SystemSettingsTab'));
const StrategiesTab = React.lazy(() => import('./components/StrategiesTab'));
const RiskGuardTab = React.lazy(() => import('./components/RiskGuardTab'));
const RegimeTab = React.lazy(() => import('./components/RegimeTab'));
const NotificationsTab = React.lazy(() => import('./components/NotificationsTab'));
const CalendarTab = React.lazy(() => import('./components/CalendarTab'));
const UniverseTab = React.lazy(() => import('./components/UniverseTab'));
const LogsTab = React.lazy(() => import('./components/LogsTab'));
const DocsTab = React.lazy(() => import('./components/DocsTab'));
const TradingLayout = React.lazy(() => import('./modules/market/layouts/TradingLayout').then(m => ({ default: m.TradingLayout })));

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }
  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }
  render() {
    if (this.state.hasError) {
      return (
        <div style={{ color: 'white', padding: '20px', background: '#300', margin: '20px', borderRadius: '8px' }}>
          <h2>Something went wrong in {this.props.name}</h2>
          <pre>{this.state.error?.message}</pre>
          <button onClick={() => this.setState({ hasError: false })}>Try again</button>
        </div>
      );
    }
    return this.props.children;
  }
}

const NavSidebar = () => {
  const navigate = useNavigate();
  const location = useLocation();
  
  const tabList = [
    { id: 'dashboard', label: 'Dashboard', path: '/' },
    { id: 'v2', label: 'V2 Terminal', path: '/v2' },
    { id: 'pnl', label: 'Live P&L', path: '/pnl' },
    { id: 'trades', label: 'Trades', path: '/trades' },
    { id: 'backtest', label: 'Backtest', path: '/backtest' },
    { id: 'configs', label: 'Configs', path: '/configs' },
    { id: 'settings', label: 'System Settings', path: '/settings' },
    { id: 'strategies', label: 'Strategies', path: '/strategies' },
    { id: 'riskguard', label: 'RiskGuard', path: '/riskguard' },
    { id: 'regime', label: 'Regime Detection', path: '/regime' },
    { id: 'notifications', label: 'Notifications', path: '/notifications' },
    { id: 'calendar', label: 'Calendar', path: '/calendar' },
    { id: 'universe', label: 'Universe', path: '/universe' },
    { id: 'logs', label: 'Logs', path: '/logs' },
    { id: 'docs', label: 'Docs', path: '/docs' }
  ];

  return (
    <nav className="sidebar">
      {tabList.map((tab) => (
        <button
          key={tab.id}
          className={location.pathname === tab.path ? 'active' : ''}
          onClick={() => navigate(tab.path)}
        >
          {tab.label}
        </button>
      ))}
    </nav>
  );
};

const Layout = ({ children }) => (
  <div className="app-container">
    <header>
      <h1>TradeAlert Bot Terminal</h1>
      <div className="header-actions">
        <KillSwitch />
      </div>
    </header>
    <div className="main-layout">
      <NavSidebar />
      <main className="content">
        <ErrorBoundary name="Content Area">
          <Suspense fallback={<div style={{ color: 'white', padding: '20px' }}>Loading Tab Content...</div>}>
            {children}
          </Suspense>
        </ErrorBoundary>
      </main>
    </div>
  </div>
);

const App = () => {
  return (
    <Router>
      <Routes>
        {/* V2 Terminal: Full Screen Experience */}
        <Route path="/v2" element={
          <div className="v2-terminal-wrapper" style={{ height: '100vh', width: '100vw', position: 'relative' }}>
            <button 
                onClick={() => window.location.href = '/'}
                style={{ 
                    position: 'absolute', bottom: '20px', right: '20px', zIndex: 9999, 
                    padding: '5px 10px', background: '#2a2e39', color: '#d1d4dc', 
                    border: '1px solid #4c525e', borderRadius: '4px', cursor: 'pointer', opacity: 0.5 
                }}
            >
                Exit V2
            </button>
            <ErrorBoundary name="V2 Terminal">
              <Suspense fallback={<div style={{ background: '#0a0e17', height: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'white' }}>Loading Terminal Components...</div>}>
                <TradingLayout />
              </Suspense>
            </ErrorBoundary>
          </div>
        } />

        {/* Standard Layout Tabs */}
        <Route path="/" element={<Layout><DashboardTab onSwitchToV2={() => window.location.href = '/v2'} /></Layout>} />
        <Route path="/pnl" element={<Layout><LivePnLTab /></Layout>} />
        <Route path="/trades" element={<Layout><TradesTab /></Layout>} />
        <Route path="/backtest" element={<Layout><BacktestTab /></Layout>} />
        <Route path="/configs" element={<Layout><ConfigsTab /></Layout>} />
        <Route path="/settings" element={<Layout><SystemSettingsTab /></Layout>} />
        <Route path="/strategies" element={<Layout><StrategiesTab /></Layout>} />
        <Route path="/riskguard" element={<Layout><RiskGuardTab /></Layout>} />
        <Route path="/regime" element={<Layout><RegimeTab /></Layout>} />
        <Route path="/notifications" element={<Layout><NotificationsTab /></Layout>} />
        <Route path="/calendar" element={<Layout><CalendarTab /></Layout>} />
        <Route path="/universe" element={<Layout><UniverseTab /></Layout>} />
        <Route path="/logs" element={<Layout><LogsTab /></Layout>} />
        <Route path="/docs" element={<Layout><DocsTab /></Layout>} />
      </Routes>
    </Router>
  );
};

export default App;
