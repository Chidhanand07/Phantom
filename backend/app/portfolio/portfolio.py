from dataclasses import dataclass, field
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.portfolio.models import Portfolio, Position


@dataclass
class PositionSnapshot:
    symbol: str
    quantity: int
    avg_price: float
    current_price: float
    sector: str
    market_value: float
    unrealized_pnl: float
    pnl_pct: float


@dataclass
class PortfolioSnapshot:
    cash: float
    positions: list[PositionSnapshot]
    total_value: float
    unrealized_pnl: float
    initial_value: float = 100000.0

    @property
    def holdings_value(self) -> float:
        return sum(p.market_value for p in self.positions)

    @property
    def total_pnl_pct(self) -> float:
        return (self.total_value - self.initial_value) / self.initial_value * 100


def get_portfolio_snapshot(db: Session, prices: dict[str, dict]) -> PortfolioSnapshot:
    portfolio = db.execute(select(Portfolio)).scalar_one_or_none()
    cash = float(portfolio.cash) if portfolio else 100000.0

    positions_rows = db.execute(select(Position)).scalars().all()
    position_snapshots = []
    total_pnl = 0.0

    for pos in positions_rows:
        price_data = prices.get(pos.symbol, {})
        current_price = price_data.get("close", float(pos.avg_price))
        avg_price = float(pos.avg_price)
        market_value = pos.quantity * current_price
        cost_basis = pos.quantity * avg_price
        pnl = market_value - cost_basis
        pnl_pct = (pnl / cost_basis * 100) if cost_basis else 0.0
        total_pnl += pnl

        position_snapshots.append(PositionSnapshot(
            symbol=pos.symbol,
            quantity=pos.quantity,
            avg_price=avg_price,
            current_price=current_price,
            sector=pos.sector or "",
            market_value=market_value,
            unrealized_pnl=pnl,
            pnl_pct=pnl_pct,
        ))

    total_value = cash + sum(p.market_value for p in position_snapshots)

    return PortfolioSnapshot(
        cash=cash,
        positions=position_snapshots,
        total_value=total_value,
        unrealized_pnl=total_pnl,
    )
