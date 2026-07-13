import json
import logging
import ssl
import threading
import time
from datetime import datetime, timezone

import requests

try:
    import websocket
except ImportError:
    websocket = None

from app import config
from app.database import SessionLocal
from app.models import Alarm, Camera, Event, EventType, Hardware, RecordingServer, Site
from app.realtime import broadcaster

logger = logging.getLogger("milestone")


def _parse_time(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


class TokenManager:
    """Holds the current Milestone IDP access token and refreshes it before it expires."""

    def __init__(self):
        self._token = None
        self._expires_at = 0
        self._lock = threading.Lock()

    def get_token(self):
        with self._lock:
            if not self._token or time.time() >= self._expires_at:
                self._authenticate()
            return self._token

    def force_refresh(self):
        with self._lock:
            self._authenticate()
            return self._token

    def _authenticate(self):
        response = requests.post(
            f"{config.SERVER_URL}/IDP/connect/token",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "grant_type": "password",
                "username": config.API_USERNAME,
                "password": config.API_PASSWORD,
                "client_id": "GrantValidatorClient",
            },
            verify=config.VERIFY_CERTIFICATES,
            timeout=15,
        )
        response.raise_for_status()
        payload = response.json()
        token = payload.get("access_token")
        if not token:
            raise RuntimeError("Milestone IDP response did not contain an access_token")
        expires_in = int(payload.get("expires_in", 3600))
        self._token = token
        self._expires_at = time.time() + max(expires_in - config.TOKEN_REFRESH_MARGIN_SECONDS, 30)
        logger.info("Milestone access token refreshed (expires in %ss)", expires_in)


token_manager = TokenManager()


def _get(endpoint):
    url = f"{config.SERVER_URL}{endpoint}"
    headers = {"Authorization": f"Bearer {token_manager.get_token()}"}
    response = requests.get(url, headers=headers, verify=config.VERIFY_CERTIFICATES, timeout=30)
    if response.status_code == 401:
        headers = {"Authorization": f"Bearer {token_manager.force_refresh()}"}
        response = requests.get(url, headers=headers, verify=config.VERIFY_CERTIFICATES, timeout=30)
    response.raise_for_status()
    return response.json().get("array", [])


def _upsert_event(db, item, ingested_via):
    if "id" not in item:
        return
    db.merge(Event(
        id=item["id"],
        specversion=item.get("specversion"),
        type=item.get("type"),
        source=item.get("source"),
        occurred_at=_parse_time(item.get("time")),
        datatype=item.get("datatype"),
        data=item.get("data"),
        raw=item,
        ingested_via=ingested_via,
        received_at=datetime.now(timezone.utc),
    ))


def sync_event_types(db):
    count = 0
    for item in _get("/api/rest/v1/eventTypes"):
        db.merge(EventType(
            id=item["id"],
            name=item.get("name"),
            display_name=item.get("displayName"),
            description=item.get("description"),
            generator_type=item.get("generatorType"),
            generator_name=item.get("generatorName"),
            occurs_globally=item.get("occursGlobally"),
            builtin=item.get("builtIn"),
            source_array=item.get("sourceArray"),
            last_modified=_parse_time(item.get("lastModified")),
            raw=item,
            synced_at=datetime.now(timezone.utc),
        ))
        count += 1
    db.commit()
    return count


def sync_cameras(db):
    count = 0
    for item in _get("/api/rest/v1/cameras"):
        db.merge(Camera(
            id=item["id"],
            name=item.get("name"),
            display_name=item.get("displayName"),
            enabled=item.get("enabled"),
            raw=item,
            synced_at=datetime.now(timezone.utc),
        ))
        count += 1
    db.commit()
    return count


def sync_hardware(db):
    count = 0
    for item in _get("/api/rest/v1/hardware"):
        db.merge(Hardware(
            id=item["id"],
            name=item.get("name"),
            display_name=item.get("displayName"),
            raw=item,
            synced_at=datetime.now(timezone.utc),
        ))
        count += 1
    db.commit()
    return count


def sync_recording_servers(db):
    count = 0
    for item in _get("/api/rest/v1/recordingServers"):
        db.merge(RecordingServer(
            id=item["id"],
            name=item.get("name"),
            display_name=item.get("displayName"),
            host_name=item.get("hostName"),
            raw=item,
            synced_at=datetime.now(timezone.utc),
        ))
        count += 1
    db.commit()
    return count


def sync_sites(db):
    count = 0
    for item in _get("/api/rest/v1/sites"):
        db.merge(Site(
            id=item["id"],
            name=item.get("name"),
            display_name=item.get("displayName"),
            raw=item,
            synced_at=datetime.now(timezone.utc),
        ))
        count += 1
    db.commit()
    return count


