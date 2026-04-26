import json
import math
import numpy as np
import pandas as pd
import fakeredis
from unittest.mock import patch
from app.data.signals import compute_signals, TechnicalSignals


def _make_df(n=100, trend="flat") -> pd.DataFrame:
    np.random.seed(42)
    if trend == "oversold":
        closes = np.linspace(1800, 1300, n) + np.random.randn(n) * 5
    elif trend == "overbought":
        closes = np.linspace(1200, 1900, n) + np.random.randn(n) * 5
    else:
        closes = 1500.0 + np.random.randn(n) * 20

    volumes = np.random.randint(500_000, 2_000_000, n)
    volumes[-1] = int(volumes[-5:].mean() * 2.5)  # spike on last bar

    return pd.DataFrame({
        "Open": closes * 0.995,
        "High": closes * 1.01,
        "Low": closes * 0.99,
        "Close": closes,
        "Volume": volumes.astype(float),
    })


def test_compute_signals_returns_dataclass():
    r = fakeredis.FakeRedis()
    df = _make_df()
    with patch("app.data.signals.yf.download", return_value=df):
        result = compute_signals("INFY.NS", r)
    assert isinstance(result, TechnicalSignals)
    assert result.symbol == "INFY.NS"


def test_rsi_oversold_detected():
    r = fakeredis.FakeRedis()
    df = _make_df(n=100, trend="oversold")
    with patch("app.data.signals.yf.download", return_value=df):
        result = compute_signals("INFY.NS", r)
    assert result.rsi_signal == "oversold"
    assert result.rsi_value < 30


def test_rsi_overbought_detected():
    r = fakeredis.FakeRedis()
    df = _make_df(n=100, trend="overbought")
    with patch("app.data.signals.yf.download", return_value=df):
        result = compute_signals("INFY.NS", r)
    assert result.rsi_signal == "overbought"
    assert result.rsi_value > 70


def test_volume_spike_detected():
    r = fakeredis.FakeRedis()
    df = _make_df()
    with patch("app.data.signals.yf.download", return_value=df):
        result = compute_signals("INFY.NS", r)
    assert result.volume_signal == "spike"


def test_signals_cached():
    r = fakeredis.FakeRedis()
    df = _make_df()
    with patch("app.data.signals.yf.download", return_value=df) as mock_dl:
        compute_signals("INFY.NS", r)
        compute_signals("INFY.NS", r)
        assert mock_dl.call_count == 1


def test_signals_cache_ttl():
    r = fakeredis.FakeRedis()
    df = _make_df()
    with patch("app.data.signals.yf.download", return_value=df):
        compute_signals("INFY.NS", r)
    ttl = r.ttl("signals:INFY.NS")
    assert 800 < ttl <= 900
