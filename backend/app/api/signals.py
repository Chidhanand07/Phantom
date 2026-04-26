from fastapi import APIRouter, HTTPException
import redis

from app.config import settings
from app.data.signals import compute_signals

router = APIRouter(prefix="/signals", tags=["signals"])


def _get_redis() -> redis.Redis:
    return redis.Redis.from_url(settings.redis_url, decode_responses=True)


@router.get("/{symbol}")
def get_signals(symbol: str):
    r = _get_redis()
    sig = compute_signals(symbol, r)
    if sig is None:
        raise HTTPException(status_code=404, detail=f"No signals for {symbol}")
    return {
        "symbol": sig.symbol,
        "rsi_value": sig.rsi_value,
        "rsi_signal": sig.rsi_signal,
        "macd_signal": sig.macd_signal,
        "macd_value": sig.macd_value,
        "sma20_signal": sig.sma20_signal,
        "sma20_value": sig.sma20_value,
        "current_price": sig.current_price,
        "volume_signal": sig.volume_signal,
        "volume_ratio": sig.volume_ratio,
    }
