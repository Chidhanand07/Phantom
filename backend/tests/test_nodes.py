import json
import pytest
from unittest.mock import MagicMock, patch
from app.agent.state import PhantomState, TradeDecision
from app.portfolio.portfolio import PortfolioSnapshot, PositionSnapshot
from app.agent.nodes import (
    reasoning_node, risk_check_node, decision_node,
    narration_node, route_risk,
)


def _make_state(cash=100000.0, positions=None, signals=None) -> PhantomState:
    portfolio = PortfolioSnapshot(
        cash=cash,
        positions=positions or [],
        total_value=cash,
        unrealized_pnl=0.0,
    )
    return PhantomState(
        portfolio=portfolio,
        signals=signals or {},
        sentiment={"INFY.NS": 0.5},
        memories=[],
        reasoning="",
        decision=None,
        narration="",
        risk_approved=False,
        risk_notes="",
    )


def test_risk_check_approves_valid_trade():
    state = _make_state(cash=100000.0)
    state["decision"] = TradeDecision(
        action="BUY", symbol="INFY.NS", quantity=10,
        price=1500.0, confidence=0.8, rationale="Test"
    )
    result = risk_check_node(state)
    assert result["risk_approved"] is True


def test_risk_check_blocks_hold():
    state = _make_state()
    state["decision"] = TradeDecision(
        action="HOLD", symbol="", quantity=0,
        price=0.0, confidence=0.5, rationale="Waiting"
    )
    result = risk_check_node(state)
    assert result["risk_approved"] is True


def test_risk_check_blocks_oversized_position():
    state = _make_state(cash=100000.0)
    state["decision"] = TradeDecision(
        action="BUY", symbol="INFY.NS", quantity=15,
        price=1500.0, confidence=0.9, rationale="Test"
    )
    # 15 * 1500 = 22500 = 22.5% of 100000 > 20% max
    result = risk_check_node(state)
    assert result["risk_approved"] is False
    assert "position size" in result["risk_notes"].lower()


def test_risk_check_blocks_insufficient_cash():
    state = _make_state(cash=8000.0)
    state["decision"] = TradeDecision(
        action="BUY", symbol="INFY.NS", quantity=5,
        price=1500.0, confidence=0.8, rationale="Test"
    )
    # 5*1500=7500, leaves 500 cash = 6.25% of 8000 < 10% minimum
    result = risk_check_node(state)
    assert result["risk_approved"] is False


def test_route_risk_approved():
    state = _make_state()
    state["risk_approved"] = True
    assert route_risk(state) == "approved"


def test_route_risk_blocked():
    state = _make_state()
    state["risk_approved"] = False
    assert route_risk(state) == "blocked"


def test_reasoning_node_sets_reasoning():
    state = _make_state()
    mock_result = MagicMock()
    mock_result.content = "Market analysis: INFY looks oversold..."

    with patch("app.agent.nodes.ChatAnthropic") as MockLLM:
        instance = MockLLM.return_value
        instance.invoke.return_value = mock_result
        result = reasoning_node(state)

    assert "reasoning" in result
    assert len(result["reasoning"]) > 0


def test_decision_node_returns_trade_decision():
    state = _make_state(cash=100000.0)
    state["reasoning"] = "INFY is oversold, good buy opportunity"

    with patch("app.agent.nodes.ChatAnthropic") as MockLLM:
        instance = MockLLM.return_value
        instance.invoke.return_value = MagicMock(
            content=json.dumps({
                "action": "BUY", "symbol": "INFY.NS", "quantity": 10,
                "price": 1500.0, "confidence": 0.8, "rationale": "RSI oversold"
            })
        )
        result = decision_node(state)

    assert result["decision"] is not None
    assert result["decision"].action in ("BUY", "SELL", "HOLD")


def test_narration_node_sets_narration():
    state = _make_state()
    state["reasoning"] = "INFY oversold analysis"
    state["decision"] = TradeDecision(
        action="BUY", symbol="INFY.NS", quantity=10,
        price=1500.0, confidence=0.8, rationale="RSI oversold"
    )

    with patch("app.agent.nodes.ChatAnthropic") as MockLLM:
        instance = MockLLM.return_value
        instance.invoke.return_value = MagicMock(
            content="I'm buying Infosys because the stock looks undervalued."
        )
        result = narration_node(state)

    assert result["narration"] != ""
