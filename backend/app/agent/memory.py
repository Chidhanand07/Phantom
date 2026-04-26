import json
from datetime import datetime, timezone
from typing import Optional

import redis
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agent.prompts import THESIS_PROMPT
from app.agent.state import TradeDecision, TradeMemoryData
from app.config import settings
from app.data.signals import TechnicalSignals
from app.portfolio.models import TradeMemory

_MEMORY_TTL = 86400 * 30  # 30 days


def generate_thesis(
    decision: TradeDecision,
    signals: TechnicalSignals,
    reasoning: str,
) -> str:
    llm = ChatAnthropic(
        model="claude-sonnet-4-6",
        anthropic_api_key=settings.anthropic_api_key,
        max_tokens=200,
    )
    prompt = ChatPromptTemplate.from_template(THESIS_PROMPT)
    chain = prompt | llm

    company_name = _company_name(decision.symbol)
    target_price = decision.price * 1.12
    stop_loss = decision.price * 0.93

    result = chain.invoke({
        "symbol": decision.symbol,
        "company_name": company_name,
        "price": decision.price,
        "reasoning": reasoning[:500],
        "signals_summary": (
            f"RSI {signals.rsi_value:.1f} ({signals.rsi_signal}), "
            f"MACD {signals.macd_signal}, price {signals.sma20_signal} SMA20"
        ),
        "target_price": target_price,
        "stop_loss": stop_loss,
    })
    return result.content.strip()


def _company_name(symbol: str) -> str:
    from app.data.sentiment import COMPANY_NAMES
    return COMPANY_NAMES.get(symbol, symbol.replace(".NS", ""))


def write_buy_memory(
    decision: TradeDecision,
    signals: TechnicalSignals,
    reasoning: str,
    db: Session,
    r: redis.Redis,
) -> None:
    thesis = generate_thesis(decision, signals, reasoning)
    target_price = decision.price * 1.12
    stop_loss = decision.price * 0.93

    row = TradeMemory(
        stock=decision.symbol,
        action="BUY",
        price=decision.price,
        quantity=decision.quantity,
        thesis=thesis,
        signals_at_entry={
            "rsi": signals.rsi_value,
            "rsi_signal": signals.rsi_signal,
            "macd_signal": signals.macd_signal,
            "sma20_signal": signals.sma20_signal,
            "volume_signal": signals.volume_signal,
        },
        target_price=target_price,
        stop_loss=stop_loss,
        thesis_status="active",
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    cache_key = f"memory:{decision.symbol}"
    data = {
        "id": str(row.id),
        "stock": row.stock,
        "action": row.action,
        "price": float(row.price),
        "quantity": row.quantity,
        "timestamp": row.timestamp.isoformat(),
        "thesis": row.thesis,
        "signals_at_entry": row.signals_at_entry or {},
        "target_price": float(row.target_price),
        "stop_loss": float(row.stop_loss),
        "thesis_status": row.thesis_status,
    }
    r.setex(cache_key, _MEMORY_TTL, json.dumps(data))


def update_sell_memory(
    decision: TradeDecision,
    outcome: str,
    db: Session,
    r: redis.Redis,
) -> None:
    row = db.execute(
        select(TradeMemory)
        .where(TradeMemory.stock == decision.symbol, TradeMemory.thesis_status == "active")
    ).scalar_one_or_none()

    if row:
        row.thesis_status = outcome
        db.commit()

    r.delete(f"memory:{decision.symbol}")


def get_memory_for_symbol(
    symbol: str, db: Session, r: redis.Redis
) -> Optional[TradeMemoryData]:
    cache_key = f"memory:{symbol}"
    cached = r.get(cache_key)
    if cached:
        data = json.loads(cached)
        return TradeMemoryData(**data)

    row = db.execute(
        select(TradeMemory)
        .where(TradeMemory.stock == symbol, TradeMemory.thesis_status == "active")
    ).scalar_one_or_none()

    if not row:
        return None

    return TradeMemoryData(
        id=str(row.id),
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
    )
