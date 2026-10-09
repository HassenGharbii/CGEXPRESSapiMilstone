from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import DATABASE_URL

engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()

# Columns added after the initial table creation. create_all() only creates
# missing tables, so existing deployments need these added explicitly.
_MIGRATIONS = [
    "ALTER TABLE cameras ADD COLUMN IF NOT EXISTS hardware_id VARCHAR",
    "ALTER TABLE hardware ADD COLUMN IF NOT EXISTS address VARCHAR",
]


def init_db():
    from app import models  # noqa: F401  (register models on Base before create_all)

    Base.metadata.create_all(bind=engine)

    with engine.begin() as conn:
        for statement in _MIGRATIONS:
            conn.execute(text(statement))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
