# Phantom Week 2 — LangGraph Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Prerequisite:** Week 1 plan complete. Docker stack running. `pytest tests/` passes. `build_phantom_state()` works.

**Goal:** Build the full 6-node LangGraph agent that reasons over market data, risk-checks decisions, narrates in plain English, writes persistent trade memory, and executes paper trades — then expose everything via FastAPI REST + WebSocket endpoints.

**Architecture:** Nodes are pure functions that transform PhantomState. The graph wires them with conditional routing. Memory persists to both Redis (fast lookup) and PostgreSQL (durable). WebSocket fan-out broadcaster streams narration live to dashboard clients.

**Tech Stack:** LangGraph 0.1.x, LangChain Anthropic (`claude-sonnet-4-6`), Pydantic structured output, FastAPI WebSocket, APScheduler wired to graph, Redis + PostgreSQL dual-write memory

---

## File Map

| File | Responsibility |
|---|---|
| `backend/app/agent/prompts.py` | All LLM prompt templates |
| `backend/app/agent/nodes.py` | All 6 node functions |
| `backend/app/agent/memory.py` | TradeMemory CRUD — Redis + PostgreSQL |
| `backend/app/portfolio/executor.py` | Paper trade execution — DB writes |
| `backend/app/agent/graph.py` | LangGraph StateGraph — wires all nodes |
| `backend/app/websocket/broadcast.py` | WebSocket connection manager + fan-out |
| `backend/app/api/portfolio.py` | GET /portfolio, /positions, /trades |
| `backend/app/api/signals.py` | GET /signals/{symbol} |
| `backend/app/api/memory.py` | GET /memories |
| `backend/app/main.py` | Full FastAPI app with WS + scheduler |
| `backend/tests/test_nodes.py` | Node unit tests (mocked LLM) |
| `backend/tests/test_memory.py` | Memory CRUD tests |
| `backend/tests/test_executor.py` | Trade executor tests |
| `backend/tests/test_graph.py` | End-to-end graph smoke test |
| `backend/tests/test_api.py` | REST endpoint tests |

---

### Task 1: LLM prompt templates

**Files:**
- Create: `backend/app/agent/prompts.py`

- [ ] **Step 1: Create `backend/app/agent/prompts.py`**

```python
REASONING_PROMPT = """You are Phantom, an autonomous AI portfolio manager for Indian equity markets.

Current portfolio state:
- Cash available: ₹{cash:,.0f}
- Total portfolio value: ₹{total_value:,.0f}
- Open positions: {position_count}

Current holdings:
{holdings_text}

Technical signals (right now):
{signals_text}

News sentiment scores (-1.0 = very negative, +1.0 = very positive):
{sentiment_text}

Your stored memories for held positions:
{memories_text}

Task: Analyse this information carefully. Consider:
1. Have any of your original investment theses played out or been invalidated?
2. Which stocks show compelling signals RIGHT NOW (not just one signal — look for confluence)?
3. Does the overall market sentiment support risk-taking or caution?
4. What would a disciplined fund manager do given the current portfolio allocation?

Write 2-3 paragraphs of analysis. Be specific about stock names and why. End with a clear conclusion about what action to take and on which stock."""

DECISION_PROMPT = """Based on this analysis:

{reasoning}

Current portfolio constraints:
- Cash available: ₹{cash:,.0f}
- Max position size: {max_position_pct:.0%} of portfolio (₹{max_position_value:,.0f})
- Current open positions: {position_count} / {max_positions}
- Min confidence to trade: {min_confidence:.0%}

Respond with a JSON object exactly matching this schema:
{{
  "action": "BUY" | "SELL" | "HOLD",
  "symbol": "<NSE symbol like INFY.NS, or empty string for HOLD>",
  "quantity": <integer shares>,
  "price": <current price float>,
  "confidence": <float 0.0 to 1.0>,
  "rationale": "<one sentence>"
}}

Rules:
- HOLD: symbol must be empty string, quantity 0, price 0.0
- BUY: only symbols from the watchlist
- quantity * price must not exceed max_position_value
- confidence below {min_confidence:.0%} → use HOLD"""

NARRATION_PROMPT = """You are the voice of Phantom, a friendly AI investor. Translate this technical decision into plain English for someone who doesn't know much about stocks.

Decision: {action} {quantity} shares of {symbol} at ₹{price:,.0f}
Confidence: {confidence:.0%}
Reasoning summary: {reasoning_summary}

Rules:
- NO jargon (no "RSI", "MACD", "oversold", "bullish crossover")
- Use analogies — explain what the signal means in real life
- 2-4 sentences maximum
- Sound like a smart friend explaining a decision, not a Bloomberg terminal
- If HOLD, explain why you're watching and waiting
- Be specific about the company — mention what they actually do

Good example: "I'm buying Reliance because they just announced a massive JioFiber expansion — think of it like a telecom land grab. The stock dipped 3% this week on market noise but the company itself got stronger. I'm treating the dip as a discount."
Bad example: "Technical indicators show oversold RSI at 28.4 with bullish MACD crossover signal."""

THESIS_PROMPT = """Write a concise investment thesis for this trade in 2-3 sentences. This will be stored as your memory and referenced when deciding to sell.

Stock: {symbol} ({company_name})
Action: BUY at ₹{price:,.0f}
Reasoning: {reasoning}
Current signals: {signals_summary}
Target price: ₹{target_price:,.0f}
Stop loss: ₹{stop_loss:,.0f}

Write the thesis in first person ("I'm buying because..."). Be specific about what would make you sell — what does "thesis played out" look like for this trade?"""
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/agent/prompts.py
git commit -m "feat: LLM prompt templates for reasoning, decision, narration, thesis"
```

