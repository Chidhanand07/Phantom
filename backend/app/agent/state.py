from dataclasses import dataclass
from typing import Literal, Optional, TypedDict

from app.portfolio.portfolio import PortfolioSnapshot
from app.data.signals import TechnicalSignals


@dataclass
class TradeDecision:
    action: Literal["BUY", "SELL", "HOLD"]
    symbol: str
    quantity: int
    price: float
    confidence: float
    rationale: str


@dataclass
class TradeMemoryData:
    id: str
    stock: str
    action: str
    price: float
    quantity: int
    timestamp: str
    thesis: str
    signals_at_entry: dict
    target_price: float
    stop_loss: float
    thesis_status: str


class PhantomState(TypedDict):
    portfolio: PortfolioSnapshot
    signals: dict[str, TechnicalSignals]
    sentiment: dict[str, float]
    memories: list[TradeMemoryData]
    reasoning: str
    decision: Optional[TradeDecision]
    narration: str
    risk_approved: bool
    risk_notes: str
