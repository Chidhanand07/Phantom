from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agent.state import TradeDecision
from app.data.fetcher import SECTORS
from app.portfolio.models import Portfolio, Position, Trade


def _get_sector(symbol: str) -> str:
    for sector, symbols in SECTORS.items():
        if symbol in symbols:
            return sector
    return "Other"


def execute_trade(
    decision: TradeDecision,
    narration: str,
    reasoning: str,
    db: Session,
) -> None:
    if decision.action == "HOLD":
        return

    portfolio = db.execute(select(Portfolio)).scalars().first()

    trade = Trade(
        symbol=decision.symbol,
        action=decision.action,
        quantity=decision.quantity,
        price=decision.price,
        confidence=decision.confidence,
        rationale=decision.rationale,
        narration=narration,
        reasoning=reasoning,
    )
    db.add(trade)

    if decision.action == "BUY":
        cost = decision.quantity * decision.price
        portfolio.cash = float(portfolio.cash) - cost

        existing = db.execute(
            select(Position).where(Position.symbol == decision.symbol)
        ).scalar_one_or_none()

        if existing:
            total_qty = existing.quantity + decision.quantity
            existing.avg_price = (
                (float(existing.avg_price) * existing.quantity + decision.price * decision.quantity)
                / total_qty
            )
            existing.quantity = total_qty
        else:
            db.add(Position(
                symbol=decision.symbol,
                quantity=decision.quantity,
                avg_price=decision.price,
                sector=_get_sector(decision.symbol),
            ))

    elif decision.action == "SELL":
        proceeds = decision.quantity * decision.price
        portfolio.cash = float(portfolio.cash) + proceeds

        pos = db.execute(
            select(Position).where(Position.symbol == decision.symbol)
        ).scalar_one_or_none()

        if pos:
            pos.quantity -= decision.quantity
            if pos.quantity <= 0:
                db.delete(pos)

    db.commit()