---

### Task 2: Trade memory CRUD

**Files:**
- Create: `backend/app/agent/memory.py`
- Create: `backend/tests/test_memory.py`

- [ ] **Step 1: Write failing test**

Create `backend/tests/test_memory.py`:
```python
import json
from datetime import datetime
from unittest.mock import patch
import fakeredis
import pytest
from app.agent.memory import write_buy_memory, update_sell_memory, get_memory_for_symbol
from app.agent.state import TradeDecision, TradeMemoryData
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
```

- [ ] **Step 2: Run test — confirm it fails**

```bash
pytest tests/test_memory.py -v
```

Expected: `ModuleNotFoundError: No module named 'app.agent.memory'`

- [ ] **Step 3: Create `backend/app/agent/memory.py`**

```python
import json
from dataclasses import asdict
from datetime import datetime
from typing import Optional

import redis
from langchain_anthropic import ChatAnthropic
from langchain.prompts import ChatPromptTemplate
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agent.prompts import THESIS_PROMPT
from app.agent.state import TradeDecision, TradeMemoryData
from app.config import settings
from app.data.fetcher import COMPANY_NAMES_MAP
from app.data.signals import TechnicalSignals
from app.portfolio.models import TradeMemory

_MEMORY_TTL = 86400 * 30  # 30 days


def generate_thesis(
    decision: TradeDecision,
    signals: TechnicalSignals,
    reasoning: str,
) -> str:
    llm = ChatAnthropic(
        model="claude-sonnet-4-6",
        anthropic_api_key=settings.anthropic_api_key,
        max_tokens=200,
    )
    prompt = ChatPromptTemplate.from_template(THESIS_PROMPT)
    chain = prompt | llm

    company_name = _company_name(decision.symbol)
    target_price = decision.price * 1.12  # 12% target
    stop_loss = decision.price * 0.93   # 7% stop

    result = chain.invoke({
        "symbol": decision.symbol,
        "company_name": company_name,
        "price": decision.price,
        "reasoning": reasoning[:500],
        "signals_summary": (
            f"RSI {signals.rsi_value:.1f} ({signals.rsi_signal}), "
            f"MACD {signals.macd_signal}, price {signals.sma20_signal} SMA20"
        ),
        "target_price": target_price,
        "stop_loss": stop_loss,
    })
    return result.content.strip()


def _company_name(symbol: str) -> str:
    from app.data.sentiment import COMPANY_NAMES
    return COMPANY_NAMES.get(symbol, symbol.replace(".NS", ""))


def write_buy_memory(
    decision: TradeDecision,
    signals: TechnicalSignals,
    reasoning: str,
    db: Session,
    r: redis.Redis,
) -> None:
    thesis = generate_thesis(decision, signals, reasoning)
    target_price = decision.price * 1.12
    stop_loss = decision.price * 0.93

    row = TradeMemory(
        stock=decision.symbol,
        action="BUY",
        price=decision.price,
        quantity=decision.quantity,
        thesis=thesis,
        signals_at_entry={
            "rsi": signals.rsi_value,
            "rsi_signal": signals.rsi_signal,
            "macd_signal": signals.macd_signal,
            "sma20_signal": signals.sma20_signal,
            "volume_signal": signals.volume_signal,
        },
        target_price=target_price,
        stop_loss=stop_loss,
        thesis_status="active",
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    cache_key = f"memory:{decision.symbol}"
    data = {
        "id": row.id,
        "stock": row.stock,
        "action": row.action,
        "price": row.price,
        "quantity": row.quantity,
        "timestamp": row.timestamp.isoformat(),
        "thesis": row.thesis,
        "signals_at_entry": row.signals_at_entry,
        "target_price": row.target_price,
        "stop_loss": row.stop_loss,
        "thesis_status": row.thesis_status,
    }
    r.setex(cache_key, _MEMORY_TTL, json.dumps(data))


def update_sell_memory(
    decision: TradeDecision,
    outcome: str,  # "played_out" | "invalidated"
    db: Session,
    r: redis.Redis,
) -> None:
    row = db.execute(
        select(TradeMemory)
        .where(TradeMemory.stock == decision.symbol, TradeMemory.thesis_status == "active")
    ).scalar_one_or_none()

    if row:
        row.thesis_status = outcome
        db.commit()

    r.delete(f"memory:{decision.symbol}")


def get_memory_for_symbol(
    symbol: str, db: Session, r: redis.Redis
) -> Optional[TradeMemoryData]:
    cache_key = f"memory:{symbol}"
    cached = r.get(cache_key)
    if cached:
        return TradeMemoryData(**json.loads(cached))

    row = db.execute(
        select(TradeMemory)
        .where(TradeMemory.stock == symbol, TradeMemory.thesis_status == "active")
    ).scalar_one_or_none()

    if not row:
        return None

    return TradeMemoryData(
        id=row.id,
        stock=row.stock,
        action=row.action,
        price=row.price,
        quantity=row.quantity,
        timestamp=row.timestamp.isoformat(),
        thesis=row.thesis,
        signals_at_entry=row.signals_at_entry or {},
        target_price=row.target_price or 0.0,
        stop_loss=row.stop_loss or 0.0,
        thesis_status=row.thesis_status,
    )
```

