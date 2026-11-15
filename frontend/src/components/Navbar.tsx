import React from 'react';
import { 
  ShieldAlert, 
  Video, 
  Activity, 
  Car, 
  History, 
  BarChart3, 
  Settings, 
  Radio
} from 'lucide-react';

interface NavbarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  isWsConnected: boolean;
  cameraState: string;
}

export const Navbar: React.FC<NavbarProps> = ({
  activeTab,
  setActiveTab,
  isWsConnected,
  cameraState
}) => {
  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: Activity },
    { id: 'live', label: 'Live Camera', icon: Video },
    { id: 'damage', label: 'Road Damage', icon: ShieldAlert },
    { id: 'objects', label: 'Object Detection', icon: Car },
    { id: 'history', label: 'History', icon: History },
    { id: 'analytics', label: 'Analytics', icon: BarChart3 },
    { id: 'settings', label: 'Settings', icon: Settings },
  ];

  return (
    <header className="border-b border-gray-800 bg-gray-900/80 backdrop-blur sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-lg bg-gradient-to-tr from-cyan-600 to-emerald-500 flex items-center justify-center shadow-lg shadow-cyan-500/20">
            <Radio className="w-6 h-6 text-white animate-pulse" />
          </div>
          <div>
            <h1 className="text-base font-bold text-white tracking-wider font-mono">ROAD•AI INTELLIGENCE</h1>
            <p className="text-xs text-gray-400">CP PLUS CP-E25A SURVEILLANCE</p>
          </div>
        </div>

        {/* Navigation Tabs */}
        <nav className="flex space-x-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`flex items-center space-x-2 px-3 py-2 rounded-md text-xs font-medium transition-all ${
                  isActive
                    ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 shadow-sm shadow-cyan-500/10'
                    : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800/60'
                }`}
              >
                <Icon className={`w-4 h-4 ${isActive ? 'text-cyan-400' : 'text-gray-400'}`} />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>

        {/* Status Pills */}
        <div className="flex items-center space-x-3">
          {/* Camera Status */}
          <div className="flex items-center space-x-2 px-2.5 py-1 rounded-full bg-gray-800 border border-gray-700 text-xs">
            <span className={`w-2 h-2 rounded-full ${cameraState === 'STREAMING' ? 'bg-emerald-400 animate-ping' : 'bg-amber-400'}`} />
            <span className="text-gray-300 font-mono text-[11px]">{cameraState}</span>
          </div>

          {/* WebSocket Status */}
          <div className="flex items-center space-x-2 px-2.5 py-1 rounded-full bg-gray-800 border border-gray-700 text-xs">
            <span className={`w-2 h-2 rounded-full ${isWsConnected ? 'bg-cyan-400' : 'bg-rose-500'}`} />
            <span className="text-gray-300 font-mono text-[11px]">{isWsConnected ? 'LIVE FEED' : 'OFFLINE'}</span>
          </div>
        </div>
      </div>
    </header>
  );
};
