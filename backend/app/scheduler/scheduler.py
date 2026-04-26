import logging
import time
from datetime import datetime, timezone

import redis
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session

from app.agent.context_builder import build_phantom_state
from app.config import settings
from app.database import SessionLocal
from app.data.fetcher import is_market_open
from app.portfolio.models import AgentLog

logger = logging.getLogger(__name__)


def run_agent_cycle() -> None:
    start = time.time()
    db: Session = SessionLocal()
    r = redis.Redis.from_url(settings.redis_url, decode_responses=True)
    market_open = is_market_open()

    log = AgentLog(market_open=market_open, cycle_at=datetime.now(timezone.utc))
    try:
        if not market_open:
            logger.info("Market closed — skipping agent cycle")
            log.action_taken = "SKIPPED"
            return

        logger.info("Starting agent cycle")
        state = build_phantom_state(db, r)
        logger.info("Context built — portfolio cash: %.2f", state["portfolio"].cash)
        log.action_taken = "CONTEXT_BUILT"

    except Exception as exc:
        logger.exception("Agent cycle failed: %s", exc)
        log.error = str(exc)
    finally:
        log.duration_seconds = round(time.time() - start, 2)
        db.add(log)
        db.commit()
        db.close()


def create_scheduler() -> BackgroundScheduler:
    from pytz import timezone as tz
    ist = tz("Asia/Kolkata")
    scheduler = BackgroundScheduler(timezone=ist)
    scheduler.add_job(
        run_agent_cycle,
        "interval",
        minutes=settings.agent_cycle_minutes,
        id="agent_cycle",
    )
    return scheduler
