import pytest
from app.portfolio.models import Portfolio, Position
from app.portfolio.portfolio import get_portfolio_snapshot, PortfolioSnapshot, PositionSnapshot


def _seed(db):
    db.add(Portfolio(cash=80000.0))
    db.add(Position(symbol="INFY.NS", quantity=10, avg_price=1500.0, sector="IT"))
    db.add(Position(symbol="TCS.NS", quantity=5, avg_price=3800.0, sector="IT"))
    db.commit()


def test_snapshot_cash(db):
    _seed(db)
    prices = {"INFY.NS": {"close": 1600.0}, "TCS.NS": {"close": 4000.0}}
    snap = get_portfolio_snapshot(db, prices)
    assert snap.cash == pytest.approx(80000.0)


def test_snapshot_total_value(db):
    _seed(db)
    prices = {"INFY.NS": {"close": 1600.0}, "TCS.NS": {"close": 4000.0}}
    snap = get_portfolio_snapshot(db, prices)
    # 80000 + 10*1600 + 5*4000 = 80000 + 16000 + 20000 = 116000
    assert snap.total_value == pytest.approx(116000.0)


def test_snapshot_pnl(db):
    _seed(db)
    prices = {"INFY.NS": {"close": 1600.0}, "TCS.NS": {"close": 4000.0}}
    snap = get_portfolio_snapshot(db, prices)
    # market value: 10*1600 + 5*4000 = 36000; cost basis: 10*1500 + 5*3800 = 34000
    assert snap.unrealized_pnl == pytest.approx(2000.0)


def test_snapshot_positions(db):
    _seed(db)
    prices = {"INFY.NS": {"close": 1600.0}, "TCS.NS": {"close": 4000.0}}
    snap = get_portfolio_snapshot(db, prices)
    assert len(snap.positions) == 2
    symbols = {p.symbol for p in snap.positions}
    assert symbols == {"INFY.NS", "TCS.NS"}


def test_snapshot_no_positions(db):
    db.add(Portfolio(cash=100000.0))
    db.commit()
    snap = get_portfolio_snapshot(db, {})
    assert snap.total_value == pytest.approx(100000.0)
    assert snap.positions == []


def test_position_pnl_pct(db):
    db.add(Portfolio(cash=100000.0))
    db.add(Position(symbol="RELIANCE.NS", quantity=10, avg_price=2000.0, sector="Energy"))
    db.commit()
    prices = {"RELIANCE.NS": {"close": 2200.0}}
    snap = get_portfolio_snapshot(db, prices)
    pos = snap.positions[0]
    assert pos.pnl_pct == pytest.approx(10.0)  # 10% gain


def test_missing_price_uses_avg_price(db):
    db.add(Portfolio(cash=100000.0))
    db.add(Position(symbol="WIPRO.NS", quantity=5, avg_price=300.0, sector="IT"))
    db.commit()
    snap = get_portfolio_snapshot(db, {})  # no price data
    pos = snap.positions[0]
    assert pos.current_price == pytest.approx(300.0)
    assert pos.unrealized_pnl == pytest.approx(0.0)
