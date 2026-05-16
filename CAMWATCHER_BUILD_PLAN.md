# CamWatcher — Full Local Build Plan

> AI Intelligence Layer for Existing CCTV Cameras  
> Local-first MVP · No cloud backend · No Supabase · SQLite + FastAPI + Next.js

---

## Project Overview

CamWatcher is an AI-powered monitoring platform that sits on top of existing IP/RTSP cameras (starting with TP-Link Tapo) and transforms them into intelligent, searchable, event-aware systems. The camera hardware is untouched — CamWatcher provides the AI brain.

**Local MVP Goals:**
- Connect to a Tapo (or any RTSP) camera
- Show a live HLS video feed in a web dashboard
- Detect motion via OpenCV
- Capture snapshots on events
- Display an event timeline
- Store everything locally (SQLite + local filesystem)

---

## Technology Decisions (Local MVP)

| Layer | Choice | Reason |
|---|---|---|
| Frontend | Next.js (App Router) + Tailwind | Fast, modern, good for dashboards |
| Backend API | Python FastAPI | Async, lightweight, great for streams |
| Database | SQLite via SQLAlchemy | Zero-setup, local, file-based |
| Stream Ingest | MediaMTX (binary) | RTSP → HLS/WebRTC conversion |
| AI/CV | OpenCV | Motion detection, no GPU needed for MVP |
| Object Detection (later) | YOLOv8 | Plug-in next phase |
| Snapshots | Local filesystem (`/media/snapshots/`) | Simple, no S3 needed |
| Notifications | In-app + WebSocket | Real-time without external services |

---

## Full File Structure

```
camwatcher/
│
├── README.md                          # Project overview and setup guide
├── .env.example                       # Environment variable template
├── docker-compose.yml                 # Optional: run everything together later
│
├── mediamtx/
│   ├── mediamtx.yml                   # MediaMTX config (RTSP → HLS)
│   └── mediamtx                       # MediaMTX binary (downloaded separately)
│
├── media/
│   └── snapshots/                     # All event snapshots stored here
│
├── backend/
│   ├── requirements.txt
│   ├── .env
│   ├── run.py                         # Entry point: starts FastAPI + stream workers
│   │
│   └── app/
│       ├── main.py                    # FastAPI app init, CORS, router mounting
│       ├── config.py                  # Settings from .env (paths, ports, etc.)
│       ├── database.py                # SQLite engine + session + Base
│       │
│       ├── models/
│       │   ├── __init__.py
│       │   ├── camera.py              # Camera ORM model
│       │   └── event.py               # Event ORM model
│       │
│       ├── schemas/
│       │   ├── __init__.py
│       │   ├── camera.py              # Pydantic schemas: CameraCreate, CameraRead
│       │   └── event.py               # Pydantic schemas: EventRead
│       │
│       ├── routes/
│       │   ├── __init__.py
│       │   ├── cameras.py             # CRUD: add/list/delete cameras
│       │   ├── events.py              # List events, get snapshot
│       │   ├── stream.py              # HLS stream URL resolver
│       │   └── ws.py                  # WebSocket: real-time event push
│       │
│       ├── services/
│       │   ├── __init__.py
│       │   ├── camera_service.py      # Camera validation, credential storage
│       │   ├── event_service.py       # Create/query events in DB
│       │   └── notification_service.py # In-app notification logic
│       │
│       ├── streaming/
│       │   ├── __init__.py
│       │   ├── stream_manager.py      # Manages all active stream workers
│       │   └── rtsp_worker.py         # Per-camera RTSP worker (OpenCV loop)
│       │
│       ├── ai/
│       │   ├── __init__.py
│       │   ├── motion_detector.py     # OpenCV frame-diff motion detection
│       │   ├── snapshot_capture.py    # Save frame as JPEG to /media/snapshots/
│       │   └── yolo_detector.py       # (Phase 2) YOLOv8 object detection stub
│       │
│       └── events/
│           ├── __init__.py
│           └── event_bus.py           # Internal pub/sub for event broadcasting
│
└── frontend/
    ├── package.json
    ├── next.config.js
    ├── tailwind.config.js
    ├── tsconfig.json
    ├── .env.local                     # NEXT_PUBLIC_API_URL etc.
    │
    └── src/
        ├── app/
        │   ├── layout.tsx             # Root layout: sidebar + topbar
        │   ├── page.tsx               # Redirect → /dashboard
        │   │
        │   ├── dashboard/
        │   │   └── page.tsx           # Live feed + recent events + stats
        │   │
        │   ├── cameras/
        │   │   ├── page.tsx           # List all cameras + status
        │   │   └── add/
        │   │       └── page.tsx       # Add camera form
        │   │
        │   ├── events/
        │   │   └── page.tsx           # Full event timeline with snapshots
        │   │
        │   └── settings/
        │       └── page.tsx           # App settings (snapshot path, etc.)
        │
        ├── components/
        │   ├── layout/
        │   │   ├── Sidebar.tsx        # Navigation sidebar
        │   │   ├── Topbar.tsx         # Top header bar
        │   │   └── NotificationBell.tsx
        │   │
        │   ├── camera/
        │   │   ├── CameraCard.tsx     # Camera status tile
        │   │   ├── CameraFeed.tsx     # HLS video player (hls.js)
        │   │   ├── AddCameraForm.tsx  # Controlled form with validation
        │   │   └── CameraList.tsx     # Grid of CameraCards
        │   │
        │   ├── events/
        │   │   ├── EventTimeline.tsx  # Scrollable timeline of events
        │   │   ├── EventCard.tsx      # Single event: snapshot + label + time
        │   │   └── EventFilter.tsx    # Filter by type/date/camera
        │   │
        │   └── ui/
        │       ├── Badge.tsx          # Status badges (Online / Motion / Idle)
        │       ├── Button.tsx
        │       ├── Card.tsx
        │       ├── Modal.tsx
        │       ├── Spinner.tsx
        │       └── EmptyState.tsx
        │
        ├── hooks/
        │   ├── useCameras.ts          # Fetch + cache cameras from API
        │   ├── useEvents.ts           # Fetch events with filters
        │   └── useWebSocket.ts        # Connect to WS for real-time events
        │
        ├── lib/
        │   ├── api.ts                 # Axios/fetch wrapper with base URL
        │   └── utils.ts               # Format timestamps, labels, etc.
        │
        └── types/
            ├── camera.ts              # Camera TypeScript types
            └── event.ts               # Event TypeScript types
```

