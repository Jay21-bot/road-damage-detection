import React, { useState, useEffect } from 'react';
import { Car, Bike, User, Truck, TrafficCone } from 'lucide-react';
import { api } from '../services/api';
import { DetectionItem, SystemStatistics } from '../types';

export const ObjectDetectionPage: React.FC = () => {
  const [objects, setObjects] = useState<DetectionItem[]>([]);
  const [stats, setStats] = useState<SystemStatistics | null>(null);
  const [selectedClass, setSelectedClass] = useState<string>('all');

  useEffect(() => {
    const fetchData = async () => {
      try {
        const detRes = await api.getDetections({ category: 'general_object', page_size: 50 });
        setObjects(detRes.detections || []);
        const statRes = await api.getStatistics();
        setStats(statRes);
      } catch (e) {
        console.error('Failed to fetch object detection items:', e);
      }
    };
    fetchData();
  }, []);

  const filteredObjects = selectedClass === 'all'
    ? objects
    : objects.filter(d => d.class_name.toLowerCase() === selectedClass.toLowerCase());

  const categories = [
    { id: 'all', label: 'All Objects', icon: TrafficCone },
    { id: 'car', label: 'Cars', icon: Car },
    { id: 'truck', label: 'Trucks', icon: Truck },
    { id: 'motorcycle', label: 'Motorcycles', icon: Bike },
    { id: 'pedestrian', label: 'Pedestrians', icon: User },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-bold font-mono text-white flex items-center space-x-2">
          <Car className="w-5 h-5 text-cyan-400" />
          <span>REAL-TIME OBJECT & VEHICLE RECOGNITION</span>
        </h2>
        <p className="text-xs text-gray-400">Classified urban traffic entities detected by the pretrained YOLO model</p>
      </div>

      {/* Metric Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl bg-gray-900 border border-gray-800">
          <span className="text-xs font-mono text-gray-400">CARS LOGGED</span>
          <p className="text-2xl font-bold font-mono text-cyan-400 mt-1">
            {stats?.objects_by_class['car'] || 0}
          </p>
        </div>
        <div className="p-4 rounded-xl bg-gray-900 border border-gray-800">
          <span className="text-xs font-mono text-gray-400">TRUCKS & BUSES</span>
          <p className="text-2xl font-bold font-mono text-cyan-400 mt-1">
            {(stats?.objects_by_class['truck'] || 0) + (stats?.objects_by_class['bus'] || 0)}
          </p>
        </div>
        <div className="p-4 rounded-xl bg-gray-900 border border-gray-800">
          <span className="text-xs font-mono text-gray-400">MOTORCYCLES / BIKES</span>
          <p className="text-2xl font-bold font-mono text-emerald-400 mt-1">
            {(stats?.objects_by_class['motorcycle'] || 0) + (stats?.objects_by_class['bicycle'] || 0)}
          </p>
        </div>
        <div className="p-4 rounded-xl bg-gray-900 border border-gray-800">
          <span className="text-xs font-mono text-gray-400">PEDESTRIANS</span>
          <p className="text-2xl font-bold font-mono text-amber-400 mt-1">
            {stats?.objects_by_class['pedestrian'] || 0}
          </p>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="flex space-x-2 border-b border-gray-800 pb-3">
        {categories.map(cat => {
          const Icon = cat.icon;
          return (
            <button
              key={cat.id}
              onClick={() => setSelectedClass(cat.id)}
              className={`flex items-center space-x-2 px-3 py-1.5 rounded-lg text-xs font-medium font-mono transition-all ${
                selectedClass === cat.id
                  ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/40'
                  : 'text-gray-400 hover:text-white bg-gray-900 border border-gray-800'
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              <span>{cat.label}</span>
            </button>
          );
        })}
      </div>

      {/* Object Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredObjects.length === 0 ? (
          <div className="col-span-full py-16 text-center text-xs text-gray-500 font-mono">
            NO DETECTED OBJECTS MATCHING FILTER
          </div>
        ) : (
          filteredObjects.map(item => (
            <div key={item.id} className="p-4 rounded-xl bg-gray-900 border border-gray-800 space-y-3">
              <div className="flex items-center justify-between">
                <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-cyan-500 text-black">
                  {item.class_name.toUpperCase()}
                </span>
                <span className="text-xs font-mono text-cyan-400 font-semibold">
                  {(item.confidence * 100).toFixed(1)}% CONF
                </span>
              </div>

              <div className="aspect-video bg-gray-950 rounded-lg border border-gray-800 flex items-center justify-center relative overflow-hidden">
                {item.snapshot_path ? (
                  <img src={item.snapshot_path} alt={item.class_name} className="w-full h-full object-cover" />
                ) : (
                  <div className="text-gray-700 font-mono text-xs">
                    [OBJECT BBOX: {item.bbox.join(', ')}]
                  </div>
                )}
              </div>

              <div className="text-[11px] font-mono text-gray-400 space-y-1">
                <div className="flex justify-between">
                  <span>CLASS ID:</span>
                  <span className="text-gray-300">#{item.class_id}</span>
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
