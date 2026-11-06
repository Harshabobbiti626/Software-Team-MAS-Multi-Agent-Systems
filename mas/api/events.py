"""
Real-time Event Broker & SSE Streaming Protocol for MAS Cockpit.
Thread-safe pub/sub broker distributing pipeline lifecycle events,
agent pod statuses, artifact diffs, and HITL gate prompts to Web UI clients.
"""

import queue
import threading
import time
from typing import Any, Dict, List, Optional


class EventBus:
    def __init__(self):
        self._lock = threading.Lock()
        self._subscribers: Dict[str, List[queue.Queue]] = {}
        self._mission_history: Dict[str, List[Dict[str, Any]]] = {}

    def subscribe(self, mission_id: str) -> queue.Queue:
        """Subscribes an SSE connection to a specific mission stream."""
        q: queue.Queue = queue.Queue(maxsize=1000)
        with self._lock:
            if mission_id not in self._subscribers:
                self._subscribers[mission_id] = []
            self._subscribers[mission_id].append(q)

            # Replay recent history to new subscriber so state is immediately hydrated
            history = self._mission_history.get(mission_id, [])
            for event in history:
                q.put(event)

        return q

    def unsubscribe(self, mission_id: str, q: queue.Queue) -> None:
        """Removes a subscriber queue upon connection close."""
        with self._lock:
            if mission_id in self._subscribers:
                if q in self._subscribers[mission_id]:
                    self._subscribers[mission_id].remove(q)
                if not self._subscribers[mission_id]:
                    del self._subscribers[mission_id]

    def publish(self, mission_id: str, event_type: str, payload: Dict[str, Any]) -> None:
        """Publishes an event to all active subscribers for the mission."""
        event = {
            "type": event_type,
            "mission_id": mission_id,
            "payload": payload,
            "data": payload,  # Dual alias so clients consuming either 'payload' or 'data' receive it flawlessly
            "timestamp": time.time(),
        }

        with self._lock:
            if mission_id not in self._mission_history:
                self._mission_history[mission_id] = []
            self._mission_history[mission_id].append(event)
            # Keep history bounded to 500 events per mission
            if len(self._mission_history[mission_id]) > 500:
                self._mission_history[mission_id].pop(0)

            subscribers = list(self._subscribers.get(mission_id, []))

        for q in subscribers:
            try:
                q.put_nowait(event)
            except queue.Full:
                pass

    def get_history(self, mission_id: str) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._mission_history.get(mission_id, []))


# Global singleton event bus
_global_event_bus: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    global _global_event_bus
    if _global_event_bus is None:
        _global_event_bus = EventBus()
    return _global_event_bus
