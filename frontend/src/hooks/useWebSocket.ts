import { useState, useEffect, useRef, useCallback } from 'react';
import { DetectionTelemetry } from '../types';
import { api } from '../services/api';

export function useWebSocket() {
  const [isConnected, setIsConnected] = useState(false);
  const [telemetry, setTelemetry] = useState<DetectionTelemetry | null>(null);
  const [latency, setLatency] = useState(0);
  const [cameraStatus, setCameraStatus] = useState<any | null>(null);
  const [isAiActive, setIsAiActive] = useState<boolean>(true);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>();

  const connect = useCallback(() => {
    try {
      const url = api.getWsUrl();
      const ws = new WebSocket(url);

      ws.onopen = () => {
        setIsConnected(true);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.event === 'DETECTION_UPDATE') {
            setTelemetry(data);
            if (data.latency_ms) setLatency(data.latency_ms);
          } else if (data.event === 'CAMERA_STATUS_CHANGED') {
            setCameraStatus(data.camera);
          } else if (data.event === 'DETECTION_STATE_CHANGED') {
            setIsAiActive(data.detection_active);
          } else if (data.event === 'HANDSHAKE_ACK') {
            if (data.camera_status) setCameraStatus(data.camera_status);
          }
        } catch (e) {
          console.error('Failed to parse WebSocket JSON:', e);
        }
      };

      ws.onclose = () => {
        setIsConnected(false);
        // Auto-reconnect with exponential backoff
        reconnectTimeoutRef.current = setTimeout(connect, 3000);
      };

      ws.onerror = () => {
        ws.close();
      };

      wsRef.current = ws;
    } catch (e) {
      setIsConnected(false);
      reconnectTimeoutRef.current = setTimeout(connect, 3000);
    }
  }, []);

  const sendCommand = (command: string, payload: any = {}) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ command, ...payload }));
    }
  };

  useEffect(() => {
    connect();
    return () => {
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      if (wsRef.current) wsRef.current.close();
    };
  }, [connect]);

  return { isConnected, telemetry, latency, cameraStatus, isAiActive, sendCommand };
}