---

## Database Schema (SQLite)

### Table: `cameras`

| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | Auto-increment |
| name | TEXT | User-given name |
| ip | TEXT | Camera local IP |
| rtsp_url | TEXT | Full RTSP URL |
| username | TEXT | RTSP username |
| password_encrypted | TEXT | AES encrypted |
| status | TEXT | `online` / `offline` / `error` |
| created_at | DATETIME | Auto |

### Table: `events`

| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | Auto-increment |
| camera_id | INTEGER FK | References cameras.id |
| type | TEXT | `motion` / `person` / `vehicle` |
| snapshot_path | TEXT | Relative path to JPEG |
| ai_summary | TEXT | AI-generated label (Phase 2) |
| timestamp | DATETIME | When event occurred |
| acknowledged | BOOLEAN | Read/unread state |

---

## API Routes (FastAPI)

### Cameras

```
GET    /api/cameras              → List all cameras
POST   /api/cameras              → Add new camera
GET    /api/cameras/{id}         → Get single camera
DELETE /api/cameras/{id}         → Delete camera
GET    /api/cameras/{id}/stream  → Returns HLS stream URL
```

### Events

```
GET    /api/events               → List events (filters: camera_id, type, date)
GET    /api/events/{id}          → Get single event
GET    /api/events/{id}/snapshot → Serve snapshot image
PATCH  /api/events/{id}/ack      → Acknowledge event
```

### WebSocket

```
WS     /ws/events                → Real-time event stream (pushes new events)
```

### Health

```
GET    /api/health               → { status: ok, cameras_active: N }
```

---

## Stream Architecture (Local)

```
Tapo Camera (RTSP)
    ↓
MediaMTX (running locally on port 8554)
    ↓ converts to HLS
HLS stream at http://localhost:8888/{camera_id}/index.m3u8
    ↓
Frontend: hls.js video player loads HLS URL
    ↓
Live feed in browser
```

**MediaMTX config (`mediamtx/mediamtx.yml`):**
```yaml
paths:
  all:
    source: publisher
    sourceOnDemand: yes
```

Backend stream worker pushes frames into MediaMTX via RTSP re-publish.

---

## Motion Detection Flow

```
rtsp_worker.py
    ↓ reads frames via OpenCV (cv2.VideoCapture)
    ↓ sends frames to motion_detector.py
motion_detector.py
    ↓ frame differencing (background subtraction)
    ↓ if motion_score > threshold:
snapshot_capture.py
    ↓ saves JPEG to /media/snapshots/{camera_id}/{timestamp}.jpg
event_service.py
    ↓ inserts Event row in SQLite
event_bus.py
    ↓ broadcasts to WebSocket clients
Frontend
    ↓ useWebSocket() receives event
    ↓ updates EventTimeline in real-time
```

---

## Frontend Pages Detail

### `/dashboard`
- Live HLS video player for first/selected camera
- Camera selector (if multiple cameras)
- Stats row: events today / cameras online / last motion
- Recent events strip (last 5 events with thumbnails)
- Real-time: WebSocket updates badge count + appends events

### `/cameras`
- Grid of camera cards showing: name, IP, status badge, last event time
- Button to go to Add Camera

### `/cameras/add`
- Form fields: Camera Name, IP Address, RTSP Username, RTSP Password
- "Test Connection" button → calls backend to validate RTSP stream
- Submit → adds camera, starts stream worker

