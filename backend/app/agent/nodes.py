import json
import logging
from typing import Literal

from langchain_anthropic import ChatAnthropic

from app.agent.prompts import DECISION_PROMPT, NARRATION_PROMPT, REASONING_PROMPT
from app.agent.state import PhantomState, TradeDecision
from app.config import settings
from app.data.fetcher import SECTORS

logger = logging.getLogger(__name__)


def _llm(max_tokens: int = 1000) -> ChatAnthropic:
    return ChatAnthropic(
        model="claude-sonnet-4-6",
        anthropic_api_key=settings.anthropic_api_key,
        max_tokens=max_tokens,
    )


def _format_holdings(state: PhantomState) -> str:
    if not state["portfolio"].positions:
        return "  (no open positions)"
    lines = []
    for p in state["portfolio"].positions:
        pnl_str = f"+{p.unrealized_pnl:,.0f}" if p.unrealized_pnl >= 0 else f"{p.unrealized_pnl:,.0f}"
        lines.append(
            f"  {p.symbol}: {p.quantity} shares @ ₹{p.avg_price:,.0f} "
            f"(current ₹{p.current_price:,.0f}, P&L ₹{pnl_str})"
        )
    return "\n".join(lines)


def _format_signals(state: PhantomState) -> str:
    lines = []
    for sym, sig in state["signals"].items():
        lines.append(
            f"  {sym}: RSI {sig.rsi_value:.1f} ({sig.rsi_signal}), "
            f"MACD {sig.macd_signal}, price {sig.sma20_signal} SMA20, "
            f"volume {sig.volume_signal}"
        )
    return "\n".join(lines) if lines else "  (no signals available)"


def _format_sentiment(state: PhantomState) -> str:
    lines = [f"  {sym}: {score:+.2f}" for sym, score in state["sentiment"].items()]
    return "\n".join(lines) if lines else "  (no sentiment data)"


def _format_memories(state: PhantomState) -> str:
    if not state["memories"]:
        return "  (no stored theses)"
    lines = []
    for m in state["memories"]:
        lines.append(f"  {m.stock}: \"{m.thesis}\" (target ₹{m.target_price:,.0f}, stop ₹{m.stop_loss:,.0f})")
    return "\n".join(lines)


def reasoning_node(state: PhantomState) -> dict:
    portfolio = state["portfolio"]
    prompt_text = REASONING_PROMPT.format(
        cash=portfolio.cash,
        total_value=portfolio.total_value,
        position_count=len(portfolio.positions),
        holdings_text=_format_holdings(state),
        signals_text=_format_signals(state),
        sentiment_text=_format_sentiment(state),
        memories_text=_format_memories(state),
    )
    llm = _llm(max_tokens=1000)
    result = llm.invoke(prompt_text)
    return {"reasoning": result.content}


def risk_check_node(state: PhantomState) -> dict:
    decision = state.get("decision")

    if decision is None or decision.action == "HOLD":
        return {"risk_approved": True, "risk_notes": ""}

    portfolio = state["portfolio"]
    total_value = portfolio.total_value
    cash = portfolio.cash
    trade_cost = decision.quantity * decision.price

    if trade_cost / total_value > settings.max_position_pct:
        return {
            "risk_approved": False,
            "risk_notes": f"Position size {trade_cost/total_value:.1%} exceeds max {settings.max_position_pct:.0%}",
        }

    if decision.action == "BUY":
        remaining_cash = cash - trade_cost
        if remaining_cash / total_value < settings.min_cash_pct:
            return {
                "risk_approved": False,
                "risk_notes": f"Insufficient cash reserve after trade: {remaining_cash/total_value:.1%} < {settings.min_cash_pct:.0%}",
            }

    if decision.action == "BUY" and len(portfolio.positions) >= settings.max_positions:
        return {
            "risk_approved": False,
            "risk_notes": f"Max open positions ({settings.max_positions}) already reached",
        }

    if decision.action == "BUY":
        symbol_sector = next(
            (s for s, syms in SECTORS.items() if decision.symbol in syms), None
        )
        if symbol_sector:
            sector_value = sum(
                p.market_value
                for p in portfolio.positions
                if p.sector == symbol_sector
            )
            new_sector_value = sector_value + trade_cost
            if new_sector_value / total_value > settings.max_sector_pct:
                return {
                    "risk_approved": False,
                    "risk_notes": f"Sector {symbol_sector} exposure {new_sector_value/total_value:.1%} exceeds max {settings.max_sector_pct:.0%}",
                }

    return {"risk_approved": True, "risk_notes": ""}


def route_risk(state: PhantomState) -> Literal["approved", "blocked"]:
    return "approved" if state["risk_approved"] else "blocked"


def decision_node(state: PhantomState) -> dict:
    portfolio = state["portfolio"]
    max_position_value = portfolio.total_value * settings.max_position_pct
    prompt_text = DECISION_PROMPT.format(
        reasoning=state["reasoning"],
        cash=portfolio.cash,
        max_position_pct=settings.max_position_pct,
        max_position_value=max_position_value,
        position_count=len(portfolio.positions),
        max_positions=settings.max_positions,
        min_confidence=settings.min_confidence_to_trade,
    )
    llm = _llm(max_tokens=300)
    result = llm.invoke(prompt_text)

    try:
        raw = result.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        data = json.loads(raw.strip())
        decision = TradeDecision(
            action=data["action"],
            symbol=data.get("symbol", ""),
            quantity=int(data.get("quantity", 0)),
            price=float(data.get("price", 0.0)),
            confidence=float(data.get("confidence", 0.0)),
            rationale=data.get("rationale", ""),
        )
        if decision.confidence < settings.min_confidence_to_trade and decision.action != "HOLD":
            decision = TradeDecision(
                action="HOLD", symbol="", quantity=0, price=0.0,
                confidence=decision.confidence, rationale="Confidence below threshold"
            )
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        logger.warning("Failed to parse decision: %s — defaulting to HOLD", e)
        decision = TradeDecision(
            action="HOLD", symbol="", quantity=0, price=0.0,
            confidence=0.0, rationale="Parse error"
        )

    return {"decision": decision}


def narration_node(state: PhantomState) -> dict:
    decision = state["decision"]
    if decision is None:
        return {"narration": "Phantom is watching the markets."}

    prompt_text = NARRATION_PROMPT.format(
        action=decision.action,
        quantity=decision.quantity,
        symbol=decision.symbol,
        price=decision.price,
        confidence=decision.confidence,
        reasoning_summary=state["reasoning"][:300],
    )
    llm = _llm(max_tokens=200)
    result = llm.invoke(prompt_text)
    return {"narration": result.content.strip()}
