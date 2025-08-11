"""A UI solution and host service to interact with the agent framework.
run:
  uv main.py
"""

import os
import sys

# Add the project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'samples', 'python')))

from contextlib import asynccontextmanager

import httpx
from copy import deepcopy
import mesop as me

from components.api_key_dialog import api_key_dialog
from components.page_scaffold import page_scaffold
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
from fastapi.middleware.wsgi import WSGIMiddleware
from pages.agent_list import agent_list_page
from pages.conversation import conversation_page
from pages.event_list import event_list_page
from pages.home import home_page_content
from pages.settings import settings_page_content
from pages.task_list import task_list_page
from service.server.server import ConversationServer
from state import host_agent_service
from state.state import AppState


load_dotenv()


def on_load(e: me.LoadEvent):  # pylint: disable=unused-argument
    """On load event"""
    state = me.state(AppState)
    me.set_theme_mode(state.theme_mode)
    if 'conversation_id' in me.query_params:
        state.current_conversation_id = me.query_params['conversation_id']
    else:
        state.current_conversation_id = ''

    # check if the API key is set in the environment
    # and if the user is using Vertex AI
    uses_vertex_ai = (
        os.getenv('GOOGLE_GENAI_USE_VERTEXAI', '').upper() == 'TRUE'
    )
    api_key = os.getenv('GOOGLE_API_KEY', '')

    if uses_vertex_ai:
        state.uses_vertex_ai = True
    elif api_key:
        state.api_key = api_key
    else:
        # Show the API key dialog if both are not set
        state.api_key_dialog_open = True


# Policy to allow the lit custom element to load
security_policy = me.SecurityPolicy(
    allowed_script_srcs=[
        'https://cdn.jsdelivr.net',
    ],
    dangerously_disable_trusted_types=True
)


@me.page(
    path='/',
    title='Chat',
    on_load=on_load,
    security_policy=security_policy,
)
def home_page():
    """Main Page"""
    state = me.state(AppState)
    state.enable_polling = True
    # Show API key dialog if needed
    api_key_dialog()
    with page_scaffold():  # pylint: disable=not-context-manager
        home_page_content(state)


@me.page(
    path='/agents',
    title='Agents',
    on_load=on_load,
    security_policy=security_policy,
)
def another_page():
    """Another Page"""
    api_key_dialog()
    # Disable polling on the Agents page to avoid background refresh loops
    app_state = me.state(AppState)
    app_state.enable_polling = False
    agent_list_page(me.state(AppState))


@me.page(
    path='/conversation',
    title='Conversation',
    on_load=on_load,
    security_policy=security_policy,
)
def chat_page():
    """Conversation Page."""
    api_key_dialog()
    me.state(AppState).enable_polling = True
    conversation_page(me.state(AppState))


@me.page(
    path='/event_list',
    title='Event List',
    on_load=on_load,
    security_policy=security_policy,
)
def event_page():
    """Event List Page."""
    api_key_dialog()
    me.state(AppState).enable_polling = True
    event_list_page(me.state(AppState))


@me.page(
    path='/settings',
    title='Settings',
    on_load=on_load,
    security_policy=security_policy,
)
def settings_page():
    """Settings Page."""
    api_key_dialog()
    me.state(AppState).enable_polling = True
    settings_page_content()


@me.page(
    path='/task_list',
    title='Task List',
    on_load=on_load,
    security_policy=security_policy,
)
def task_page():
    """Task List Page."""
    api_key_dialog()
    me.state(AppState).enable_polling = True
    task_list_page(me.state(AppState))


class HTTPXClientWrapper:
    """Wrapper to return the singleton client where needed."""

    async_client: httpx.AsyncClient = None

    def start(self):
        """Instantiate the client. Call from the FastAPI startup hook."""
        self.async_client = httpx.AsyncClient(timeout=30)

    async def stop(self):
        """Gracefully shutdown. Call from FastAPI shutdown hook."""
        await self.async_client.aclose()
        self.async_client = None

    def __call__(self):
        """Calling the instantiated HTTPXClientWrapper returns the wrapped singleton."""
        # Ensure we don't use it if not started / running
        assert self.async_client is not None
        return self.async_client


# Setup the server global objects
httpx_client_wrapper = HTTPXClientWrapper()
agent_server = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    httpx_client_wrapper.start()
    global agent_server
    agent_server = ConversationServer(app, httpx_client_wrapper())
    app.openapi_schema = None
    app.mount(
        '/',
        WSGIMiddleware(
            me.create_wsgi_app(
                debug_mode=False  # Disable debug mode to prevent frequent hot-reload
            )
        ),
    )
    app.setup()
    yield
    await httpx_client_wrapper.stop()


if __name__ == '__main__':
    import uvicorn
    from uvicorn.config import LOGGING_CONFIG as UVICORN_LOGGING_CONFIG

    # Customize log format to include filename and line number
    LOGGING_WITH_LINES = deepcopy(UVICORN_LOGGING_CONFIG)
    LOGGING_WITH_LINES["formatters"]["default"]["fmt"] = (
        "%(levelprefix)s %(asctime)s [%(filename)s:%(lineno)d %(name)s] %(message)s"
    )
    LOGGING_WITH_LINES["formatters"]["access"]["fmt"] = (
        '%(levelprefix)s %(asctime)s [%(filename)s:%(lineno)d uvicorn.access] %(client_addr)s - "%(request_line)s" %(status_code)s'
    )

    app = FastAPI(lifespan=lifespan)

    @app.websocket("/__ws__")
    async def websocket_endpoint(websocket: WebSocket):
        await websocket.accept()
        try:
            while True:
                # Send state updates through WebSocket
                await websocket.send_json({
                    "type": "state_update",
                    "data": AppState().dict()
                })
                await asyncio.sleep(1)  # Send updates every second
        except Exception as e:
            print(f"WebSocket error: {e}")
        finally:
            await websocket.close()

    # Setup the connection details, these should be set in the environment
    host = '127.0.0.1'  # Use localhost for both server and client
    port = 12000

    # Set the client to talk to the server
    host_agent_service.server_url = f'http://{host}:{port}'

    uvicorn.run(
        app,
        host=host,
        port=port,
        timeout_graceful_shutdown=0,
        reload=False,  # Disable auto-reload
        log_config=LOGGING_WITH_LINES,
    )
