import React from 'react';
import { ShieldAlert, Car, Cpu, Radio, Zap, AlertTriangle, ArrowUpRight } from 'lucide-react';
import { SystemStatistics, SystemHealth, DetectionItem } from '../types';
import { LivePlayer } from '../components/LivePlayer';

interface DashboardPageProps {
  stats: SystemStatistics | null;
  health: SystemHealth | null;
  recentDetections: DetectionItem[];
  fps: number;
  latency: number;
  cameraState: string;
}

export const DashboardPage: React.FC<DashboardPageProps> = ({
  stats,
  health,
  recentDetections,
  fps,
  latency,
  cameraState
}) => {
  const damageCount = stats?.total_road_damages || 0;
  const objectCount = stats?.total_objects || 0;
  const totalCount = stats?.total_detections || 0;

  return (
    <div className="space-y-6">
      {/* Metric Cards Row */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {/* Total Detections */}
        <div className="p-4 rounded-xl bg-gray-900 border border-gray-800 relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono text-gray-400">TOTAL DETECTIONS</span>
            <Zap className="w-4 h-4 text-cyan-400" />
          </div>
          <p className="text-2xl font-bold font-mono text-white mt-2">{totalCount.toLocaleString()}</p>
          <div className="mt-2 flex items-center text-xs text-emerald-400">
            <ArrowUpRight className="w-3.5 h-3.5 mr-1" />
            <span>Active Real-Time Stream</span>
          </div>
        </div>

        {/* Road Damages */}
        <div className="p-4 rounded-xl bg-gray-900 border border-rose-950/60 relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono text-rose-400">ROAD DAMAGE ALERTS</span>
            <ShieldAlert className="w-4 h-4 text-rose-500" />
          </div>
          <p className="text-2xl font-bold font-mono text-rose-400 mt-2">{damageCount.toLocaleString()}</p>
          <div className="mt-2 text-xs text-gray-400">
            Potholes & Surface Cracks
          </div>
        </div>

        {/* Objects Detected */}
        <div className="p-4 rounded-xl bg-gray-900 border border-cyan-950/60 relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono text-cyan-400">TRAFFIC OBJECTS</span>
            <Car className="w-4 h-4 text-cyan-400" />
          </div>
          <p className="text-2xl font-bold font-mono text-cyan-400 mt-2">{objectCount.toLocaleString()}</p>
          <div className="mt-2 text-xs text-gray-400">
            Vehicles, Pedestrians, Signs
          </div>
        </div>

        {/* System & AI Health */}
        <div className="p-4 rounded-xl bg-gray-900 border border-gray-800 relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono text-gray-400">ENGINE LATENCY</span>
            <Cpu className="w-4 h-4 text-emerald-400" />
          </div>
          <p className="text-2xl font-bold font-mono text-emerald-400 mt-2">{latency.toFixed(1)} ms</p>
          <div className="mt-2 text-xs text-gray-400 font-mono">
            {fps.toFixed(1)} FPS | {health?.memory_usage_mb || 0} MB RAM
          </div>
        </div>
      </div>

      {/* Main Grid: Stream & Activity Feed */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Live Surveillance Feed */}
        <div className="lg:col-span-2 space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-bold font-mono uppercase tracking-wider text-gray-300 flex items-center space-x-2">
              <Radio className="w-4 h-4 text-emerald-400" />
              <span>LIVE CP PLUS CP-E25A STREAM</span>
            </h2>
            <span className="text-xs font-mono text-gray-400">1080p DUAL YOLO INFERENCE</span>
          </div>

          <LivePlayer
            detections={recentDetections}
            fps={fps}
            latency={latency}
            cameraState={cameraState}
          />
        </div>

        {/* Real-Time Detection Feed */}
        <div className="space-y-3">
          <h2 className="text-sm font-bold font-mono uppercase tracking-wider text-gray-300 flex items-center space-x-2">
            <AlertTriangle className="w-4 h-4 text-amber-400" />
            <span>INCIDENT LOG FEED</span>
          </h2>

          <div className="rounded-xl border border-gray-800 bg-gray-900/60 p-3 h-[420px] overflow-y-auto space-y-2.5">
            {recentDetections.length === 0 ? (
              <div className="h-full flex items-center justify-center text-xs text-gray-500 font-mono">
                AWAITING DETECTION EVENTS...
              </div>
            ) : (
              recentDetections.map((det) => {
                const isDamage = det.category === 'road_damage';
                return (
                  <div
                    key={det.id}
                    className={`p-2.5 rounded-lg border text-xs flex items-center justify-between transition-all ${
                      isDamage
                        ? 'bg-rose-950/20 border-rose-800/40 text-rose-200'
                        : 'bg-cyan-950/20 border-cyan-800/40 text-cyan-200'
                    }`}
                  >
                    <div>
                      <span className={`px-1.5 py-0.5 rounded text-[10px] font-mono font-bold mr-2 ${
                        isDamage ? 'bg-rose-500 text-white' : 'bg-cyan-500 text-black'
                      }`}>
                        {isDamage ? 'DAMAGE' : 'OBJECT'}
                      </span>
                      <span className="font-semibold">{det.class_name.toUpperCase()}</span>
                    </div>

                    <div className="text-right font-mono">
                      <span className="text-gray-300 font-bold">{(det.confidence * 100).toFixed(0)}%</span>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
