# Phantom — Design Spec

**Date:** 2026-04-26  
**Status:** Approved  
**Build approach:** Bottom-up layers (data → agent → frontend)  
**Target environment:** Local, Docker Compose only

---

## What It Is

Phantom is an autonomous AI paper trading agent for Indian equity markets (NSE/BSE). It manages a virtual ₹1,00,000 portfolio, running a full market-data → signal → sentiment → reasoning → decision → narration cycle every 15 minutes during market hours. Every decision is narrated in plain English and streamed live to a dark Next.js dashboard via WebSocket. No real money, no brokerage integration.

The distinguishing feature: the agent writes a thesis when it buys a stock and references that thesis when deciding whether to sell. Users watch it say _"Selling Infosys — my thesis from 8 days ago has played out"_ in real time.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Agent orchestration | LangGraph + LangChain |
| LLM | Claude API (`claude-sonnet-4-6`) |
| Backend | FastAPI (Python 3.11+) |
| Frontend | Next.js 14 (App Router, TypeScript) |
| Market data | yfinance (free, no key) |
| Technical signals | pandas-ta |
| News sentiment | NewsAPI + LangChain sentiment chain |
| Database | PostgreSQL (SQLAlchemy ORM + Alembic) |
| Cache / agent state | Redis |
| Real-time | WebSocket (FastAPI native) |
| Scheduler | APScheduler |
| Config | Pydantic Settings |
| DB migrations | Alembic |
| Containers | Docker + docker-compose |

---

## Project Structure

```
phantom/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI entry point, WebSocket /ws/feed
│   │   ├── config.py                # Pydantic Settings — all env vars, validated at startup
│   │   │
│   │   ├── agent/
│   │   │   ├── graph.py             # LangGraph StateGraph — 6-node pipeline
│   │   │   ├── state.py             # PhantomState TypedDict
│   │   │   ├── nodes.py             # All 6 node functions
│   │   │   ├── context_builder.py   # Assembles clean PhantomState for the graph
│   │   │   ├── memory.py            # TradeMemory CRUD (Redis + PostgreSQL)
│   │   │   └── prompts.py           # All LLM prompt templates
│   │   │
│   │   ├── data/
│   │   │   ├── fetcher.py           # yfinance wrapper, market hours check, Redis cache
│   │   │   ├── signals.py           # RSI-14, MACD, SMA-20, volume delta
│   │   │   └── sentiment.py         # NewsAPI + LangChain scorer, RSS fallback
│   │   │
│   │   ├── portfolio/
│   │   │   ├── models.py            # SQLAlchemy: Position, Trade, TradeMemory, AgentLog
│   │   │   ├── portfolio.py         # Portfolio state — holdings, cash, P&L
│   │   │   └── executor.py          # Paper trade execution, DB writes
│   │   │
│   │   ├── scheduler/
│   │   │   └── scheduler.py         # APScheduler — fires every 15min, market hours guard
│   │   │
│   │   ├── websocket/
│   │   │   └── broadcast.py         # WS connection manager, fan-out broadcaster
│   │   │
│   │   └── api/
│   │       ├── portfolio.py         # GET /portfolio, /positions, /trades
│   │       ├── signals.py           # GET /signals/{symbol}
│   │       └── memory.py            # GET /memories
│   │
│   ├── alembic/                     # DB migrations
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/
│   ├── app/
│   │   ├── page.tsx                 # Main dashboard
│   │   ├── layout.tsx
│   │   └── components/
│   │       ├── AgentFeed.tsx        # Live WS narration stream, typewriter animation
│   │       ├── Portfolio.tsx        # Holdings + P&L table
│   │       ├── TradeHistory.tsx     # All trades with collapsible reasoning
│   │       ├── SignalBoard.tsx      # RSI/MACD/sentiment per stock
│   │       ├── MemoryViewer.tsx     # Agent's stored theses per position
│   │       └── PerfChart.tsx        # Portfolio vs NIFTY50 (recharts)
│   ├── lib/
│   │   ├── useWebSocket.ts          # WS hook with reconnect logic
│   │   └── demo-data.ts             # Pre-recorded decisions for demo mode
│   ├── package.json
│   └── Dockerfile
│
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## Core Data Structures

### PhantomState — passed between all LangGraph nodes

```python
class PhantomState(TypedDict):
    portfolio: PortfolioSnapshot       # holdings, cash, total value
    signals: dict[str, TechnicalSignals]
    sentiment: dict[str, float]        # -1.0 to +1.0 per stock
    memories: list[TradeMemory]        # stored theses for held positions
    reasoning: str                     # output from reasoning_node
    decision: TradeDecision            # BUY/SELL/HOLD + symbol + qty + confidence
    narration: str                     # plain English explanation
    risk_approved: bool
