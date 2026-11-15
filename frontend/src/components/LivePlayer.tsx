import React, { useRef, useState, useEffect } from 'react';
import { Play, Pause, Maximize2, RefreshCw, Eye, EyeOff } from 'lucide-react';
import { api } from '../services/api';
import { DetectionItem } from '../types';

interface LivePlayerProps {
  detections: DetectionItem[];
  fps: number;
  latency: number;
  cameraState: string;
}

export const LivePlayer: React.FC<LivePlayerProps> = ({
  detections,
  fps,
  latency,
  cameraState
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [isPlaying, setIsPlaying] = useState(true);
  const [showOverlay, setShowOverlay] = useState(false); // Disabled by default to avoid duplicate bounding boxes over MJPEG stream
  const [streamUrl, setStreamUrl] = useState(api.getStreamUrl());

  const handleToggleDetection = async () => {
    if (isPlaying) {
      await api.stopDetection();
      setIsPlaying(false);
    } else {
      await api.startDetection();
      setIsPlaying(true);
    }
  };

  const handleRefreshStream = () => {
    setStreamUrl(`${api.getStreamUrl()}?t=${Date.now()}`);
  };

  const toggleFullscreen = () => {
    if (!containerRef.current) return;
    if (!document.fullscreenElement) {
      containerRef.current.requestFullscreen();
    } else {
      document.exitFullscreen();
    }
  };

  // Render synchronized vector bounding boxes onto the canvas
  useEffect(() => {
    if (!showOverlay || !canvasRef.current) return;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    detections.forEach((det) => {
      const [cx, cy, nw, nh] = det.normalized_bbox;
      const x = (cx - nw / 2) * canvas.width;
      const y = (cy - nh / 2) * canvas.height;
      const w = nw * canvas.width;
      const h = nh * canvas.height;

      const isDamage = det.category === 'road_damage';
      const color = isDamage ? '#ff2a55' : '#00e5ff';

      // Draw box
      ctx.strokeStyle = color;
      ctx.lineWidth = 2;
      ctx.strokeRect(x, y, w, h);

      // Label background
      ctx.fillStyle = color;
      const label = `${isDamage ? '[DMG]' : '[OBJ]'} ${det.class_name.toUpperCase()} ${(det.confidence * 100).toFixed(0)}%`;
      ctx.font = '11px JetBrains Mono, monospace';
      const textW = ctx.measureText(label).width;
      ctx.fillRect(x, Math.max(0, y - 18), textW + 8, 18);

      // Label text
      ctx.fillStyle = '#ffffff';
      ctx.fillText(label, x + 4, Math.max(12, y - 5));
    });
  }, [detections, showOverlay]);

  return (
    <div ref={containerRef} className="relative rounded-xl overflow-hidden border border-gray-800 bg-gray-950 shadow-2xl group">
      {/* Video Stream Element */}
      <div className="relative aspect-video w-full bg-black flex items-center justify-center">
        <img
          src={streamUrl}
          alt="CP PLUS Live Surveillance Feed"
          className="w-full h-full object-contain"
          onError={(e) => {
            (e.target as HTMLImageElement).src = 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="640" height="360" viewBox="0 0 640 360"><rect width="100%" height="100%" fill="%23111827"/><text x="50%" y="50%" fill="%23ef4444" font-family="sans-serif" font-size="16" text-anchor="middle">STREAM SIGNAL DISCONNECTED</text></svg>';
          }}
        />

        {/* Vector Canvas Overlay for Crisp Bounding Boxes */}
        <canvas
          ref={canvasRef}
          width={1280}
          height={720}
          className={`absolute inset-0 w-full h-full pointer-events-none ${showOverlay ? 'block' : 'hidden'}`}
        />

        {/* Tactical HUD Header Overlay */}
        <div className="absolute top-3 left-3 right-3 flex items-center justify-between pointer-events-none">
          <div className="flex items-center space-x-2 bg-gray-900/80 backdrop-blur px-3 py-1.5 rounded-lg border border-gray-700/60 font-mono text-xs text-gray-300">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <span className="text-emerald-400 font-semibold">CP-E25A</span>
            <span className="text-gray-500">|</span>
            <span>{fps.toFixed(1)} FPS</span>
            <span className="text-gray-500">|</span>
            <span>{latency.toFixed(1)}ms</span>
          </div>

          <div className="bg-gray-900/80 backdrop-blur px-3 py-1.5 rounded-lg border border-gray-700/60 font-mono text-xs text-cyan-400">
            ACTIVE DETECTIONS: {detections.length}
          </div>
        </div>

        {/* Video Control Bar (Auto-reveals on hover) */}
        <div className="absolute bottom-3 left-3 right-3 flex items-center justify-between p-2.5 rounded-lg bg-gray-900/90 backdrop-blur border border-gray-800 transition-opacity opacity-90 group-hover:opacity-100">
          <div className="flex items-center space-x-2">
            <button
              onClick={handleToggleDetection}
              className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-md text-xs font-semibold font-mono transition-all ${
                isPlaying
                  ? 'bg-rose-500/20 text-rose-400 border border-rose-500/40 hover:bg-rose-500/30'
                  : 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40 hover:bg-emerald-500/30'
              }`}
            >
              {isPlaying ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
              <span>{isPlaying ? 'PAUSE AI' : 'RESUME AI'}</span>
            </button>

            <button
              onClick={() => setShowOverlay(!showOverlay)}
              className="px-2.5 py-1.5 rounded-md bg-gray-800 text-gray-300 hover:text-white text-xs flex items-center space-x-1 border border-gray-700"
            >
              {showOverlay ? <Eye className="w-3.5 h-3.5 text-cyan-400" /> : <EyeOff className="w-3.5 h-3.5 text-gray-500" />}
              <span className="font-mono">{showOverlay ? 'HUD ON' : 'HUD OFF'}</span>
            </button>
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={handleRefreshStream}
              title="Reload Stream"
              className="p-1.5 rounded-md bg-gray-800 text-gray-400 hover:text-white border border-gray-700"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
            <button
              onClick={toggleFullscreen}
              title="Full Screen"
              className="p-1.5 rounded-md bg-gray-800 text-gray-400 hover:text-white border border-gray-700"
            >
              <Maximize2 className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