Note: `fetcher.py` does not export `COMPANY_NAMES_MAP` — the `_company_name` helper in memory.py imports from `sentiment.py`. Remove the `from app.data.fetcher import COMPANY_NAMES_MAP` line — it's covered by the `_company_name()` function body.

- [ ] **Step 4: Fix the import in memory.py** — remove line `from app.data.fetcher import COMPANY_NAMES_MAP` (line is redundant given `_company_name()` already imports from sentiment).

The corrected `_company_name` function (replace in memory.py):
```python
def _company_name(symbol: str) -> str:
    from app.data.sentiment import COMPANY_NAMES
    return COMPANY_NAMES.get(symbol, symbol.replace(".NS", ""))
```

And remove the top-level import of `COMPANY_NAMES_MAP`.

- [ ] **Step 5: Run tests — confirm pass**

```bash
pytest tests/test_memory.py -v
```

Expected: 4 tests pass.

- [ ] **Step 6: Commit**

```bash
git add backend/app/agent/memory.py backend/tests/test_memory.py
git commit -m "feat: trade memory CRUD — Redis + PostgreSQL dual write"
```

---

### Task 3: Portfolio trade executor

**Files:**
- Create: `backend/app/portfolio/executor.py`
- Create: `backend/tests/test_executor.py`

- [ ] **Step 1: Write failing test**

