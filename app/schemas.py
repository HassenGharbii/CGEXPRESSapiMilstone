from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class EventOut(BaseModel):
    id: str
    specversion: Optional[str] = None
    type: Optional[str] = None
    source: Optional[str] = None
    occurred_at: Optional[datetime] = None
    datatype: Optional[str] = None
    data: Optional[Any] = None
    ingested_via: Optional[str] = None
    received_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class EventTypeOut(BaseModel):
    id: str
    name: Optional[str] = None
    display_name: Optional[str] = None
    description: Optional[str] = None
    generator_type: Optional[str] = None
    builtin: Optional[bool] = None

    model_config = {"from_attributes": True}


class AlarmOut(BaseModel):
    id: str
    local_id: Optional[int] = None
    name: Optional[str] = None
    message: Optional[str] = None
    source: Optional[str] = None
    priority_name: Optional[str] = None
    state_name: Optional[str] = None
    occurred_at: Optional[datetime] = None
    last_updated: Optional[datetime] = None

    model_config = {"from_attributes": True}


class SimpleResourceOut(BaseModel):
    id: str
    name: Optional[str] = None
    display_name: Optional[str] = None

    model_config = {"from_attributes": True}


class HealthOut(BaseModel):
    status: str
    websocket_connected: bool
    last_event_received_at: Optional[datetime] = None


class SyncResult(BaseModel):
    event_types: int
    cameras: int
    hardware: int
    recording_servers: int
    sites: int
    alarms: int
    events_backfilled: int
