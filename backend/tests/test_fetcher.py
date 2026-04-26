import json
import pytest
import pandas as pd
import fakeredis
from unittest.mock import patch, MagicMock
from app.data.fetcher import fetch_price, fetch_all_prices, is_market_open, WATCHLIST, SECTORS


def make_mock_history():
    return pd.DataFrame({
        "Open": [1490.0],
        "High": [1510.0],
        "Low": [1485.0],
        "Close": [1500.0],
        "Volume": [1000000],
    })


def test_fetch_price_live(monkeypatch):
    r = fakeredis.FakeRedis()
    mock_ticker = MagicMock()
    mock_ticker.history.return_value = make_mock_history()

    with patch("app.data.fetcher.yf.Ticker", return_value=mock_ticker):
        result = fetch_price("INFY.NS", r)

    assert result is not None
    assert result["symbol"] == "INFY.NS"
    assert result["close"] == 1500.0
    assert result["volume"] == 1000000


def test_fetch_price_cached(monkeypatch):
    r = fakeredis.FakeRedis()
    cached = {"symbol": "INFY.NS", "close": 1234.0, "open": 1230.0, "high": 1240.0, "low": 1220.0, "volume": 500000}
    r.setex("price:INFY.NS", 900, json.dumps(cached))

    with patch("app.data.fetcher.yf.Ticker") as mock_ticker:
        result = fetch_price("INFY.NS", r)
        mock_ticker.assert_not_called()

    assert result["close"] == 1234.0


def test_fetch_price_sets_cache():
    r = fakeredis.FakeRedis()
    mock_ticker = MagicMock()
    mock_ticker.history.return_value = make_mock_history()

    with patch("app.data.fetcher.yf.Ticker", return_value=mock_ticker):
        fetch_price("INFY.NS", r)

    assert r.exists("price:INFY.NS")
    ttl = r.ttl("price:INFY.NS")
    assert 800 < ttl <= 900


def test_watchlist_has_15_stocks():
    assert len(WATCHLIST) == 15  # 14 tradeable + NIFTY


def test_sectors_cover_all_tradeable():
    all_sector_stocks = [s for stocks in SECTORS.values() for s in stocks]
    tradeable = [s for s in WATCHLIST if s != "^NSEI"]
    assert set(all_sector_stocks) == set(tradeable)


def test_is_market_open_returns_bool():
    result = is_market_open()
    assert isinstance(result, bool)
