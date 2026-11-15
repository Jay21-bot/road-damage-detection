import React, { useState, useEffect } from 'react';
import { Navbar } from './components/Navbar';
import { DashboardPage } from './pages/DashboardPage';
import { LiveMonitoringPage } from './pages/LiveMonitoringPage';
import { RoadDamagePage } from './pages/RoadDamagePage';
import { ObjectDetectionPage } from './pages/ObjectDetectionPage';
import { HistoryPage } from './pages/HistoryPage';
import { AnalyticsPage } from './pages/AnalyticsPage';
import { SettingsPage } from './pages/SettingsPage';
import { useWebSocket } from './hooks/useWebSocket';
import { api } from './services/api';
import { SystemStatistics, SystemHealth, CameraStatus } from './types';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<string>('dashboard');
  const [stats, setStats] = useState<SystemStatistics | null>(null);
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [camera, setCamera] = useState<CameraStatus | null>(null);

  const { isConnected: isWsConnected, telemetry, latency } = useWebSocket();

  // Periodic polling for aggregate statistics & health
  useEffect(() => {
    const poll = async () => {
      try {
        const [s, h, c] = await Promise.all([
          api.getStatistics(),
          api.getHealth(),
          api.getCameraStatus()
        ]);
        setStats(s);
        setHealth(h);
        setCamera(c);
      } catch (e) {
        console.error('Polling error:', e);
      }
    };
    poll();
    const interval = setInterval(poll, 4000);
    return () => clearInterval(interval);
  }, []);

  const activeDetections = telemetry?.detections || [];
  const currentFps = telemetry?.fps || 0;
  const cameraState = telemetry?.camera_state || camera?.state || 'DISCONNECTED';

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col font-sans hud-grid">
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        isWsConnected={isWsConnected}
        cameraState={cameraState}
      />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {activeTab === 'dashboard' && (
          <DashboardPage
            stats={stats}
            health={health}
            recentDetections={activeDetections}
            fps={currentFps}
            latency={latency}
            cameraState={cameraState}
          />
        )}

        {activeTab === 'live' && (
          <LiveMonitoringPage
            detections={activeDetections}
            fps={currentFps}
            latency={latency}
            cameraState={cameraState}
          />
        )}

        {activeTab === 'damage' && <RoadDamagePage />}

        {activeTab === 'objects' && <ObjectDetectionPage />}

        {activeTab === 'history' && <HistoryPage />}

        {activeTab === 'analytics' && <AnalyticsPage />}

        {activeTab === 'settings' && <SettingsPage />}
      </main>

      <footer className="border-t border-gray-900 bg-gray-950 py-4 text-center text-xs font-mono text-gray-500">
        AI-Based Road Damage Detection & Real-Time Object Recognition System | CP PLUS CP-E25A Open Source
      </footer>
    </div>
  );
};

export default App;
