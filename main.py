import os
import requests
import logging
import json
import threading
from requests.exceptions import RequestException

try:
    import websocket
except ImportError:
    websocket = None

USERNAME = os.getenv("API_USERNAME", "axone")
PASSWORD = os.getenv("API_PASSWORD", "Ax0nesys!")
SERVER_URL = os.getenv("SERVER_URL", "http://192.168.20.1")
VERIFY_CERTIFICATES = os.getenv("VERIFY_CERTIFICATES", "True") == "True"
RECORDING_SERVER_ID = os.getenv("RECORDING_SERVER_ID", "27ed6e15-babf-4c4f-a86e-cf3d2a188ec1")
DATA_DIR = os.getenv("DATA_DIR", "data")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_access_token(session):
    try:
        response = session.post(
            f"{SERVER_URL}/IDP/connect/token",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "grant_type": "password",
                "username": USERNAME,
                "password": PASSWORD,
                "client_id": "GrantValidatorClient",
            },
            verify=VERIFY_CERTIFICATES,
        )
        response.raise_for_status()
        token = response.json().get("access_token")
        if not token:
            logger.error("Access token not found in the response.")
            return None
        logger.info("Access token retrieved successfully.")

        with open("access_token.txt", "w") as file:
            file.write(token)
        logger.info("Access token saved to 'access_token.txt'.")

        return token
    except RequestException as e:
        logger.error(f"Error retrieving token: {e}")
        return None


def fetch_and_save_data(endpoint, filename, token):
    try:
        url = f"{SERVER_URL}{endpoint}"
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(url, headers=headers, verify=VERIFY_CERTIFICATES)
        response.raise_for_status()
        data = response.json()

        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR)

        filepath = os.path.join(DATA_DIR, f"{filename}.json")
        with open(filepath, "w") as file:
            json.dump(data, file, indent=4)
        logger.info(f"Data saved to '{filepath}'")
    except RequestException as e:
        logger.error(f"Error fetching data from {endpoint}: {e}")


def run_rest_api():
    with requests.Session() as session:
        token = get_access_token(session)
        if not token:
            logger.error("Failed to retrieve access token. Exiting.")
            return

        fetch_and_save_data("/api/rest/v1/events", "events", token)
        fetch_and_save_data("/api/rest/v1/eventTypes", "event_types", token)
        fetch_and_save_data("/api/rest/v1/alarms", "alarms", token)
        fetch_and_save_data("/api/rest/v1/recordingServers", "recording_servers", token)
        fetch_and_save_data("/api/rest/v1/system", "system_info", token)
        fetch_and_save_data("/api/rest/v1/system/health", "system_health", token)

        storage_endpoint = f"/api/rest/v1/recordingServers/{RECORDING_SERVER_ID}/storage"
        fetch_and_save_data(storage_endpoint, "recording_server_storage", token)

        logger.info("All data has been retrieved and saved successfully.")


def on_message(ws, message):
    data = json.loads(message)
    print(f"Received data: {json.dumps(data, indent=2)}")


def on_error(ws, error):
    print(f"WebSocket error: {error}")


def on_close(ws, close_status_code, close_msg):
    print(f"WebSocket closed with status: {close_status_code}, message: {close_msg}")


def on_open(ws):
    print("WebSocket connection established.")
    start_session_message = {"command": "startSession", "data": {}}
    ws.send(json.dumps(start_session_message))
    print("Session started.")

    subscribe_message = {
        "command": "subscribe",
        "data": {"eventFilter": {"eventType": "*", "source": "*"}},
    }
    ws.send(json.dumps(subscribe_message))
    print("Subscribed to all events.")


def run_websocket(token):
    if websocket is None:
        logger.warning("websocket-client not installed, skipping WebSocket client.")
        return

    ws_url = SERVER_URL.replace("http://", "ws://").replace("https://", "wss://")
    api_gateway = f"{ws_url}/api/ws/events/v1"
    headers = [f"Authorization: Bearer {token}"]

    ws = websocket.WebSocketApp(
        api_gateway,
        header=headers,
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close,
    )
    ws.run_forever()


def main():
    if not all([USERNAME, PASSWORD]):
        logger.error("API_USERNAME and API_PASSWORD must be set as environment variables.")
        return

    run_rest_api()

    with open("access_token.txt", "r") as f:
        token = f.read().strip()

    if os.getenv("ENABLE_WEBSOCKET", "false").lower() == "true":
        logger.info("Starting WebSocket client...")
        ws_thread = threading.Thread(target=run_websocket, args=(token,), daemon=True)
        ws_thread.start()
        ws_thread.join()


if __name__ == "__main__":
    main()
