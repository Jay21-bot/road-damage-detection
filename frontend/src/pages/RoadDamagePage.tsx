import React, { useState, useEffect } from 'react';
import { ShieldAlert, AlertOctagon, CheckCircle2 } from 'lucide-react';
import { api } from '../services/api';
import { DetectionItem, SystemStatistics } from '../types';

export const RoadDamagePage: React.FC = () => {
  const [damages, setDamages] = useState<DetectionItem[]>([]);
  const [stats, setStats] = useState<SystemStatistics | null>(null);
  const [selectedClass, setSelectedClass] = useState<string>('all');

  useEffect(() => {
    const fetchData = async () => {
      try {
        const detRes = await api.getDetections({ category: 'road_damage', page_size: 50 });
        setDamages(detRes.detections || []);
        const statRes = await api.getStatistics();
        setStats(statRes);
      } catch (e) {
        console.error('Failed to fetch road damage items:', e);
      }
    };
    fetchData();
  }, []);

  const filteredDamages = selectedClass === 'all'
    ? damages
    : damages.filter(d => d.class_name.toLowerCase() === selectedClass.toLowerCase());

  const damageClasses = [
    { id: 'all', label: 'All Damages' },
    { id: 'pothole', label: 'Potholes (D40)' },
    { id: 'longitudinal_crack', label: 'Longitudinal (D00)' },
    { id: 'transverse_crack', label: 'Transverse (D10)' },
    { id: 'alligator_crack', label: 'Alligator (D20)' },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-bold font-mono text-white flex items-center space-x-2">
          <ShieldAlert className="w-5 h-5 text-rose-500" />
          <span>ROAD DAMAGE DETECTION LOGS & GALLERY</span>
        </h2>
        <p className="text-xs text-gray-400">Classified structural asphalt damage from the CP PLUS camera stream</p>
      </div>

      {/* Class Statistics Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl bg-gray-900 border border-gray-800">
          <span className="text-xs font-mono text-gray-400">POTHOLES DETECTED</span>
          <p className="text-2xl font-bold font-mono text-rose-400 mt-1">
            {stats?.damage_by_class['pothole'] || 0}
          </p>
        </div>
        <div className="p-4 rounded-xl bg-gray-900 border border-gray-800">
          <span className="text-xs font-mono text-gray-400">LONGITUDINAL CRACKS</span>
          <p className="text-2xl font-bold font-mono text-amber-400 mt-1">
            {stats?.damage_by_class['longitudinal_crack'] || 0}
          </p>
        </div>
        <div className="p-4 rounded-xl bg-gray-900 border border-gray-800">
          <span className="text-xs font-mono text-gray-400">TRANSVERSE CRACKS</span>
          <p className="text-2xl font-bold font-mono text-amber-400 mt-1">
            {stats?.damage_by_class['transverse_crack'] || 0}
          </p>
        </div>
        <div className="p-4 rounded-xl bg-gray-900 border border-gray-800">
          <span className="text-xs font-mono text-gray-400">ALLIGATOR FATIGUE CRACKS</span>
          <p className="text-2xl font-bold font-mono text-rose-400 mt-1">
            {stats?.damage_by_class['alligator_crack'] || 0}
          </p>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="flex space-x-2 border-b border-gray-800 pb-3">
        {damageClasses.map(cls => (
          <button
            key={cls.id}
            onClick={() => setSelectedClass(cls.id)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium font-mono transition-all ${
              selectedClass === cls.id
                ? 'bg-rose-500/20 text-rose-400 border border-rose-500/40'
                : 'text-gray-400 hover:text-white bg-gray-900 border border-gray-800'
            }`}
          >
            {cls.label}
          </button>
        ))}
      </div>

      {/* Incidents Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredDamages.length === 0 ? (
          <div className="col-span-full py-16 text-center text-xs text-gray-500 font-mono">
            NO ROAD DAMAGE RECORDS MATCHING SELECTION
          </div>
        ) : (
          filteredDamages.map((item) => (
            <div key={item.id} className="p-4 rounded-xl bg-gray-900 border border-gray-800 space-y-3">
              <div className="flex items-center justify-between">
                <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-rose-500 text-white">
                  {item.class_name.toUpperCase()}
                </span>
                <span className="text-xs font-mono text-rose-400 font-semibold">
                  {(item.confidence * 100).toFixed(1)}% CONF
                </span>
              </div>

              <div className="aspect-video bg-gray-950 rounded-lg border border-gray-800 flex items-center justify-center relative overflow-hidden">
                {item.snapshot_path ? (
                  <img src={item.snapshot_path} alt={item.class_name} className="w-full h-full object-cover" />
                ) : (
                  <div className="absolute inset-0 flex items-center justify-center text-gray-700 font-mono text-xs">
                    [INCIDENT CROP: {item.bbox.join(', ')}]
                  </div>
                )}
              </div>

              <div className="text-[11px] font-mono text-gray-400 space-y-1">
                <div className="flex justify-between">
                  <span>RECORD ID:</span>
                  <span className="text-gray-300">{item.id.slice(0, 12)}...</span>
                </div>
                <div className="flex justify-between">
                  <span>TIMESTAMP:</span>
                  <span className="text-gray-300">{new Date(item.timestamp * 1000).toLocaleTimeString()}</span>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
