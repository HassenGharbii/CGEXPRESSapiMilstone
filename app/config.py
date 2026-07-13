import os


def _bool(name, default):
    return os.getenv(name, str(default)).lower() in ("1", "true", "yes")


API_USERNAME = os.getenv("API_USERNAME", "axone")
API_PASSWORD = os.getenv("API_PASSWORD", "Ax0nesys!")
SERVER_URL = os.getenv("SERVER_URL", "http://192.168.20.1").rstrip("/")
VERIFY_CERTIFICATES = _bool("VERIFY_CERTIFICATES", True)

EVENT_TYPE_FILTER = os.getenv("EVENT_TYPE_FILTER", "*")
EVENT_SOURCE_FILTER = os.getenv("EVENT_SOURCE_FILTER", "*")

ENABLE_WEBSOCKET = _bool("ENABLE_WEBSOCKET", True)
WS_RECONNECT_DELAY_SECONDS = int(os.getenv("WS_RECONNECT_DELAY_SECONDS", "5"))
TOKEN_REFRESH_MARGIN_SECONDS = int(os.getenv("TOKEN_REFRESH_MARGIN_SECONDS", "60"))

SYNC_INTERVAL_SECONDS = int(os.getenv("SYNC_INTERVAL_SECONDS", "300"))

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://milestone:milestone@db:6623/milestone",
)
