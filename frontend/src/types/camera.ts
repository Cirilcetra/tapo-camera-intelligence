export type CameraStatus = "online" | "offline" | "error" | "connecting";
export type CameraProvider = "tapo" | "rtsp";
export type PreferredProvider = "auto" | "tapo" | "rtsp";
export type AuthMethod = "camera_account" | "cloud_account";

export interface Camera {
  id: number;
  name: string;
  ip: string;
  username: string;
  rtsp_path: string;
  status: CameraStatus;
  preferred_provider: PreferredProvider;
  provider: CameraProvider;
  auth_method: AuthMethod;
  hls_url: string | null;
  last_seen: string | null;
  created_at: string;
}

export interface CameraCreate {
  name: string;
  ip: string;
  username: string;
  password: string;
  rtsp_path?: string;
  preferred_provider?: PreferredProvider;
  auth_method?: AuthMethod;
}

export type CameraTestPayload = CameraCreate;

export interface StreamInfo {
  hls_url: string;
}
