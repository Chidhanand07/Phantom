import json
import logging
import math
from dataclasses import asdict, dataclass
from typing import Literal, Optional

import numpy as np
import pandas as pd
import redis
import yfinance as yf

logger = logging.getLogger(__name__)
_SIGNALS_TTL = 900  # 15 minutes


@dataclass
class TechnicalSignals:
    symbol: str
    rsi_value: float
    rsi_signal: Literal["oversold", "overbought", "neutral"]
    macd_signal: Literal["bullish_crossover", "bearish_crossover", "neutral"]
    macd_value: float
    macd_hist: float
    sma20_signal: Literal["above", "below"]
    sma20_value: float
    current_price: float
    volume_signal: Literal["spike", "normal"]
    volume_ratio: float


def _compute_rsi(closes: pd.Series, period: int = 14) -> float:
    delta = closes.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    # np.where produces RSI=100 for zero-loss (pure uptrend), not NaN
    rs = np.where(loss == 0, np.inf, gain / loss.replace(0, np.nan))
    rsi = pd.Series(100 - (100 / (1 + rs)), index=closes.index)
    return float(rsi.iloc[-1])


def _compute_macd(
    closes: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9
) -> tuple[float, float, str]:
    ema_fast = closes.ewm(span=fast, adjust=False).mean()
    ema_slow = closes.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    hist = macd_line - signal_line

    macd_val = float(macd_line.iloc[-1])
    hist_val = float(hist.iloc[-1])

    prev_macd = float(macd_line.iloc[-2])
    prev_signal = float(signal_line.iloc[-2])
    curr_signal = float(signal_line.iloc[-1])

    if prev_macd < prev_signal and macd_val >= curr_signal:
        crossover = "bullish_crossover"
    elif prev_macd > prev_signal and macd_val <= curr_signal:
        crossover = "bearish_crossover"
    else:
        crossover = "neutral"

    return macd_val, hist_val, crossover


def compute_signals(symbol: str, r: redis.Redis) -> Optional[TechnicalSignals]:
    cache_key = f"signals:{symbol}"
    cached = r.get(cache_key)
    if cached:
        return TechnicalSignals(**json.loads(cached))

    try:
        df = yf.download(symbol, period="30d", interval="15m", auto_adjust=True, progress=False)
    except Exception as e:
        logger.warning("yfinance download failed for %s: %s", symbol, e)
        return None

    if df.empty:
        return None

    # yfinance 1.x may return MultiIndex columns for single-ticker downloads
    if hasattr(df.columns, "levels"):
        df.columns = df.columns.get_level_values(0)

    if len(df) < 30:
        return None

    closes = df["Close"].squeeze()
    volumes = df["Volume"].squeeze()

    if closes.isna().all():
        return None

    rsi_val = _compute_rsi(closes)
    if math.isnan(rsi_val):
        return None

    if rsi_val < 30:
        rsi_signal: Literal["oversold", "overbought", "neutral"] = "oversold"
    elif rsi_val > 70:
        rsi_signal = "overbought"
    else:
        rsi_signal = "neutral"

    macd_val, macd_hist, macd_signal = _compute_macd(closes)

    sma20 = float(closes.rolling(20).mean().iloc[-1])
    current_price = float(closes.iloc[-1])
    sma20_signal: Literal["above", "below"] = "above" if current_price > sma20 else "below"

    vol_avg = float(volumes.iloc[-6:-1].mean())  # prior 5 bars, excludes current
    vol_today = float(volumes.iloc[-1])
    volume_ratio = vol_today / vol_avg if vol_avg > 0 else 1.0
    volume_signal: Literal["spike", "normal"] = "spike" if volume_ratio > 1.5 else "normal"

    result = TechnicalSignals(
        symbol=symbol,
        rsi_value=rsi_val,
        rsi_signal=rsi_signal,
        macd_signal=macd_signal,
        macd_value=macd_val,
        macd_hist=macd_hist,
        sma20_signal=sma20_signal,
        sma20_value=sma20,
        current_price=current_price,
        volume_signal=volume_signal,
        volume_ratio=volume_ratio,
    )
    r.setex(cache_key, _SIGNALS_TTL, json.dumps(asdict(result)))
    return result