Create `backend/tests/test_executor.py`:
```python
import pytest
from app.portfolio.executor import execute_trade
from app.portfolio.models import Portfolio, Position, Trade
from app.agent.state import TradeDecision
from sqlalchemy import select


def _seed(db, cash=100000.0):
    db.add(Portfolio(cash=cash))
    db.commit()


def _buy_decision(symbol="INFY.NS", qty=10, price=1500.0):
    return TradeDecision(
        action="BUY", symbol=symbol, quantity=qty, price=price,
        confidence=0.8, rationale="Test buy"
    )


def _sell_decision(symbol="INFY.NS", qty=10, price=1600.0):
    return TradeDecision(
        action="SELL", symbol=symbol, quantity=qty, price=price,
        confidence=0.75, rationale="Test sell"
    )


def test_buy_creates_position(db):
    _seed(db)
    execute_trade(_buy_decision(), "Narration text", "Reasoning text", db)
    pos = db.execute(select(Position).where(Position.symbol == "INFY.NS")).scalar_one_or_none()
    assert pos is not None
    assert pos.quantity == 10
    assert pos.avg_price == 1500.0


def test_buy_deducts_cash(db):
    _seed(db)
    execute_trade(_buy_decision(), "Narration", "Reasoning", db)
    portfolio = db.execute(select(Portfolio)).scalar_one()
    assert portfolio.cash == pytest.approx(100000.0 - 10 * 1500.0)


def test_buy_records_trade(db):
    _seed(db)
    execute_trade(_buy_decision(), "My narration", "My reasoning", db)
    trade = db.execute(select(Trade).where(Trade.symbol == "INFY.NS")).scalar_one()
    assert trade.action == "BUY"
    assert trade.narration == "My narration"


def test_sell_removes_position(db):
    _seed(db, cash=85000.0)
    db.add(Position(symbol="INFY.NS", quantity=10, avg_price=1500.0, sector="IT"))
    db.commit()
    execute_trade(_sell_decision(), "Selling", "Reasoning", db)
    pos = db.execute(select(Position).where(Position.symbol == "INFY.NS")).scalar_one_or_none()
    assert pos is None


def test_sell_adds_cash(db):
    _seed(db, cash=85000.0)
    db.add(Position(symbol="INFY.NS", quantity=10, avg_price=1500.0, sector="IT"))
    db.commit()
    execute_trade(_sell_decision(price=1600.0), "Selling", "Reasoning", db)
    portfolio = db.execute(select(Portfolio)).scalar_one()
    assert portfolio.cash == pytest.approx(85000.0 + 10 * 1600.0)


def test_partial_sell_reduces_quantity(db):
    _seed(db, cash=85000.0)
    db.add(Position(symbol="INFY.NS", quantity=20, avg_price=1500.0, sector="IT"))
    db.commit()
    execute_trade(_sell_decision(qty=10), "Partial sell", "Reasoning", db)
    pos = db.execute(select(Position).where(Position.symbol == "INFY.NS")).scalar_one()
    assert pos.quantity == 10


def test_buy_existing_position_updates_avg_price(db):
    _seed(db, cash=70000.0)
    db.add(Position(symbol="INFY.NS", quantity=10, avg_price=1500.0, sector="IT"))
    db.commit()
    execute_trade(_buy_decision(qty=10, price=1600.0), "Adding", "Reasoning", db)
    pos = db.execute(select(Position).where(Position.symbol == "INFY.NS")).scalar_one()
    assert pos.quantity == 20
    assert pos.avg_price == pytest.approx(1550.0)
```

- [ ] **Step 2: Run test — confirm it fails**

```bash
pytest tests/test_executor.py -v
```

Expected: `ModuleNotFoundError: No module named 'app.portfolio.executor'`

- [ ] **Step 3: Create `backend/app/portfolio/executor.py`**

```python
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agent.state import TradeDecision
from app.data.fetcher import SECTORS
from app.portfolio.models import Portfolio, Position, Trade


def _get_sector(symbol: str) -> str:
    for sector, symbols in SECTORS.items():
        if symbol in symbols:
            return sector
    return "Other"


def execute_trade(
    decision: TradeDecision,
    narration: str,
    reasoning: str,
    db: Session,
) -> None:
    if decision.action == "HOLD":
        return

    portfolio = db.execute(select(Portfolio)).scalar_one()

    trade = Trade(
        symbol=decision.symbol,
        action=decision.action,
        quantity=decision.quantity,
        price=decision.price,
        confidence=decision.confidence,
        rationale=decision.rationale,
        narration=narration,
        reasoning=reasoning,
    )
    db.add(trade)

    if decision.action == "BUY":
        cost = decision.quantity * decision.price
        portfolio.cash -= cost

        existing = db.execute(
            select(Position).where(Position.symbol == decision.symbol)
        ).scalar_one_or_none()

        if existing:
            total_qty = existing.quantity + decision.quantity
            existing.avg_price = (
                (existing.quantity * existing.avg_price + decision.quantity * decision.price)
                / total_qty
            )
            existing.quantity = total_qty
        else:
            db.add(Position(
                symbol=decision.symbol,
                quantity=decision.quantity,
                avg_price=decision.price,
                sector=_get_sector(decision.symbol),
            ))

    elif decision.action == "SELL":
        proceeds = decision.quantity * decision.price
        portfolio.cash += proceeds

        pos = db.execute(
            select(Position).where(Position.symbol == decision.symbol)
        ).scalar_one_or_none()

        if pos:
            pos.quantity -= decision.quantity
            if pos.quantity <= 0:
                db.delete(pos)

    db.commit()
```

- [ ] **Step 4: Run tests — confirm pass**

```bash
pytest tests/test_executor.py -v
```

Expected: 7 tests pass.

- [ ] **Step 5: Commit**

```bash
git add backend/app/portfolio/executor.py backend/tests/test_executor.py
git commit -m "feat: paper trade executor — BUY/SELL with position tracking and cash management"
```

---

### Task 4: Agent nodes

