from collections.abc import Callable
from dataclasses import asdict, dataclass
from typing import Any

import mesop.labs as mel
from state.state import AppState


@dataclass
class WebSocketAction:
    value: AppState


@mel.web_component(path='./websocket_poller.js')
def websocket_poller(
    *,
    trigger_event: Callable[[mel.WebEvent], Any],
    action: WebSocketAction | None = None,
):
    """Creates a WebSocket-based component for real-time state updates.

    Instead of polling at regular intervals, this component establishes a WebSocket
    connection and receives updates in real-time when they occur.

    Returns:
        The web component that was created.
    """
    return mel.insert_web_component(
        name='websocket-poller',
        events={
            'triggerEvent': trigger_event,
        },
        properties={
            'action': asdict(action) if action else {},
        },
    )
