import { CameraStatus, SystemHealth, SystemStatistics, DetectionItem } from '../types';

const getApiBase = () => {
  return localStorage.getItem('ROAD_AI_BACKEND_URL') || import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
};

export const api = {
  getBaseUrl: getApiBase,

  async getHealth(): Promise<SystemHealth> {
    const res = await fetch(`${getApiBase()}/health`);
    return res.json();
  },

  async getCameraStatus(): Promise<CameraStatus> {
    const res = await fetch(`${getApiBase()}/api/v1/camera/status`);
    return res.json();
  },

  async connectCamera(payload: any) {
    const res = await fetch(`${getApiBase()}/api/v1/camera/connect`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    return res.json();
  },

  async disconnectCamera() {
    const res = await fetch(`${getApiBase()}/api/v1/camera/disconnect`, { method: 'POST' });
    return res.json();
  },

  async startDetection() {
    const res = await fetch(`${getApiBase()}/api/v1/detection/start`, { method: 'POST' });
    return res.json();
  },

  async stopDetection() {
    const res = await fetch(`${getApiBase()}/api/v1/detection/stop`, { method: 'POST' });
    return res.json();
  },

  async getDetectionStatus() {
    const res = await fetch(`${getApiBase()}/api/v1/detection/status`);
    return res.json();
  },

  async getDetections(params: { category?: string; class_name?: string; min_confidence?: number; page?: number; page_size?: number } = {}) {
    const query = new URLSearchParams();
    if (params.category) query.append('category', params.category);
    if (params.class_name) query.append('class_name', params.class_name);
    if (params.min_confidence) query.append('min_confidence', params.min_confidence.toString());
    if (params.page) query.append('page', params.page.toString());
    if (params.page_size) query.append('page_size', params.page_size.toString());

    const res = await fetch(`${getApiBase()}/api/v1/detections?${query.toString()}`);
    return res.json();
  },

  async getStatistics(): Promise<SystemStatistics> {
    const res = await fetch(`${getApiBase()}/api/v1/statistics`);
    return res.json();
  },

  getStreamUrl(): string {
    return `${getApiBase()}/api/v1/camera/stream`;
  },

  getWsUrl(): string {
    const base = getApiBase().replace(/^http/, 'ws');
    return `${base}/ws/detections`;
  }
};