```

### TradeMemory — persistent agent memory

```python
class TradeMemory(BaseModel):
    id: str
    stock: str                         # "INFY.NS"
    action: str                        # "BUY"
    price: float
    quantity: int
    timestamp: datetime
    thesis: str                        # "Buying because Q3 results beat estimates by 8%..."
    signals_at_entry: dict
    target_price: float
    stop_loss: float
    thesis_status: str                 # "active" | "played_out" | "invalidated"
```

### TradeDecision — structured output from decision_node

```python
class TradeDecision(BaseModel):
    action: Literal["BUY", "SELL", "HOLD"]
    symbol: str
    quantity: int
    price: float
    confidence: float                  # 0.0 to 1.0, minimum 0.65 to trade
    rationale: str                     # one sentence
```

---

## Build Layers (approved sequence)

### Week 1 — Data Pipeline

| Layer | File(s) | Deliverable |
|---|---|---|
| 1 — Docker | `docker-compose.yml` | FastAPI + PostgreSQL + Redis running locally |
| 2 — DB Models | `portfolio/models.py` + Alembic | All migrations run clean; ₹1L seed portfolio |
| 3 — Fetcher | `data/fetcher.py` | Live OHLCV for 15 NSE stocks, Redis-cached |
| 4 — Signals | `data/signals.py` | RSI-14, MACD, SMA-20, volume delta as structured signals |
| 5 — Sentiment | `data/sentiment.py` | NewsAPI + LangChain scorer, 1hr TTL, RSS fallback |
| 6 — Scheduler | `scheduler/scheduler.py` | Fires every 15min, IST market hours guard |
| 6b — Context Builder | `agent/context_builder.py` | Assembles full PhantomState; nodes do zero data fetching |

### Week 2 — LangGraph Agent

| Layer | File(s) | Deliverable |
|---|---|---|
| 7 — Agent Core | `agent/graph.py`, `nodes.py`, `state.py` | Full 6-node graph runs end-to-end with real data |
| 8 — Memory | `agent/memory.py` | TradeMemory written on BUY, updated on SELL, injected into context |
| 9 — API + WS | `api/`, `websocket/broadcast.py`, `main.py` | REST endpoints + WS /ws/feed working |
| 9b — Config | `config.py`, `.env.example` | All env vars declared, Pydantic validates at startup |

### Week 3 — Frontend

| Layer | Day(s) | Deliverable |
|---|---|---|
| 10 — Demo Mode | Day 15 | Pre-recorded JSON + WS mock server; frontend tested without agent |
| 11 — Dashboard | Days 16–18 | All 6 components built and verified against demo data |
| 12 — Live WS | Day 19 | AgentFeed wired to live ws://localhost:8000/ws/feed |

---

## The LangGraph Agent — 6 Nodes

```
reason → decide → risk_check → narrate → remember → execute
                        ↓ (if risk blocked)
                       END
