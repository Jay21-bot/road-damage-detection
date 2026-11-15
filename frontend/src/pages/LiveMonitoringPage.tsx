import React, { useState } from 'react';
import { Video, Sliders, ShieldCheck, Camera } from 'lucide-react';
import { LivePlayer } from '../components/LivePlayer';
import { DetectionItem } from '../types';
import { api } from '../services/api';

interface LiveMonitoringPageProps {
  detections: DetectionItem[];
  fps: number;
  latency: number;
  cameraState: string;
}

export const LiveMonitoringPage: React.FC<LiveMonitoringPageProps> = ({
  detections,
  fps,
  latency,
  cameraState
}) => {
  const [minConf, setMinConf] = useState(0.35);
  const [showPotholes, setShowPotholes] = useState(true);
  const [showObjects, setShowObjects] = useState(true);

  const filteredDetections = detections.filter(d => {
    if (d.confidence < minConf) return false;
    if (d.category === 'road_damage' && !showPotholes) return false;
    if (d.category === 'general_object' && !showObjects) return false;
    return true;
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-bold font-mono text-white flex items-center space-x-2">
            <Video className="w-5 h-5 text-cyan-400" />
            <span>DEDICATED LIVE CAMERA MONITORING</span>
          </h2>
          <p className="text-xs text-gray-400">High-definition real-time surveillance feed with vector bounding box overlay</p>
        </div>

        <div className="flex items-center space-x-3 text-xs font-mono">
          <span className="text-gray-400">MODEL PROFILE:</span>
          <span className="px-2 py-1 rounded bg-gray-800 text-cyan-400 border border-gray-700">DUAL YOLOv8 (640x640)</span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Main Live Monitor (3 Cols) */}
        <div className="lg:col-span-3">
          <LivePlayer
            detections={filteredDetections}
            fps={fps}
            latency={latency}
            cameraState={cameraState}
          />
        </div>

        {/* Live Controls & Layer Toggles (1 Col) */}
        <div className="space-y-4">
          <div className="p-4 rounded-xl bg-gray-900 border border-gray-800 space-y-4">
            <h3 className="text-xs font-bold font-mono text-gray-300 flex items-center space-x-2">
              <Sliders className="w-4 h-4 text-cyan-400" />
              <span>OVERLAY FILTERS</span>
            </h3>

            {/* Confidence Slider */}
            <div className="space-y-2">
              <div className="flex justify-between text-xs font-mono">
                <span className="text-gray-400">MIN CONFIDENCE:</span>
                <span className="text-cyan-400 font-bold">{(minConf * 100).toFixed(0)}%</span>
              </div>
              <input
                type="range"
                min="0.1"
                max="0.9"
                step="0.05"
                value={minConf}
                onChange={(e) => setMinConf(parseFloat(e.target.value))}
                className="w-full accent-cyan-400"
              />
            </div>

            {/* Layer Toggles */}
            <div className="space-y-2.5 pt-2 border-t border-gray-800 text-xs">
              <label className="flex items-center justify-between cursor-pointer">
                <span className="text-rose-400 font-semibold">ROAD DAMAGES (RED)</span>
                <input
                  type="checkbox"
                  checked={showPotholes}
                  onChange={(e) => setShowPotholes(e.target.checked)}
                  className="rounded bg-gray-800 border-gray-700 text-rose-500 focus:ring-0"
                />
              </label>

              <label className="flex items-center justify-between cursor-pointer">
                <span className="text-cyan-400 font-semibold">OBJECTS (CYAN)</span>
                <input
                  type="checkbox"
                  checked={showObjects}
                  onChange={(e) => setShowObjects(e.target.checked)}
                  className="rounded bg-gray-800 border-gray-700 text-cyan-500 focus:ring-0"
                />
              </label>
            </div>
          </div>

          {/* Camera Info Card */}
          <div className="p-4 rounded-xl bg-gray-900 border border-gray-800 text-xs space-y-2">
            <h3 className="text-xs font-bold font-mono text-gray-300 flex items-center space-x-2">
              <Camera className="w-4 h-4 text-emerald-400" />
              <span>HARDWARE TELEMETRY</span>
            </h3>
            <div className="flex justify-between py-1 border-b border-gray-800 text-gray-400">
              <span>DEVICE:</span>
              <span className="text-white font-mono">CP PLUS CP-E25A</span>
            </div>
            <div className="flex justify-between py-1 border-b border-gray-800 text-gray-400">
              <span>PROTOCOL:</span>
              <span className="text-white font-mono">RTSP / ONVIF Profile S</span>
            </div>
            <div className="flex justify-between py-1 text-gray-400">
              <span>COMPRESSION:</span>
              <span className="text-white font-mono">H.264 / MJPEG</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