**Files:**
- Create: `backend/app/agent/nodes.py`
- Create: `backend/tests/test_nodes.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_nodes.py`:
```python
import json
import pytest
from unittest.mock import MagicMock, patch
from app.agent.state import PhantomState, TradeDecision
from app.portfolio.portfolio import PortfolioSnapshot
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


# --- risk_check_node tests (pure Python — no mocks needed) ---

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
    # HOLD is always approved — no risk to check
    assert result["risk_approved"] is True


def test_risk_check_blocks_oversized_position():
    state = _make_state(cash=100000.0)
    state["decision"] = TradeDecision(
        action="BUY", symbol="INFY.NS", quantity=15,
        price=1500.0, confidence=0.9, rationale="Test"
    )
    # 15 * 1500 = 22500, which is 22.5% of 100000 > 20% max
    result = risk_check_node(state)
    assert result["risk_approved"] is False
    assert "position size" in result["risk_notes"].lower()


def test_risk_check_blocks_insufficient_cash():
    state = _make_state(cash=8000.0)  # only 8% cash after trade would be negative
    state["decision"] = TradeDecision(
        action="BUY", symbol="INFY.NS", quantity=5,
        price=1500.0, confidence=0.8, rationale="Test"
    )
    # 5*1500=7500, leaves 500 cash = 0.5% of portfolio — below 10% minimum
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


# --- reasoning_node test (mocked LLM) ---

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


# --- decision_node test (mocked structured output) ---

def test_decision_node_returns_trade_decision():
    state = _make_state(cash=100000.0)
    state["reasoning"] = "INFY is oversold, good buy opportunity"

    mock_decision = TradeDecision(
        action="BUY", symbol="INFY.NS", quantity=10,
        price=1500.0, confidence=0.8, rationale="RSI oversold"
    )

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


# --- narration_node test (mocked LLM) ---

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
    assert "RSI" not in result["narration"]  # no jargon
```

- [ ] **Step 2: Run test — confirm it fails**

```bash
pytest tests/test_nodes.py -v
```

Expected: `ModuleNotFoundError: No module named 'app.agent.nodes'`

- [ ] **Step 3: Create `backend/app/agent/nodes.py`**

```python
import json
import logging
from dataclasses import asdict
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

    # Check 1: position size
    if trade_cost / total_value > settings.max_position_pct:
        return {
            "risk_approved": False,
            "risk_notes": f"Position size {trade_cost/total_value:.1%} exceeds max {settings.max_position_pct:.0%}",
        }

    # Check 2: cash reserve (must keep min 10% after trade)
    if decision.action == "BUY":
        remaining_cash = cash - trade_cost
        if remaining_cash / total_value < settings.min_cash_pct:
            return {
                "risk_approved": False,
                "risk_notes": f"Insufficient cash reserve after trade: {remaining_cash/total_value:.1%} < {settings.min_cash_pct:.0%}",
            }

    # Check 3: max open positions
    if decision.action == "BUY" and len(portfolio.positions) >= settings.max_positions:
        return {
            "risk_approved": False,
            "risk_notes": f"Max open positions ({settings.max_positions}) already reached",
        }

    # Check 4: sector exposure
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
        # Strip markdown code fences if present
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
        # Enforce minimum confidence
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
```

- [ ] **Step 4: Run tests — confirm pass**

```bash
pytest tests/test_nodes.py -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add backend/app/agent/nodes.py backend/tests/test_nodes.py
git commit -m "feat: all 6 langgraph node functions — reasoning, risk_check, decision, narration"
```

---

### Task 5: LangGraph graph + memory/executor nodes

**Files:**
- Create: `backend/app/agent/graph.py`
- Create: `backend/tests/test_graph.py`

- [ ] **Step 1: Write failing test**

Create `backend/tests/test_graph.py`:
```python
import json
import fakeredis
from unittest.mock import MagicMock, patch
from app.agent.graph import build_graph
from app.agent.state import TradeDecision
from app.portfolio.models import Portfolio


def _seed(db):
    db.add(Portfolio(cash=100000.0))
    db.commit()


def test_graph_compiles():
    db = MagicMock()
    r = fakeredis.FakeRedis()
    graph = build_graph(db, r)
    assert graph is not None


def test_graph_hold_path(db):
    _seed(db)
    r = fakeredis.FakeRedis()

    hold_decision = TradeDecision(
        action="HOLD", symbol="", quantity=0,
        price=0.0, confidence=0.5, rationale="Waiting"
    )

    with patch("app.agent.nodes.reasoning_node", return_value={"reasoning": "Flat market"}):
        with patch("app.agent.nodes.decision_node", return_value={"decision": hold_decision}):
            with patch("app.agent.nodes.narration_node", return_value={"narration": "Watching markets."}):
                graph = build_graph(db, r)
                # Pass minimal state to trigger graph
                from app.agent.context_builder import build_phantom_state
                with patch("app.agent.context_builder.fetch_all_prices", return_value={}):
                    with patch("app.agent.context_builder.compute_signals", return_value=None):
                        with patch("app.agent.context_builder.get_all_sentiments", return_value={}):
                            state = build_phantom_state(db, r)

                result = graph.invoke(state)

    assert result["narration"] == "Watching markets."
    assert result["decision"].action == "HOLD"
```

