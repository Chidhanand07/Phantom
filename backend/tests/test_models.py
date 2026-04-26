from app.portfolio.models import Portfolio, Position, Trade, TradeMemory, AgentLog


def test_portfolio_creation(db):
    p = Portfolio(cash=100000.0)
    db.add(p)
    db.commit()
    db.refresh(p)
    assert p.id is not None
    assert p.cash == 100000.0


def test_position_creation(db):
    pos = Position(symbol="INFY.NS", quantity=10, avg_price=1500.0, sector="IT")
    db.add(pos)
    db.commit()
    db.refresh(pos)
    assert pos.id is not None
    assert pos.symbol == "INFY.NS"


def test_trade_creation(db):
    t = Trade(
        symbol="INFY.NS",
        action="BUY",
        quantity=10,
        price=1500.0,
        confidence=0.8,
        rationale="Oversold RSI",
        narration="Buying Infosys because...",
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    assert t.id is not None
    assert t.action == "BUY"


def test_trade_memory_creation(db):
    m = TradeMemory(
        stock="INFY.NS",
        action="BUY",
        price=1500.0,
        quantity=10,
        thesis="Q3 beats estimates",
        signals_at_entry={"rsi": 28.0},
        target_price=1700.0,
        stop_loss=1400.0,
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    assert m.thesis_status == "active"
    assert m.id is not None


def test_agent_log_creation(db):
    log = AgentLog(market_open=True, action_taken="BUY", symbol="INFY.NS", duration_seconds=2.3)
    db.add(log)
    db.commit()
    assert log.id is not None
