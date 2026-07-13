import asyncio
import json
import logging
import threading
from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import RedirectResponse, StreamingResponse
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app import config, milestone_client, schemas
from app.database import get_db, init_db
from app.models import Alarm, Camera, Event, EventType, Hardware, RecordingServer, Site
from app.realtime import broadcaster

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    broadcaster.bind_loop(asyncio.get_event_loop())

    try:
        milestone_client.full_sync()
    except Exception:
        logger.exception("Initial sync with Milestone failed; will retry on the periodic schedule")

    stop_sync = threading.Event()

    def _periodic_sync():
        while not stop_sync.wait(config.SYNC_INTERVAL_SECONDS):
            try:
                result = milestone_client.sync_reference_data()
                logger.info("Periodic reference sync complete: %s", result)
            except Exception:
                logger.exception("Periodic sync failed")

    sync_thread = threading.Thread(target=_periodic_sync, daemon=True)
    sync_thread.start()

    if config.ENABLE_WEBSOCKET:
        milestone_client.listener.start()

    yield

    stop_sync.set()
    milestone_client.listener.stop()


app = FastAPI(
    title="Milestone XProtect Event API",
    description=(
        "Realtime events, alarms and configuration data pulled from a Milestone "
        "XProtect VMS (MIP VMS API) and persisted to PostgreSQL. Events arrive "
        "continuously over the Events & State WebSocket API and are stored as "
        "soon as they are received."
    ),
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docs")


@app.get("/health", response_model=schemas.HealthOut, tags=["system"])
def health():
    return schemas.HealthOut(
        status="ok",
        websocket_connected=milestone_client.listener.connected,
        last_event_received_at=milestone_client.listener.last_event_at,
    )


@app.post("/sync", response_model=schemas.SyncResult, tags=["system"])
def trigger_sync(force_events_backfill: bool = False):
    try:
        return milestone_client.full_sync(force_events_backfill=force_events_backfill)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Sync with Milestone failed: {exc}")


@app.get("/events", response_model=List[schemas.EventOut], tags=["events"])
def list_events(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    type: Optional[str] = Query(None, description="Filter by Milestone event type id"),
    source: Optional[str] = Query(None, description="Filter by source substring, e.g. 'cameras/'"),
    db: Session = Depends(get_db),
):
    query = db.query(Event)
    if type:
        query = query.filter(Event.type == type)
    if source:
        query = query.filter(Event.source.ilike(f"%{source}%"))
    return query.order_by(desc(Event.occurred_at)).offset(offset).limit(limit).all()


@app.get("/events/stream", tags=["events"])
async def stream_events():
    async def gen():
        async for event in broadcaster.subscribe():
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")


@app.get("/events/{event_id}", response_model=schemas.EventOut, tags=["events"])
def get_event(event_id: str, db: Session = Depends(get_db)):
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


@app.get("/event-types", response_model=List[schemas.EventTypeOut], tags=["configuration"])
def list_event_types(search: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(EventType)
    if search:
        query = query.filter(EventType.display_name.ilike(f"%{search}%"))
    return query.order_by(EventType.display_name).all()


@app.get("/alarms", response_model=List[schemas.AlarmOut], tags=["alarms"])
def list_alarms(state: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(Alarm)
    if state:
        query = query.filter(Alarm.state_name == state)
    return query.order_by(desc(Alarm.occurred_at)).all()


@app.get("/cameras", response_model=List[schemas.SimpleResourceOut], tags=["configuration"])
def list_cameras(db: Session = Depends(get_db)):
    return db.query(Camera).order_by(Camera.display_name).all()


@app.get("/hardware", response_model=List[schemas.SimpleResourceOut], tags=["configuration"])
def list_hardware(db: Session = Depends(get_db)):
    return db.query(Hardware).order_by(Hardware.display_name).all()


@app.get("/recording-servers", response_model=List[schemas.SimpleResourceOut], tags=["configuration"])
def list_recording_servers(db: Session = Depends(get_db)):
    return db.query(RecordingServer).order_by(RecordingServer.display_name).all()


@app.get("/sites", response_model=List[schemas.SimpleResourceOut], tags=["configuration"])
def list_sites(db: Session = Depends(get_db)):
    return db.query(Site).order_by(Site.display_name).all()