- [ ] **Step 2: Run test — confirm it fails**

```bash
pytest tests/test_graph.py -v
```

Expected: `ModuleNotFoundError: No module named 'app.agent.graph'`

- [ ] **Step 3: Create `backend/app/agent/graph.py`**

```python
import logging
from dataclasses import asdict

import redis
from langgraph.graph import END, StateGraph
from sqlalchemy.orm import Session

from app.agent.memory import write_buy_memory, update_sell_memory
from app.agent.nodes import (
    decision_node, narration_node, reasoning_node,
    risk_check_node, route_risk,
)
from app.agent.state import PhantomState
from app.portfolio.executor import execute_trade

logger = logging.getLogger(__name__)


def _make_memory_executor_node(db: Session, r: redis.Redis):
    def memory_writer_node(state: PhantomState) -> dict:
        decision = state.get("decision")
        if decision is None or decision.action == "HOLD":
            return {}

        signals = state["signals"].get(decision.symbol)
        if decision.action == "BUY" and signals:
            try:
                write_buy_memory(decision, signals, state["reasoning"], db, r)
            except Exception as e:
                logger.warning("Memory write failed: %s", e)
        elif decision.action == "SELL":
            try:
                outcome = "played_out" if decision.confidence > 0.6 else "invalidated"
                update_sell_memory(decision, outcome, db, r)
            except Exception as e:
                logger.warning("Memory update failed: %s", e)

        return {}

    def trade_executor_node(state: PhantomState) -> dict:
        decision = state.get("decision")
        if decision is None or decision.action == "HOLD":
            logger.info("HOLD — no trade executed")
            return {}

        try:
            execute_trade(decision, state["narration"], state["reasoning"], db)
            logger.info("Executed %s %d %s @ %.2f", decision.action, decision.quantity, decision.symbol, decision.price)
        except Exception as e:
            logger.error("Trade execution failed: %s", e)

        return {}

    return memory_writer_node, trade_executor_node


def build_graph(db: Session, r: redis.Redis) -> StateGraph:
    memory_writer_node, trade_executor_node = _make_memory_executor_node(db, r)

    graph = StateGraph(PhantomState)
    graph.add_node("reason", reasoning_node)
    graph.add_node("risk_check", risk_check_node)
    graph.add_node("decide", decision_node)
    graph.add_node("narrate", narration_node)
    graph.add_node("remember", memory_writer_node)
    graph.add_node("execute", trade_executor_node)

    graph.set_entry_point("reason")
    graph.add_edge("reason", "decide")
    graph.add_edge("decide", "risk_check")
    graph.add_conditional_edges("risk_check", route_risk, {
        "approved": "narrate",
        "blocked": END,
    })
    graph.add_edge("narrate", "remember")
    graph.add_edge("remember", "execute")
    graph.add_edge("execute", END)

    return graph.compile()
```

- [ ] **Step 4: Run tests — confirm pass**

```bash
pytest tests/test_graph.py -v
```

Expected: tests pass.

- [ ] **Step 5: Commit**

```bash
git add backend/app/agent/graph.py backend/tests/test_graph.py
git commit -m "feat: langgraph 6-node graph — reason→risk→decide→narrate→remember→execute"
```

---

### Task 6: WebSocket broadcaster + full FastAPI app

**Files:**
- Create: `backend/app/websocket/broadcast.py`
- Modify: `backend/app/main.py`
- Modify: `backend/app/scheduler/scheduler.py`

- [ ] **Step 1: Create `backend/app/websocket/broadcast.py`**

```python
import asyncio
import json
import logging
from dataclasses import asdict
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        self._connections: list[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self._connections.append(ws)
        logger.info("WS client connected. Total: %d", len(self._connections))

    async def disconnect(self, ws: WebSocket) -> None:
        async with self._lock:
            self._connections = [c for c in self._connections if c != ws]
        logger.info("WS client disconnected. Total: %d", len(self._connections))

    async def broadcast(self, message: dict[str, Any]) -> None:
        payload = json.dumps(message)
        dead = []
        for ws in list(self._connections):
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            await self.disconnect(ws)


manager = ConnectionManager()


async def broadcast_trade(narration: str, decision: Any, portfolio: Any) -> None:
    await manager.broadcast({
        "type": "trade",
        "narration": narration,
        "decision": {
            "action": decision.action,
            "symbol": decision.symbol,
            "quantity": decision.quantity,
            "price": decision.price,
            "confidence": decision.confidence,
            "rationale": decision.rationale,
        },
        "portfolio": {
            "cash": portfolio.cash,
            "total_value": portfolio.total_value,
            "unrealized_pnl": portfolio.unrealized_pnl,
            "positions": [
                {
                    "symbol": p.symbol,
                    "quantity": p.quantity,
                    "avg_price": p.avg_price,
                    "current_price": p.current_price,
                    "market_value": p.market_value,
                    "unrealized_pnl": p.unrealized_pnl,
                    "sector": p.sector,
                }
                for p in portfolio.positions
            ],
        },
    })


async def broadcast_heartbeat(market_open: bool) -> None:
    from datetime import datetime, timezone
    await manager.broadcast({
        "type": "heartbeat",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "market_open": market_open,
    })
```

