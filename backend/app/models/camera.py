from datetime import datetime
from sqlalchemy import Integer, String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Camera(Base):
    __tablename__ = "cameras"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    ip: Mapped[str] = mapped_column(String, nullable=False)
    rtsp_url: Mapped[str] = mapped_column(String, nullable=False)
    username: Mapped[str] = mapped_column(String, nullable=False)
    password_encrypted: Mapped[str] = mapped_column(String, nullable=False)
    rtsp_path: Mapped[str] = mapped_column(String, nullable=False, default="stream1")
    status: Mapped[str] = mapped_column(String, nullable=False, default="offline")
    # User-chosen mode: "auto" | "tapo" | "rtsp"
    preferred_provider: Mapped[str] = mapped_column(String, nullable=False, default="auto")
    # Resolved mode after startup probe: "tapo" | "rtsp"
    provider: Mapped[str] = mapped_column(String, nullable=False, default="rtsp")
    # How to interpret username/password for the Tapo API:
    #   "camera_account" → username/password are the camera-account creds from the
    #     Tapo app's Advanced Settings. Used for both RTSP and pytapo.
    #   "cloud_account"  → username is the Tapo app email, password is the Tapo app
    #     password. pytapo uses these as `admin` + cloud_password. RTSP will only
    #     work if the camera-account is also enabled in the Tapo app.
    auth_method: Mapped[str] = mapped_column(String, nullable=False, default="camera_account")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
