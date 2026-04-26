import asyncio
import logging
import time
from datetime import datetime, timezone

import redis as redis_lib
from apscheduler.schedulers.background import BackgroundScheduler
from pytz import timezone as tz
from sqlalchemy.orm import Session

from app.agent.context_builder import build_phantom_state
from app.agent.graph import build_graph
from app.config import settings
from app.database import SessionLocal
from app.data.fetcher import is_market_open, fetch_all_prices
from app.portfolio.models import AgentLog
from app.portfolio.portfolio import get_portfolio_snapshot

logger = logging.getLogger(__name__)

_redis_client: redis_lib.Redis | None = None


def _get_redis() -> redis_lib.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis_lib.Redis.from_url(settings.redis_url, decode_responses=True)
    return _redis_client


def run_agent_cycle() -> None:
    start = time.time()
    log = AgentLog(cycle_at=datetime.now(timezone.utc))
    db: Session | None = None
    try:
        db = SessionLocal()
        r = _get_redis()
        market_open = is_market_open()
        log.market_open = market_open

        if not market_open:
            logger.info("Market closed — skipping agent cycle")
            log.action_taken = "SKIPPED"
            return

        logger.info("Starting agent cycle")
        state = build_phantom_state(db, r)
        graph = build_graph(db, r)
        result = graph.invoke(state)

        decision = result.get("decision")
        narration = result.get("narration", "Phantom is watching the markets.")

        log.action_taken = decision.action if decision else "HOLD"
        log.symbol = decision.symbol if decision and decision.symbol else None

        if decision and decision.action != "HOLD":
            try:
                from app.websocket.broadcast import broadcast_trade
                prices = fetch_all_prices(r)
                portfolio = get_portfolio_snapshot(db, prices)
                asyncio.run(broadcast_trade(narration, decision, portfolio))
            except Exception as e:
                logger.warning("WS broadcast failed: %s", e)

        logger.info("Cycle complete: %s %s", log.action_taken, log.symbol or "")

    except Exception as exc:
        logger.exception("Agent cycle failed: %s", exc)
        log.error = str(exc)
    finally:
        log.duration_seconds = round(time.time() - start, 2)
        if db is not None:
            try:
                db.add(log)
                db.commit()
            except Exception:
                logger.exception("Failed to persist AgentLog")
                db.rollback()
            finally:
                db.close()


def create_scheduler() -> BackgroundScheduler:
    ist = tz("Asia/Kolkata")
    scheduler = BackgroundScheduler(timezone=ist)
    scheduler.add_job(
        run_agent_cycle,
        "interval",
        minutes=settings.agent_cycle_minutes,
        id="agent_cycle",
    )
    return scheduler
