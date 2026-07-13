import asyncio
import logging

logger = logging.getLogger("realtime")


class EventBroadcaster:
    """Bridges events pushed from the background WebSocket thread to any
    number of async subscribers (e.g. the /events/stream SSE endpoint)."""

    def __init__(self):
        self._loop = None
        self._subscribers = set()

    def bind_loop(self, loop):
        self._loop = loop

    async def subscribe(self):
        queue = asyncio.Queue(maxsize=100)
        self._subscribers.add(queue)
        try:
            while True:
                event = await queue.get()
                yield event
        finally:
            self._subscribers.discard(queue)

    def publish(self, event):
        if not self._loop:
            return
        self._loop.call_soon_threadsafe(self._publish_sync, event)

    def _publish_sync(self, event):
        for queue in list(self._subscribers):
            if queue.full():
                logger.warning("SSE subscriber queue full, dropping event")
                continue
            queue.put_nowait(event)


broadcaster = EventBroadcaster()
