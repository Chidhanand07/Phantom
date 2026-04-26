from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

import redis

from app.config import settings
from app.database import get_db
from app.data.fetcher import fetch_all_prices
from app.portfolio.models import Trade
from app.portfolio.portfolio import get_portfolio_snapshot

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


def _get_redis() -> redis.Redis:
    return redis.Redis.from_url(settings.redis_url, decode_responses=True)


@router.get("")
def get_portfolio(db: Session = Depends(get_db)):
    r = _get_redis()
    prices = fetch_all_prices(r)
    snap = get_portfolio_snapshot(db, prices)
    return {
        "cash": snap.cash,
        "total_value": snap.total_value,
        "unrealized_pnl": snap.unrealized_pnl,
        "total_pnl_pct": snap.total_pnl_pct,
        "positions": [
            {
                "symbol": p.symbol,
                "quantity": p.quantity,
                "avg_price": p.avg_price,
                "current_price": p.current_price,
                "market_value": p.market_value,
                "unrealized_pnl": p.unrealized_pnl,
                "pnl_pct": p.pnl_pct,
                "sector": p.sector,
            }
            for p in snap.positions
        ],
    }


@router.get("/trades")
def get_trades(limit: int = 50, db: Session = Depends(get_db)):
    trades = db.execute(
        select(Trade).order_by(Trade.executed_at.desc()).limit(limit)
    ).scalars().all()
    return [
        {
            "id": t.id,
            "symbol": t.symbol,
            "action": t.action,
            "quantity": t.quantity,
            "price": float(t.price),
            "confidence": float(t.confidence) if t.confidence is not None else None,
            "rationale": t.rationale,
            "narration": t.narration,
            "executed_at": t.executed_at.isoformat(),
        }
        for t in trades
    ]
