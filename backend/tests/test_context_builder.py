import fakeredis
from unittest.mock import patch, MagicMock, call
from app.agent.context_builder import build_phantom_state
from app.agent.state import PhantomState
from app.portfolio.models import Portfolio
from app.data.signals import TechnicalSignals


def _seed_portfolio(db):
    db.add(Portfolio(cash=100000.0))
    db.commit()


def _make_signals(sym="INFY.NS") -> TechnicalSignals:
    return TechnicalSignals(
        symbol=sym, rsi_value=45.0, rsi_signal="neutral",
        macd_signal="neutral", macd_value=0.0, macd_hist=0.0,
        sma20_signal="above", sma20_value=1450.0,
        current_price=1500.0, volume_signal="normal", volume_ratio=1.0,
    )


def test_build_phantom_state_returns_state(db):
    _seed_portfolio(db)
    r = fakeredis.FakeRedis()

    with patch("app.agent.context_builder.fetch_all_prices", return_value={"INFY.NS": {"close": 1500.0}}):
        with patch("app.agent.context_builder.compute_signals", return_value=_make_signals()):
            with patch("app.agent.context_builder.get_all_sentiments", return_value={"INFY.NS": 0.3}):
                state = build_phantom_state(db, r)

    assert isinstance(state, dict)
    assert state["portfolio"].cash == 100000.0
    assert state["reasoning"] == ""
    assert state["risk_approved"] is False


def test_build_phantom_state_includes_signals(db):
    _seed_portfolio(db)
    r = fakeredis.FakeRedis()

    with patch("app.agent.context_builder.fetch_all_prices", return_value={}):
        with patch("app.agent.context_builder.compute_signals", return_value=_make_signals("INFY.NS")) as mock_sig:
            with patch("app.agent.context_builder.get_all_sentiments", return_value={"INFY.NS": 0.5}):
                state = build_phantom_state(db, r)

    assert "INFY.NS" in state["signals"]
    assert state["signals"]["INFY.NS"].rsi_value == 45.0
    assert mock_sig.call_count == 14  # all WATCHLIST symbols except ^NSEI
    called_symbols = [c.args[0] for c in mock_sig.call_args_list]
    assert "^NSEI" not in called_symbols


def test_build_phantom_state_sentiment_included(db):
    _seed_portfolio(db)
    r = fakeredis.FakeRedis()

    with patch("app.agent.context_builder.fetch_all_prices", return_value={}):
        with patch("app.agent.context_builder.compute_signals", return_value=None):
            with patch("app.agent.context_builder.get_all_sentiments", return_value={"RELIANCE.NS": 0.8}):
                state = build_phantom_state(db, r)

    assert state["sentiment"].get("RELIANCE.NS") == 0.8
