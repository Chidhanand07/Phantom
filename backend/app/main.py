import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from app.api import memory as memory_api
from app.api import portfolio as portfolio_api
from app.api import signals as signals_api
from app.scheduler.scheduler import create_scheduler
from app.websocket.broadcast import broadcast_heartbeat, manager

logger = logging.getLogger(__name__)


async def _heartbeat_loop() -> None:
    from app.data.fetcher import is_market_open
    while True:
        try:
            await broadcast_heartbeat(is_market_open())
        except Exception as e:
            logger.warning("Heartbeat failed: %s", e)
        await asyncio.sleep(60)


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = create_scheduler()
    scheduler.start()
    heartbeat_task = asyncio.create_task(_heartbeat_loop())
    yield
    heartbeat_task.cancel()
    scheduler.shutdown()


app = FastAPI(title="Phantom", version="0.1.0", lifespan=lifespan)

app.include_router(portfolio_api.router)
app.include_router(signals_api.router)
app.include_router(memory_api.router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.websocket("/ws/feed")
async def websocket_feed(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
