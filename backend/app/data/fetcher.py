import json
import logging
import math
from datetime import datetime
from typing import Optional

import pytz
import redis
import yfinance as yf

logger = logging.getLogger(__name__)

WATCHLIST: list[str] = [
    "INFY.NS", "TCS.NS", "WIPRO.NS",
    "HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS",
    "RELIANCE.NS", "ONGC.NS",
    "MARUTI.NS", "TATAMOTORS.NS", "M&M.NS",
    "HINDUNILVR.NS", "ITC.NS", "NESTLEIND.NS",
    "^NSEI",
]

SECTORS: dict[str, list[str]] = {
    "IT": ["INFY.NS", "TCS.NS", "WIPRO.NS"],
    "Banking": ["HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS"],
    "Energy": ["RELIANCE.NS", "ONGC.NS"],
    "Auto": ["MARUTI.NS", "TATAMOTORS.NS", "M&M.NS"],
    "FMCG": ["HINDUNILVR.NS", "ITC.NS", "NESTLEIND.NS"],
}

IST = pytz.timezone("Asia/Kolkata")
_PRICE_TTL = 900  # 15 minutes


def is_market_open() -> bool:
    now = datetime.now(IST)
    if now.weekday() >= 5:
        return False
    market_open = now.replace(hour=9, minute=15, second=0, microsecond=0)
    market_close = now.replace(hour=15, minute=30, second=0, microsecond=0)
    return market_open <= now <= market_close


def fetch_price(symbol: str, r: redis.Redis) -> Optional[dict]:
    cache_key = f"price:{symbol}"
    cached = r.get(cache_key)
    if cached:
        return json.loads(cached)

    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="2d", interval="15m")
    except Exception as e:
        logger.warning("yfinance fetch failed for %s: %s", symbol, e)
        return None

    if hist.empty:
        return None

    latest = hist.iloc[-1]
    price_fields = [latest["Close"], latest["Open"], latest["High"], latest["Low"]]
    if any(math.isnan(float(v)) for v in price_fields):
        return None

    data = {
        "symbol": symbol,
        "close": float(latest["Close"]),
        "open": float(latest["Open"]),
        "high": float(latest["High"]),
        "low": float(latest["Low"]),
        "volume": int(latest["Volume"]),
    }
    r.setex(cache_key, _PRICE_TTL, json.dumps(data))
    return data


def fetch_all_prices(r: redis.Redis) -> dict[str, dict]:
    result = {}
    for sym in WATCHLIST:
        price = fetch_price(sym, r)
        if price is not None:
            result[sym] = price
    return result
