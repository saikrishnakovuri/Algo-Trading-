import React from 'react';
import { NavLink } from 'react-router-dom';
import { 
  LayoutDashboard, 
  History, 
  Bell, 
  PlusCircle, 
  BarChart3, 
  FlaskConical, 
  FastForward, 
  Link,
  Settings,
  ShieldCheck,
  BookOpen,
  Layers,
  FileCode,
  Cpu,
  Bug
} from 'lucide-react';

const Sidebar = () => {
  const navItems = [
    { name: 'Dashboard', path: '/', icon: <LayoutDashboard size={20} /> },
    { name: 'Trades', path: '/trades', icon: <History size={20} /> },
    { name: 'Alert Logs', path: '/alerts', icon: <Bell size={20} /> },
    { name: 'New Trade', path: '/new-trade', icon: <PlusCircle size={20} /> },
    { name: 'Journal', path: '/journal', icon: <BookOpen size={20} /> },
    { name: 'PA Engine', path: '/pa-engine', icon: <ShieldCheck size={20} /> },
    { name: 'Analysis', path: '/analysis', icon: <Layers size={20} /> },
    { name: 'Explorer', path: '/config-explorer', icon: <FileCode size={20} /> },
    { name: 'Analytics', path: '/analytics', icon: <BarChart3 size={20} /> },
    { name: 'Risk Lab', path: '/risk-lab', icon: <FlaskConical size={20} /> },
    { name: 'Backtesting', path: '/backtest', icon: <FastForward size={20} /> },
    { name: 'Control', path: '/control-center', icon: <Cpu size={20} /> },
    { name: 'Integration', path: '/integration', icon: <Link size={20} /> },
    { name: 'Settings', path: '/settings', icon: <Settings size={20} /> },
    
  ];

  return (
    <div className="w-64 bg-[#161b27] border-r border-[#1e2130] flex flex-col h-screen sticky top-0">
      <div className="p-6 border-b border-[#1e2130]">
        <h1 className="text-xl font-bold text-[#00bcd4] tracking-wider">ALGOBOT V3</h1>
      </div>
      <nav className="flex-1 overflow-y-auto p-4 space-y-2">
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) =>
              `flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
                isActive
                  ? 'bg-[#1e2130] text-[#00bcd4] border-l-4 border-[#00bcd4]'
                  : 'text-gray-400 hover:bg-[#1e2130] hover:text-white'
              }`
            }
          >
            <span className="flex-shrink-0">{item.icon}</span>
            <span className="font-medium truncate">{item.name}</span>
          </NavLink>
        ))}
      </nav>
      <div className="p-4 border-t border-[#1e2130]">
        <div className="flex items-center gap-2 px-4 py-2 bg-[#0f1117] rounded-lg">
          <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></div>
          <span className="text-xs text-gray-400">System Live</span>
        </div>
      </div>
    </div>
  );
};

export default Sidebar;
