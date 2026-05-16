from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).parent.parent / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    DATABASE_URL: str = "sqlite:///./camwatcher.db"
    SNAPSHOT_DIR: str = "../media/snapshots"

    MEDIAMTX_URL: str = "http://localhost:8888"
    MEDIAMTX_API_URL: str = "http://localhost:9997"
    MEDIAMTX_RTSP_URL: str = "rtsp://localhost:8554"

    SECRET_KEY: str = "change-me"
    MOTION_THRESHOLD: int = 5000
    FRAME_SKIP: int = 5

    # pytapo event polling
    TAPO_POLL_INTERVAL: float = 2.0          # seconds between getEvents calls
    TAPO_EVENT_LOOKBACK_SECONDS: int = 10    # initial history window on startup

    # AI enrichment
    OPENAI_API_KEY: str = ""
    OPENAI_VISION_MODEL: str = "gpt-4o-mini"
    OPENAI_EMBED_MODEL: str = "text-embedding-3-small"
    AI_ENRICHMENT_ENABLED: bool = True
    AI_ENRICHMENT_CONCURRENCY: int = 2


settings = Settings()
