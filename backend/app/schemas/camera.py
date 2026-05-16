from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, Field

# "auto"  → probe pytapo first, fall back to RTSP/OpenCV if it fails
# "tapo"  → pytapo required; error out if probe fails
# "rtsp"  → skip pytapo entirely, use RTSP + OpenCV motion
PreferredProvider = Literal["auto", "tapo", "rtsp"]

# How to interpret username/password for the Tapo API
#   "camera_account" → camera-account creds from Tapo app Advanced Settings
#   "cloud_account"  → Tapo app email + password (used as admin + cloud_password)
AuthMethod = Literal["camera_account", "cloud_account"]


class CameraCreate(BaseModel):
    name: str
    ip: str
    username: str
    password: str
    rtsp_path: str = Field(default="stream1")
    preferred_provider: PreferredProvider = Field(default="auto")
    auth_method: AuthMethod = Field(default="camera_account")


class CameraTest(BaseModel):
    ip: str
    username: str
    password: str
    rtsp_path: str = Field(default="stream1")
    preferred_provider: PreferredProvider = Field(default="auto")
    auth_method: AuthMethod = Field(default="camera_account")


class CameraRead(BaseModel):
    id: int
    name: str
    ip: str
    rtsp_url: str
    username: str
    rtsp_path: str
    status: str
    preferred_provider: str
    provider: str
    auth_method: str
    created_at: datetime

    model_config = {"from_attributes": True}
