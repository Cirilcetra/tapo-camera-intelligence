import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import Base, engine

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables (new columns are handled by migrations below)
    Base.metadata.create_all(bind=engine)

    # Idempotent schema migrations (adds AI columns if not present)
    from app.migrations import run_migrations
    run_migrations()

    # Ensure snapshot directory exists
    snap_dir = Path(settings.SNAPSHOT_DIR)
    snap_dir.mkdir(parents=True, exist_ok=True)

    # Wire the asyncio loop into the event bus (for thread→asyncio handoff)
    from app.events.event_bus import event_bus
    event_bus.set_loop(asyncio.get_running_loop())

    # Build the in-memory semantic index from existing embeddings
    from app.ai.semantic_search import semantic_index
    await asyncio.to_thread(semantic_index.build_from_db)

    # Start the AI enrichment worker(s)
    from app.ai.enricher import event_enricher
    await event_enricher.start()

    # Start stream workers for all persisted cameras
    from app.streaming.stream_manager import stream_manager
    await stream_manager.start_all()

    yield

    # Shutdown: stop stream workers first, then enricher
    await stream_manager.stop_all()
    await event_enricher.stop()


app = FastAPI(title="CamWatcher API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve snapshots as static files
snap_dir = Path(settings.SNAPSHOT_DIR)
snap_dir.mkdir(parents=True, exist_ok=True)
app.mount("/media/snapshots", StaticFiles(directory=str(snap_dir)), name="snapshots")

# Routers
from app.routes.health import router as health_router
from app.routes.cameras import router as cameras_router
from app.routes.events import router as events_router
from app.routes.search import router as search_router
from app.routes.ws import router as ws_router
from app.routes.settings import router as settings_router

app.include_router(health_router)
app.include_router(cameras_router)
# search must be registered before events because both share the /api/events prefix
# and /api/events/search would otherwise be shadowed by /api/events/{event_id}
app.include_router(search_router)
app.include_router(events_router)
app.include_router(ws_router)
app.include_router(settings_router)