### `/events`
- Full scrollable timeline
- Filter bar: camera dropdown, event type, date range
- Each event card: snapshot thumbnail, camera name, event type badge, timestamp, AI summary (when available)
- Click to expand snapshot full-size

### `/settings`
- Snapshot save path
- Motion detection sensitivity slider
- Notification preferences

---

## Environment Variables

### `backend/.env`
```env
DATABASE_URL=sqlite:///./camwatcher.db
SNAPSHOT_DIR=../media/snapshots
MEDIAMTX_URL=http://localhost:8888
SECRET_KEY=your-secret-key-for-encryption
MOTION_THRESHOLD=5000
FRAME_SKIP=5
```

### `frontend/.env.local`
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000
NEXT_PUBLIC_MEDIAMTX_URL=http://localhost:8888
```

---

## Python Dependencies (`backend/requirements.txt`)

```
fastapi
uvicorn[standard]
sqlalchemy
opencv-python-headless
python-multipart
python-dotenv
cryptography
websockets
Pillow
httpx
pydantic
pydantic-settings
```

---

## Frontend Dependencies (`frontend/package.json`)

```json
{
  "dependencies": {
    "next": "14.x",
    "react": "18.x",
    "react-dom": "18.x",
    "hls.js": "^1.5.x",
    "axios": "^1.6.x",
    "date-fns": "^3.x",
    "lucide-react": "latest",
    "clsx": "^2.x",
    "tailwind-merge": "^2.x"
  },
  "devDependencies": {
    "typescript": "^5.x",
    "@types/react": "^18.x",
    "@types/node": "^20.x",
    "tailwindcss": "^3.x",
    "autoprefixer": "^10.x",
    "postcss": "^8.x"
  }
}
```

---

## Build Phases

### Phase 1 — Foundation (Week 1)
- [ ] Set up folder structure
- [ ] Install and configure MediaMTX
- [ ] FastAPI app skeleton with SQLite
- [ ] Camera model + routes (add/list/delete)
- [ ] RTSP worker (connect via OpenCV, keep-alive loop)
- [ ] Next.js scaffold with Tailwind
- [ ] Sidebar + Topbar layout
- [ ] Add Camera form → calls POST /api/cameras
- [ ] HLS player with hls.js on dashboard

### Phase 2 — Motion & Events (Week 2)
- [ ] Motion detection (OpenCV frame diff)
- [ ] Snapshot capture on motion
- [ ] Event model + DB writes
- [ ] Events API routes
- [ ] WebSocket broadcaster
- [ ] `useWebSocket` hook in frontend
- [ ] Event timeline page with snapshots
- [ ] Real-time event updates on dashboard

### Phase 3 — Polish & AI (Week 3)
- [ ] Camera status polling (online/offline)
- [ ] Event filter (type, camera, date)
- [ ] Acknowledge events (read/unread)
- [ ] Notification bell with unread count
- [ ] YOLOv8 stub → plug into AI pipeline
- [ ] AI summary field populated on events
- [ ] Settings page (sensitivity, paths)

### Phase 4 — AI Features (Week 4+)
- [ ] YOLOv8 object detection (person/vehicle/animal)
- [ ] AI summary generation via OpenAI Vision API
- [ ] Semantic search over events
- [ ] Clip generation (short video around event)

---

## Security Notes (Local)

- RTSP credentials encrypted with `cryptography` (Fernet) before SQLite storage
- RTSP stream never exposed to browser directly — always proxied via MediaMTX → HLS
- No open ports required beyond localhost (8000 for API, 8888 for MediaMTX)
- `.env` files git-ignored

---

## How to Run Locally

```bash
# 1. Start MediaMTX
cd mediamtx && ./mediamtx

# 2. Start Backend
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python run.py

# 3. Start Frontend
cd frontend
npm install
npm run dev
```

Open: `http://localhost:3000`

---

## Key Architectural Principles for Claude to Follow

1. **Browser never touches RTSP directly.** Always: Camera → MediaMTX → HLS → Browser.
2. **SQLite only.** No Postgres, no Supabase, no cloud DB. `camwatcher.db` file in `backend/`.
3. **Local filesystem for snapshots.** Save to `../media/snapshots/{camera_id}/`. Serve via FastAPI static files or dedicated endpoint.
4. **One stream worker per camera.** `stream_manager.py` holds a dict of `{camera_id: RTSPWorker}`. Workers run as asyncio tasks or threads.
5. **Event bus for real-time.** Motion detection → event_bus → WebSocket route → connected frontend clients.
6. **Encryption for credentials.** Use Fernet symmetric encryption. Store key in `.env`.
7. **Pydantic everywhere.** All API inputs/outputs typed with Pydantic schemas. No raw dicts.
8. **Frontend types mirror backend schemas.** Keep `frontend/src/types/` in sync with backend Pydantic models.
9. **No Redux / Zustand for MVP.** Simple React hooks + local state. `useCameras` and `useEvents` hooks handle fetch + cache.
10. **hls.js for video.** Native HLS support only in Safari. Use `hls.js` for cross-browser compatibility.
