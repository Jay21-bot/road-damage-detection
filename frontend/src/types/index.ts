export interface DetectionItem {
  id: string;
  timestamp: number;
  category: 'road_damage' | 'general_object';
  class_id: number;
  class_name: string;
  confidence: number;
  bbox: [number, number, number, number]; // [x1, y1, x2, y2]
  normalized_bbox: [number, number, number, number]; // [cx, cy, nw, nh]
  snapshot_path?: string | null;
  flagged_for_review?: boolean;
}

export interface CameraStatus {
  state: 'DISCONNECTED' | 'CONNECTING' | 'CONNECTED' | 'STREAMING' | 'RECONNECTING' | 'ERROR';
  active_url: string | null;
  resolution: string;
  fps: number;
  frames_received: number;
  reconnect_attempts: number;
  last_error: string | null;
  last_frame_age_seconds: number | null;
}

export interface SystemHealth {
  status: string;
  uptime_seconds: number;
  cpu_usage_percent: number;
  memory_usage_mb: number;
  memory_percent: number;
  camera_connected: boolean;
  ai_models_loaded: boolean;
  detection_active: boolean;
}

export interface SystemStatistics {
  total_detections: number;
  total_road_damages: number;
  total_objects: number;
  damage_by_class: Record<string, number>;
  objects_by_class: Record<string, number>;
  avg_inference_fps: number;
  system_uptime_seconds: number;
}

export interface DetectionTelemetry {
  event: string;
  timestamp: number;
  frame_id: number;
  fps: number;
  latency_ms: number;
  camera_state: string;
  counts: {
    damages: number;
    objects: number;
    total: number;
  };
  detections: DetectionItem[];
}