- [ ] **Step 2: Create `backend/app/api/portfolio.py`**

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select
import redis

from app.database import get_db
from app.config import settings
from app.portfolio.portfolio import get_portfolio_snapshot
from app.portfolio.models import Trade
from app.data.fetcher import fetch_all_prices

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


def get_redis() -> redis.Redis:
    return redis.Redis.from_url(settings.redis_url, decode_responses=True)


@router.get("")
def get_portfolio(db: Session = Depends(get_db)):
    r = get_redis()
    prices = fetch_all_prices(r)
    snap = get_portfolio_snapshot(db, prices)
    return {
        "cash": snap.cash,
        "total_value": snap.total_value,
        "unrealized_pnl": snap.unrealized_pnl,
        "total_pnl_pct": snap.total_pnl_pct,
        "positions": [
            {
                "symbol": p.symbol,
                "quantity": p.quantity,
                "avg_price": p.avg_price,
                "current_price": p.current_price,
                "market_value": p.market_value,
                "unrealized_pnl": p.unrealized_pnl,
                "pnl_pct": p.pnl_pct,
                "sector": p.sector,
            }
            for p in snap.positions
        ],
    }


@router.get("/trades")
def get_trades(limit: int = 50, db: Session = Depends(get_db)):
    trades = db.execute(
        select(Trade).order_by(Trade.executed_at.desc()).limit(limit)
    ).scalars().all()
    return [
        {
            "id": t.id,
            "symbol": t.symbol,
            "action": t.action,
            "quantity": t.quantity,
            "price": t.price,
            "confidence": t.confidence,
            "rationale": t.rationale,
            "narration": t.narration,
            "executed_at": t.executed_at.isoformat(),
        }
        for t in trades
    ]
```

- [ ] **Step 3: Create `backend/app/api/signals.py`**

```python
from fastapi import APIRouter, HTTPException
import redis

from app.config import settings
from app.data.signals import compute_signals

router = APIRouter(prefix="/signals", tags=["signals"])


def get_redis() -> redis.Redis:
    return redis.Redis.from_url(settings.redis_url, decode_responses=True)


@router.get("/{symbol}")
def get_signals(symbol: str):
    r = get_redis()
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
```

- [ ] **Step 4: Create `backend/app/api/memory.py`**

```python
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session
import redis

from app.config import settings
from app.database import get_db
from app.portfolio.models import TradeMemory

router = APIRouter(prefix="/memories", tags=["memory"])


@router.get("")
def get_memories(db: Session = Depends(get_db)):
    rows = db.execute(select(TradeMemory).order_by(TradeMemory.timestamp.desc())).scalars().all()
    return [
        {
            "id": m.id,
            "stock": m.stock,
            "action": m.action,
            "price": m.price,
            "quantity": m.quantity,
            "timestamp": m.timestamp.isoformat(),
            "thesis": m.thesis,
            "signals_at_entry": m.signals_at_entry,
            "target_price": m.target_price,
            "stop_loss": m.stop_loss,
            "thesis_status": m.thesis_status,
        }
        for m in rows
    ]
```

- [ ] **Step 5: Update `backend/app/main.py` — full app with WS + REST**

```python
import asyncio
import json
import logging
from contextlib import asynccontextmanager

import redis as redis_lib
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from app.api import memory as memory_router
from app.api import portfolio as portfolio_router
from app.api import signals as signals_router
from app.config import settings
from app.database import SessionLocal
from app.scheduler.scheduler import create_scheduler
from app.websocket.broadcast import broadcast_heartbeat, manager

logger = logging.getLogger(__name__)


async def _heartbeat_loop():
    from app.data.fetcher import is_market_open
    while True:
        try:
            await broadcast_heartbeat(is_market_open())
        except Exception as e:
            logger.warning("Heartbeat failed: %s", e)
        await asyncio.sleep(60)


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = create_scheduler()
    scheduler.start()
    heartbeat_task = asyncio.create_task(_heartbeat_loop())
    yield
    heartbeat_task.cancel()
    scheduler.shutdown()


