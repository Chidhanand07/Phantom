import asyncio
import json
import logging
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        self._connections: list[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self._connections.append(ws)
        logger.info("WS client connected. Total: %d", len(self._connections))

    async def disconnect(self, ws: WebSocket) -> None:
        async with self._lock:
            self._connections = [c for c in self._connections if c != ws]
        logger.info("WS client disconnected. Total: %d", len(self._connections))

    async def broadcast(self, message: dict[str, Any]) -> None:
        payload = json.dumps(message)
        dead = []
        for ws in list(self._connections):
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            await self.disconnect(ws)


manager = ConnectionManager()


async def broadcast_trade(narration: str, decision: Any, portfolio: Any) -> None:
    await manager.broadcast({
        "type": "trade",
        "narration": narration,
        "decision": {
            "action": decision.action,
            "symbol": decision.symbol,
            "quantity": decision.quantity,
            "price": decision.price,
            "confidence": decision.confidence,
            "rationale": decision.rationale,
        },
        "portfolio": {
            "cash": portfolio.cash,
            "total_value": portfolio.total_value,
            "unrealized_pnl": portfolio.unrealized_pnl,
            "positions": [
                {
                    "symbol": p.symbol,
                    "quantity": p.quantity,
                    "avg_price": p.avg_price,
                    "current_price": p.current_price,
                    "market_value": p.market_value,
                    "unrealized_pnl": p.unrealized_pnl,
                    "sector": p.sector,
                }
                for p in portfolio.positions
            ],
        },
    })


async def broadcast_heartbeat(market_open: bool) -> None:
    from datetime import datetime, timezone
    await manager.broadcast({
        "type": "heartbeat",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "market_open": market_open,
    })
