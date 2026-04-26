import redis
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.agent.state import PhantomState, TradeMemoryData
from app.data.fetcher import fetch_all_prices, WATCHLIST
from app.data.signals import compute_signals
from app.data.sentiment import get_all_sentiments
from app.portfolio.portfolio import get_portfolio_snapshot
from app.portfolio.models import TradeMemory, Position


def _get_active_memories(db: Session) -> list[TradeMemoryData]:
    held = db.execute(select(Position)).scalars().all()
    held_symbols = {p.symbol for p in held}

    memories = []
    for sym in held_symbols:
        row = db.execute(
            select(TradeMemory)
            .where(TradeMemory.stock == sym, TradeMemory.thesis_status == "active")
        ).scalar_one_or_none()
        if row:
            memories.append(TradeMemoryData(
                id=row.id,
                stock=row.stock,
                action=row.action,
                price=float(row.price),
                quantity=row.quantity,
                timestamp=row.timestamp.isoformat(),
                thesis=row.thesis,
                signals_at_entry=row.signals_at_entry or {},
                target_price=float(row.target_price) if row.target_price else 0.0,
                stop_loss=float(row.stop_loss) if row.stop_loss else 0.0,
                thesis_status=row.thesis_status,
            ))
    return memories


def build_phantom_state(db: Session, r: redis.Redis) -> PhantomState:
    prices = fetch_all_prices(r)
    portfolio = get_portfolio_snapshot(db, prices)

    signals: dict = {}
    for sym in WATCHLIST:
        if sym == "^NSEI":
            continue
        sig = compute_signals(sym, r)
        if sig is not None:
            signals[sym] = sig

    sentiment = get_all_sentiments(r)
    memories = _get_active_memories(db)

    return PhantomState(
        portfolio=portfolio,
        signals=signals,
        sentiment=sentiment,
        memories=memories,
        reasoning="",
        decision=None,
        narration="",
        risk_approved=False,
        risk_notes="",
    )
