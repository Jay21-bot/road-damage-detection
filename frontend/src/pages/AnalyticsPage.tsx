import React, { useState, useEffect } from 'react';
import { BarChart3, PieChart, TrendingUp, AlertTriangle } from 'lucide-react';
import { api } from '../services/api';
import { SystemStatistics } from '../types';

export const AnalyticsPage: React.FC = () => {
  const [stats, setStats] = useState<SystemStatistics | null>(null);

  useEffect(() => {
    api.getStatistics().then(setStats).catch(console.error);
  }, []);

  const totalDetections = stats?.total_detections || 1;
  const damageTotal = stats?.total_road_damages || 0;
  const objectTotal = stats?.total_objects || 0;

  const damageShare = ((damageTotal / totalDetections) * 100).toFixed(1);
  const objectShare = ((objectTotal / totalDetections) * 100).toFixed(1);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-bold font-mono text-white flex items-center space-x-2">
          <BarChart3 className="w-5 h-5 text-cyan-400" />
          <span>ROAD INTELLIGENCE & TRAFFIC ANALYTICS</span>
        </h2>
        <p className="text-xs text-gray-400">Aggregated statistical breakdown of anomalies, vehicles, and surveillance trends</p>
      </div>

      {/* Top Ratio Progress Bar */}
      <div className="p-4 rounded-xl bg-gray-900 border border-gray-800 space-y-3">
        <div className="flex justify-between text-xs font-mono">
          <span className="text-rose-400 font-semibold">ROAD DAMAGES: {damageTotal} ({damageShare}%)</span>
          <span className="text-cyan-400 font-semibold">TRAFFIC OBJECTS: {objectTotal} ({objectShare}%)</span>
        </div>
        <div className="w-full h-3 bg-gray-800 rounded-full overflow-hidden flex">
          <div style={{ width: `${damageShare}%` }} className="bg-rose-500 h-full transition-all duration-500" />
          <div style={{ width: `${objectShare}%` }} className="bg-cyan-500 h-full transition-all duration-500" />
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Road Damage Breakdown */}
        <div className="p-5 rounded-xl bg-gray-900 border border-gray-800 space-y-4">
          <h3 className="text-sm font-bold font-mono text-rose-400 flex items-center space-x-2">
            <AlertTriangle className="w-4 h-4 text-rose-500" />
            <span>ROAD DAMAGE CATEGORIES</span>
          </h3>

          <div className="space-y-3 text-xs font-mono">
            {Object.entries(stats?.damage_by_class || {
              pothole: 0,
              longitudinal_crack: 0,
              transverse_crack: 0,
              alligator_crack: 0
            }).map(([name, count]) => {
              const pct = damageTotal > 0 ? ((count / damageTotal) * 100).toFixed(0) : 0;
              return (
                <div key={name} className="space-y-1">
                  <div className="flex justify-between text-gray-300">
                    <span className="uppercase">{name.replace('_', ' ')}</span>
                    <span className="text-rose-400 font-bold">{count} ({pct}%)</span>
                  </div>
                  <div className="w-full h-2 bg-gray-800 rounded-full overflow-hidden">
                    <div style={{ width: `${pct}%` }} className="bg-rose-500 h-full" />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Traffic Object Breakdown */}
        <div className="p-5 rounded-xl bg-gray-900 border border-gray-800 space-y-4">
          <h3 className="text-sm font-bold font-mono text-cyan-400 flex items-center space-x-2">
            <TrendingUp className="w-4 h-4 text-cyan-400" />
            <span>TRAFFIC ENTITIES DISTRIBUTION</span>
          </h3>

          <div className="space-y-3 text-xs font-mono">
            {Object.entries(stats?.objects_by_class || {
              car: 0,
              truck: 0,
              bus: 0,
              motorcycle: 0,
              pedestrian: 0
            }).map(([name, count]) => {
              const pct = objectTotal > 0 ? ((count / objectTotal) * 100).toFixed(0) : 0;
              return (
                <div key={name} className="space-y-1">
                  <div className="flex justify-between text-gray-300">
                    <span className="uppercase">{name}</span>
                    <span className="text-cyan-400 font-bold">{count} ({pct}%)</span>
                  </div>
                  <div className="w-full h-2 bg-gray-800 rounded-full overflow-hidden">
                    <div style={{ width: `${pct}%` }} className="bg-cyan-500 h-full" />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
};
