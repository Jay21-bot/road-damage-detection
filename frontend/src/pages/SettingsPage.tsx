import React, { useState, useEffect } from 'react';
import { Settings, Save, Camera, Sliders, CheckCircle2, Server } from 'lucide-react';
import { api } from '../services/api';

export const SettingsPage: React.FC = () => {
  const [backendUrl, setBackendUrl] = useState(api.getBaseUrl());
  const [cameraIp, setCameraIp] = useState('192.168.1.100');
  const [rtspPort, setRtspPort] = useState(554);
  const [onvifPort, setOnvifPort] = useState(8000);
  const [username, setUsername] = useState('admin');
  const [password, setPassword] = useState('');
  const [subtype, setSubtype] = useState(0);
  const [savedMsg, setSavedMsg] = useState(false);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    localStorage.setItem('ROAD_AI_BACKEND_URL', backendUrl);

    try {
      await api.connectCamera({
        ip_address: cameraIp,
        rtsp_port: rtspPort,
        onvif_port: onvifPort,
        username,
        password,
        stream_subtype: subtype
      });
      setSavedMsg(true);
      setTimeout(() => setSavedMsg(false), 4000);
    } catch (e) {
      console.error('Failed to update camera settings:', e);
    }
  };

  return (
    <div className="space-y-6 max-w-4xl">
      <div>
        <h2 className="text-lg font-bold font-mono text-white flex items-center space-x-2">
          <Settings className="w-5 h-5 text-cyan-400" />
          <span>SYSTEM & CAMERA STREAM SETTINGS</span>
        </h2>
        <p className="text-xs text-gray-400">Configure backend API endpoints, CP PLUS camera credentials, and inference profiles</p>
      </div>

      {savedMsg && (
        <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-mono flex items-center space-x-2">
          <CheckCircle2 className="w-4 h-4" />
          <span>Settings successfully applied and camera connection updated.</span>
        </div>
      )}

      <form onSubmit={handleSave} className="space-y-6">
        {/* Backend API Configuration */}
        <div className="p-5 rounded-xl bg-gray-900 border border-gray-800 space-y-4">
          <h3 className="text-sm font-bold font-mono text-gray-300 flex items-center space-x-2">
            <Server className="w-4 h-4 text-cyan-400" />
            <span>BACKEND API ENDPOINT</span>
          </h3>

          <div className="space-y-1.5">
            <label className="text-xs font-mono text-gray-400">FASTAPI SERVER URL</label>
            <input
              type="text"
              value={backendUrl}
              onChange={(e) => setBackendUrl(e.target.value)}
              placeholder="http://localhost:8000"
              className="w-full bg-gray-950 border border-gray-700 rounded-lg px-3 py-2 text-xs font-mono text-white focus:border-cyan-500 focus:outline-none"
            />
            <p className="text-[11px] text-gray-500 font-mono">Used for REST calls and WebSocket streaming (ws:// auto-derived)</p>
          </div>
        </div>

        {/* Camera Connection Configuration */}
        <div className="p-5 rounded-xl bg-gray-900 border border-gray-800 space-y-4">
          <h3 className="text-sm font-bold font-mono text-gray-300 flex items-center space-x-2">
            <Camera className="w-4 h-4 text-emerald-400" />
            <span>CP PLUS CP-E25A CONFIGURATION</span>
          </h3>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label className="text-xs font-mono text-gray-400">CAMERA IP ADDRESS</label>
              <input
                type="text"
                value={cameraIp}
                onChange={(e) => setCameraIp(e.target.value)}
                className="w-full bg-gray-950 border border-gray-700 rounded-lg px-3 py-2 text-xs font-mono text-white focus:border-cyan-500 focus:outline-none"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-mono text-gray-400">RTSP PORT (DEFAULT: 554)</label>
              <input
                type="number"
                value={rtspPort}
                onChange={(e) => setRtspPort(parseInt(e.target.value))}
                className="w-full bg-gray-950 border border-gray-700 rounded-lg px-3 py-2 text-xs font-mono text-white focus:border-cyan-500 focus:outline-none"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-mono text-gray-400">USERNAME</label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full bg-gray-950 border border-gray-700 rounded-lg px-3 py-2 text-xs font-mono text-white focus:border-cyan-500 focus:outline-none"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-mono text-gray-400">PASSWORD</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full bg-gray-950 border border-gray-700 rounded-lg px-3 py-2 text-xs font-mono text-white focus:border-cyan-500 focus:outline-none"
              />
            </div>

            <div className="space-y-1.5 sm:col-span-2">
              <label className="text-xs font-mono text-gray-400">STREAM SUBTYPE</label>
              <select
                value={subtype}
                onChange={(e) => setSubtype(parseInt(e.target.value))}
                className="w-full bg-gray-950 border border-gray-700 rounded-lg px-3 py-2 text-xs font-mono text-white focus:border-cyan-500 focus:outline-none"
              >
                <option value={0}>Main Stream (1080p Full HD - High Precision)</option>
                <option value={1}>Sub Stream (Standard Def 360p - High FPS)</option>
              </select>
            </div>
          </div>
        </div>

        <button
          type="submit"
          className="flex items-center space-x-2 px-5 py-2.5 rounded-lg bg-cyan-500 hover:bg-cyan-400 text-black font-mono font-bold text-xs transition-all shadow-lg shadow-cyan-500/20"
        >
          <Save className="w-4 h-4" />
          <span>SAVE CONFIGURATION</span>
        </button>
      </form>
    </div>
  );
};
