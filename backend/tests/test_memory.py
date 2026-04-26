import json
from unittest.mock import patch
import fakeredis
from app.agent.memory import write_buy_memory, update_sell_memory, get_memory_for_symbol
from app.agent.state import TradeDecision
from app.data.signals import TechnicalSignals
from app.portfolio.models import TradeMemory


def _make_decision(action="BUY", symbol="INFY.NS", qty=10, price=1500.0):
    return TradeDecision(
        action=action, symbol=symbol, quantity=qty, price=price,
        confidence=0.8, rationale="RSI oversold"
    )


def _make_signals():
    return TechnicalSignals(
        symbol="INFY.NS", rsi_value=28.0, rsi_signal="oversold",
        macd_signal="bullish_crossover", macd_value=-5.0, macd_hist=1.0,
        sma20_signal="below", sma20_value=1550.0,
        current_price=1500.0, volume_signal="spike", volume_ratio=2.1,
    )


def test_write_buy_memory_creates_db_row(db):
    r = fakeredis.FakeRedis()
    decision = _make_decision()
    signals = _make_signals()

    with patch("app.agent.memory.generate_thesis", return_value="Buying because RSI oversold"):
        write_buy_memory(decision, signals, "Reasoning text", db, r)

    row = db.query(TradeMemory).filter_by(stock="INFY.NS").first()
    assert row is not None
    assert row.action == "BUY"
    assert row.thesis == "Buying because RSI oversold"
    assert row.thesis_status == "active"


def test_write_buy_memory_sets_redis(db):
    r = fakeredis.FakeRedis()
    decision = _make_decision()
    signals = _make_signals()

    with patch("app.agent.memory.generate_thesis", return_value="RSI thesis"):
        write_buy_memory(decision, signals, "Reasoning", db, r)

    cached = r.get("memory:INFY.NS")
    assert cached is not None
    data = json.loads(cached)
    assert data["stock"] == "INFY.NS"


def test_update_sell_memory_marks_played_out(db):
    r = fakeredis.FakeRedis()
    row = TradeMemory(
        stock="INFY.NS", action="BUY", price=1500.0, quantity=10,
        thesis="Buy thesis", thesis_status="active",
        target_price=1700.0, stop_loss=1400.0,
    )
    db.add(row)
    db.commit()

    decision = _make_decision(action="SELL", price=1720.0)
    update_sell_memory(decision, "played_out", db, r)

    db.refresh(row)
    assert row.thesis_status == "played_out"


def test_get_memory_returns_none_when_missing(db):
    r = fakeredis.FakeRedis()
    result = get_memory_for_symbol("TCS.NS", db, r)
    assert result is None
