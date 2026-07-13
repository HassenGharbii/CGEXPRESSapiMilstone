from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB

from app.database import Base


class EventType(Base):
    __tablename__ = "event_types"

    id = Column(String, primary_key=True)
    name = Column(String, index=True)
    display_name = Column(String)
    description = Column(Text)
    generator_type = Column(String)
    generator_name = Column(String)
    occurs_globally = Column(Boolean)
    builtin = Column(Boolean)
    source_array = Column(JSONB)
    last_modified = Column(DateTime(timezone=True))
    raw = Column(JSONB)
    synced_at = Column(DateTime(timezone=True))


class Event(Base):
    __tablename__ = "events"

    id = Column(String, primary_key=True)
    specversion = Column(String)
    type = Column(String, index=True)
    source = Column(String, index=True)
    occurred_at = Column(DateTime(timezone=True), index=True)
    datatype = Column(String)
    data = Column(JSONB, nullable=True)
    raw = Column(JSONB)
    ingested_via = Column(String)
    received_at = Column(DateTime(timezone=True), index=True)


class Alarm(Base):
    __tablename__ = "alarms"

    id = Column(String, primary_key=True)
    local_id = Column(Integer)
    name = Column(String)
    message = Column(Text)
    source = Column(String, index=True)
    priority_name = Column(String)
    state_name = Column(String, index=True)
    occurred_at = Column(DateTime(timezone=True))
    last_updated = Column(DateTime(timezone=True))
    raw = Column(JSONB)
    synced_at = Column(DateTime(timezone=True))


class Camera(Base):
    __tablename__ = "cameras"

    id = Column(String, primary_key=True)
    name = Column(String)
    display_name = Column(String)
    enabled = Column(Boolean)
    raw = Column(JSONB)
    synced_at = Column(DateTime(timezone=True))


class Hardware(Base):
    __tablename__ = "hardware"

    id = Column(String, primary_key=True)
    name = Column(String)
    display_name = Column(String)
    raw = Column(JSONB)
    synced_at = Column(DateTime(timezone=True))


class RecordingServer(Base):
    __tablename__ = "recording_servers"

    id = Column(String, primary_key=True)
    name = Column(String)
    display_name = Column(String)
    host_name = Column(String)
    raw = Column(JSONB)
    synced_at = Column(DateTime(timezone=True))


class Site(Base):
    __tablename__ = "sites"

    id = Column(String, primary_key=True)
    name = Column(String)
    display_name = Column(String)
    raw = Column(JSONB)
    synced_at = Column(DateTime(timezone=True))
