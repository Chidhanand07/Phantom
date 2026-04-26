import pytest
from app.portfolio.executor import execute_trade
from app.portfolio.models import Portfolio, Position, Trade
from app.agent.state import TradeDecision
from sqlalchemy import select


def _seed(db, cash=100000.0):
    db.add(Portfolio(cash=cash))
    db.commit()


def _buy_decision(symbol="INFY.NS", qty=10, price=1500.0):
    return TradeDecision(
        action="BUY", symbol=symbol, quantity=qty, price=price,
        confidence=0.8, rationale="Test buy"
    )


def _sell_decision(symbol="INFY.NS", qty=10, price=1600.0):
    return TradeDecision(
        action="SELL", symbol=symbol, quantity=qty, price=price,
        confidence=0.75, rationale="Test sell"
    )


def test_buy_creates_position(db):
    _seed(db)
    execute_trade(_buy_decision(), "Narration text", "Reasoning text", db)
    pos = db.execute(select(Position).where(Position.symbol == "INFY.NS")).scalar_one_or_none()
    assert pos is not None
    assert pos.quantity == 10
    assert float(pos.avg_price) == pytest.approx(1500.0)


def test_buy_deducts_cash(db):
    _seed(db)
    execute_trade(_buy_decision(), "Narration", "Reasoning", db)
    portfolio = db.execute(select(Portfolio)).scalar_one()
    assert float(portfolio.cash) == pytest.approx(100000.0 - 10 * 1500.0)


def test_buy_records_trade(db):
    _seed(db)
    execute_trade(_buy_decision(), "My narration", "My reasoning", db)
    trade = db.execute(select(Trade).where(Trade.symbol == "INFY.NS")).scalar_one()
    assert trade.action == "BUY"
    assert trade.narration == "My narration"


def test_sell_removes_position(db):
    _seed(db, cash=85000.0)
    db.add(Position(symbol="INFY.NS", quantity=10, avg_price=1500.0, sector="IT"))
    db.commit()
    execute_trade(_sell_decision(), "Selling", "Reasoning", db)
    pos = db.execute(select(Position).where(Position.symbol == "INFY.NS")).scalar_one_or_none()
    assert pos is None


def test_sell_adds_cash(db):
    _seed(db, cash=85000.0)
    db.add(Position(symbol="INFY.NS", quantity=10, avg_price=1500.0, sector="IT"))
    db.commit()
    execute_trade(_sell_decision(price=1600.0), "Selling", "Reasoning", db)
    portfolio = db.execute(select(Portfolio)).scalar_one()
    assert float(portfolio.cash) == pytest.approx(85000.0 + 10 * 1600.0)


def test_partial_sell_reduces_quantity(db):
    _seed(db, cash=85000.0)
    db.add(Position(symbol="INFY.NS", quantity=20, avg_price=1500.0, sector="IT"))
    db.commit()
    execute_trade(_sell_decision(qty=10), "Partial sell", "Reasoning", db)
    pos = db.execute(select(Position).where(Position.symbol == "INFY.NS")).scalar_one()
    assert pos.quantity == 10


def test_buy_existing_position_updates_avg_price(db):
    _seed(db, cash=70000.0)
    db.add(Position(symbol="INFY.NS", quantity=10, avg_price=1500.0, sector="IT"))
    db.commit()
    execute_trade(_buy_decision(qty=10, price=1600.0), "Adding", "Reasoning", db)
    pos = db.execute(select(Position).where(Position.symbol == "INFY.NS")).scalar_one()
    assert pos.quantity == 20
    assert float(pos.avg_price) == pytest.approx(1550.0)