def sync_alarms(db):
    count = 0
    for item in _get("/api/rest/v1/alarms"):
        priority = item.get("priority") or {}
        state = item.get("state") or {}
        db.merge(Alarm(
            id=item["id"],
            local_id=item.get("localId"),
            name=item.get("name"),
            message=item.get("message"),
            source=item.get("source"),
            priority_name=priority.get("name"),
            state_name=state.get("name"),
            occurred_at=_parse_time(item.get("time")),
            last_updated=_parse_time(item.get("lastUpdatedTime")),
            raw=item,
            synced_at=datetime.now(timezone.utc),
        ))
        count += 1
    db.commit()
    return count


def sync_events_backfill(db):
    count = 0
    for item in _get("/api/rest/v1/events"):
        _upsert_event(db, item, ingested_via="rest_backfill")
        count += 1
    db.commit()
    return count


def sync_reference_data():
    db = SessionLocal()
    try:
        return {
            "event_types": sync_event_types(db),
            "cameras": sync_cameras(db),
            "hardware": sync_hardware(db),
            "recording_servers": sync_recording_servers(db),
            "sites": sync_sites(db),
            "alarms": sync_alarms(db),
        }
    finally:
        db.close()


def backfill_events(force=False):
    db = SessionLocal()
    try:
        if not force and db.query(Event.id).limit(1).first():
            return 0
        return sync_events_backfill(db)
    finally:
        db.close()


def full_sync(force_events_backfill=False):
    result = sync_reference_data()
    result["events_backfilled"] = backfill_events(force=force_events_backfill)
    return result


class EventStreamListener:
    """Maintains a persistent WebSocket connection to Milestone's Events & State
    API, storing every incoming event straight to Postgres in real time."""

    def __init__(self):
        self._stop = threading.Event()
        self._thread = None
        self._ws = None
        self._connected = False
        self.last_event_at = None

    @property
    def connected(self):
        return self._connected

    def start(self):
        if websocket is None:
            logger.warning("websocket-client not installed; realtime ingestion disabled")
            return
        self._thread = threading.Thread(target=self._run_forever, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._ws:
            self._ws.close()

    def _run_forever(self):
        while not self._stop.is_set():
            try:
                self._connect_once()
            except Exception:
                logger.exception("WebSocket listener crashed, will reconnect")
            self._connected = False
            if not self._stop.is_set():
                time.sleep(config.WS_RECONNECT_DELAY_SECONDS)

    def _connect_once(self):
        ws_url = config.SERVER_URL.replace("https://", "wss://").replace("http://", "ws://")
        url = f"{ws_url}/api/ws/events/v1"
        token = token_manager.get_token()
        headers = [f"Authorization: Bearer {token}"]

        def on_open(ws):
            self._connected = True
            logger.info("Connected to Milestone event stream")
            ws.send(json.dumps({"command": "startSession", "data": {}}))
            ws.send(json.dumps({
                "command": "subscribe",
                "data": {
                    "eventFilter": {
                        "eventType": config.EVENT_TYPE_FILTER,
                        "source": config.EVENT_SOURCE_FILTER,
                    }
                },
            }))
            logger.info("Subscribed to events (type=%s, source=%s)",
                        config.EVENT_TYPE_FILTER, config.EVENT_SOURCE_FILTER)

        def on_message(ws, message):
            self._handle_message(message)

        def on_error(ws, error):
            logger.error("WebSocket error: %s", error)

        def on_close(ws, status_code, msg):
            self._connected = False
            logger.warning("WebSocket closed (%s): %s", status_code, msg)

        self._ws = websocket.WebSocketApp(
            url,
            header=headers,
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close,
        )
        sslopt = None if config.VERIFY_CERTIFICATES else {"cert_reqs": ssl.CERT_NONE}
        self._ws.run_forever(ping_interval=30, ping_timeout=10, sslopt=sslopt)

    def _handle_message(self, raw_message):
        try:
            payload = json.loads(raw_message)
        except (json.JSONDecodeError, TypeError):
            logger.warning("Received non-JSON websocket message: %s", str(raw_message)[:200])
            return

        for event in self._extract_events(payload):
            self._store_event(event)

    @staticmethod
    def _extract_events(payload):
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict):
            if isinstance(payload.get("data"), list):
                return payload["data"]
            if isinstance(payload.get("data"), dict):
                return [payload["data"]]
            if "id" in payload and "type" in payload:
                return [payload]
        logger.debug("Unrecognized websocket payload shape: %s", payload)
        return []

    def _store_event(self, event):
        if "id" not in event:
            return
        db = SessionLocal()
        try:
            _upsert_event(db, event, ingested_via="websocket")
            db.commit()
            self.last_event_at = datetime.now(timezone.utc)
        finally:
            db.close()
        broadcaster.publish(event)


listener = EventStreamListener()