app = FastAPI(title="Phantom", version="0.1.0", lifespan=lifespan)

app.include_router(portfolio_router.router)
app.include_router(signals_router.router)
app.include_router(memory_router.router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.websocket("/ws/feed")
async def websocket_feed(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()  # keep connection alive
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
```

- [ ] **Step 6: Wire broadcast into scheduler**

Update `backend/app/scheduler/scheduler.py` — replace the `run_agent_cycle` function body:

```python
import asyncio
import logging
import time
from datetime import datetime

import pytz
import redis
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session

from app.agent.context_builder import build_phantom_state
from app.agent.graph import build_graph
from app.config import settings
from app.database import SessionLocal
from app.portfolio.models import AgentLog

logger = logging.getLogger(__name__)
IST = pytz.timezone("Asia/Kolkata")


def run_agent_cycle() -> None:
    from app.data.fetcher import is_market_open
    start = time.time()
    db: Session = SessionLocal()
    r = redis.Redis.from_url(settings.redis_url, decode_responses=True)
    market_open = is_market_open()

    log = AgentLog(market_open=market_open, cycle_at=datetime.utcnow())
    try:
        if not market_open:
            logger.info("Market closed — skipping agent cycle")
            log.action_taken = "SKIPPED"
            return

        logger.info("Starting agent cycle")
        state = build_phantom_state(db, r)
        graph = build_graph(db, r)
        result = graph.invoke(state)

        decision = result.get("decision")
        narration = result.get("narration", "Phantom is watching the markets.")

        log.action_taken = decision.action if decision else "HOLD"
        log.symbol = decision.symbol if decision and decision.symbol else None

        # Broadcast result over WebSocket (fire-and-forget)
        try:
            from app.websocket.broadcast import broadcast_trade
            from app.portfolio.portfolio import get_portfolio_snapshot
            from app.data.fetcher import fetch_all_prices

            if decision and decision.action != "HOLD":
                prices = fetch_all_prices(r)
                portfolio = get_portfolio_snapshot(db, prices)
                asyncio.run(broadcast_trade(narration, decision, portfolio))
        except Exception as e:
            logger.warning("WS broadcast failed: %s", e)

        logger.info("Cycle complete: %s %s", log.action_taken, log.symbol or "")

    except Exception as exc:
        logger.exception("Agent cycle failed: %s", exc)
        log.error = str(exc)
    finally:
        log.duration_seconds = round(time.time() - start, 2)
        db.add(log)
        db.commit()
        db.close()


def create_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler(timezone=IST)
    scheduler.add_job(
        run_agent_cycle,
        "interval",
        minutes=settings.agent_cycle_minutes,
        id="agent_cycle",
    )
    return scheduler
```

- [ ] **Step 7: Run full test suite**

```bash
cd backend
pytest tests/ -v --tb=short
```

Expected: all tests pass.

- [ ] **Step 8: Rebuild Docker and verify endpoints**

```bash
docker compose up --build -d
```

Test REST endpoints:
```bash
curl http://localhost:8000/health
curl http://localhost:8000/portfolio
curl http://localhost:8000/portfolio/trades
curl http://localhost:8000/memories
```

All should return JSON (portfolio will show ₹100000 cash, others empty arrays).

Test WebSocket (in a second terminal):
```bash
# Install wscat if needed: npm install -g wscat
wscat -c ws://localhost:8000/ws/feed
```

Expected: receives heartbeat JSON every 60 seconds.

- [ ] **Step 9: Commit**

```bash
git add backend/app/websocket/broadcast.py backend/app/api/ \
  backend/app/main.py backend/app/scheduler/scheduler.py
git commit -m "feat: fastapi REST + websocket feed + agent graph wired to scheduler"
```

---

### Week 2 Verification

Run full test suite:
```bash
cd backend
pytest tests/ -v
```

Manual smoke test (run during market hours OR mock market_open):
```bash
docker compose exec api python -c "
from app.scheduler.scheduler import run_agent_cycle
from unittest.mock import patch
with patch('app.data.fetcher.is_market_open', return_value=True):
    run_agent_cycle()
print('Cycle complete — check logs and /portfolio/trades')
"
```

Check agent log in DB:
```bash
psql postgresql://phantom:phantom@localhost:5432/phantom \
  -c "SELECT cycle_at, action_taken, symbol, duration_seconds, error FROM agent_logs ORDER BY cycle_at DESC LIMIT 5;"
```

Week 2 complete when agent runs one full cycle, makes a decision, and it appears in `/portfolio/trades`.