```

### Node 1: reasoning_node
- Synthesises portfolio + signals + sentiment + memories into chain-of-thought analysis
- Key prompt: "Consider your existing positions and the theses you wrote when buying them. Have those theses played out?"
- Output: `state["reasoning"]` — 2–3 paragraphs

### Node 2: risk_check_node (pure Python — no LLM)
- Max position size: 20% of portfolio value
- Max sector exposure: 40%
- Min cash reserve: 10%
- Max open positions: 5
- Violation → `risk_approved = False` → routes to END

### Node 3: decision_node
- Input: `state["reasoning"]`
- Output: structured `TradeDecision` via `with_structured_output`
- Min confidence to trade: 0.65

### Node 4: narration_node
- Plain English, no jargon, 2–4 sentences, analogies encouraged
- This is the product's voice — spend the most prompt-engineering time here
- Good: "I'm buying Reliance because they just announced a JioFiber expansion — think of it like a telecom land grab."
- Bad: "RSI indicates oversold conditions at 28.4 with a bullish MACD crossover."

### Node 5: memory_writer_node
- BUY → create TradeMemory in Redis (`memory:{symbol}`) + PostgreSQL
- SELL → fetch existing memory, update `thesis_status`
- HOLD → no-op

### Node 6: trade_executor_node
- Update `positions` table, adjust cash, insert into `trade_history`
- Broadcast via WebSocket: `{type: "trade", narration, decision, portfolio}`

---

## WebSocket Protocol

```typescript
// Trade decision + narration
{ type: "trade", narration: string, decision: TradeDecision, portfolio: PortfolioSnapshot }

// Agent reasoning (thinking mode)
{ type: "reasoning", text: string }

// Heartbeat — 60s interval
{ type: "heartbeat", timestamp: string, market_open: boolean }

// Portfolio update after execution
{ type: "portfolio_update", portfolio: PortfolioSnapshot }
```

---

## Watchlist — 15 NSE Stocks

```python
WATCHLIST = [
    "INFY.NS", "TCS.NS", "WIPRO.NS",           # IT
    "HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS",   # Banking
    "RELIANCE.NS", "ONGC.NS",                    # Energy
    "MARUTI.NS", "TATAMOTORS.NS", "M&M.NS",       # Auto
    "HINDUNILVR.NS", "ITC.NS", "NESTLEIND.NS",  # FMCG
    "^NSEI",                                     # NIFTY50 (comparison only, never traded)
]

SECTORS = {
    "IT": ["INFY.NS", "TCS.NS", "WIPRO.NS"],
    "Banking": ["HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS"],
    "Energy": ["RELIANCE.NS", "ONGC.NS"],
    "Auto": ["MARUTI.NS", "TATAMOTORS.NS", "M&M.NS"],
    "FMCG": ["HINDUNILVR.NS", "ITC.NS", "NESTLEIND.NS"],
}
```

---

## Environment Variables

```bash
# LLM
ANTHROPIC_API_KEY=sk-ant-...

# Database
DATABASE_URL=postgresql://phantom:phantom@localhost:5432/phantom

# Redis
REDIS_URL=redis://localhost:6379

# News
NEWS_API_KEY=...

# Portfolio limits
INITIAL_PORTFOLIO_VALUE=100000
MAX_POSITION_PCT=0.20
MAX_SECTOR_PCT=0.40
MIN_CASH_PCT=0.10
MAX_POSITIONS=5

# Agent behaviour
AGENT_CYCLE_MINUTES=15
MIN_CONFIDENCE_TO_TRADE=0.65

# Frontend
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws/feed
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## Key Implementation Rules

1. **Paper trades only** — never integrate real brokerage APIs.
2. **AI reasons, pandas-ta signals** — LLM synthesises deterministic signals, never generates them.
3. **Narration quality is the product** — disproportionate time on `narration_node` prompt. Test on non-technical people.
4. **Memory persists across restarts** — Redis (fast) AND PostgreSQL (durable). Both always updated together.
5. **Risk checker is pure Python** — deterministic, unbypassable, no LLM.
6. **context_builder.py owns all data assembly** — nodes receive ready-to-use PhantomState, do zero fetching.
7. **Config validates at startup** — missing env var = loud crash, not silent failure.
8. **Demo mode built before dashboard** — frontend developed against pre-recorded data, live WS wired last.
9. **Cache aggressively** — sentiment 1hr TTL, signals 15min TTL.
10. **Layer gate rule** — don't move to the next layer until the current layer's deliverable is verified.
