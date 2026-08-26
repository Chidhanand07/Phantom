<div align="center">

# 👻 Phantom

### An Autonomous AI Portfolio Manager for Indian Equity Markets

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-14-000000?style=flat-square&logo=nextdotjs&logoColor=white)](https://nextjs.org)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2-FF6B6B?style=flat-square)](https://langchain-ai.github.io/langgraph)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?style=flat-square&logo=postgresql&logoColor=white)](https://postgresql.org)
[![Redis](https://img.shields.io/badge/Redis-7-DC382D?style=flat-square&logo=redis&logoColor=white)](https://redis.io)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat-square&logo=docker&logoColor=white)](https://docker.com)

<br/>

> *"A portfolio that thinks for itself."*

</div>

---

## Overview

Phantom is a fully autonomous paper-trading agent built for NSE-listed Indian equities. It runs a multi-step AI reasoning pipeline every 15 minutes during market hours — fetching live prices, scoring news sentiment, reasoning like a fund manager, checking risk constraints, and executing trades — all without human intervention. Every decision is narrated in plain English and streamed live to a real-time dashboard.

---

## How It Works

```
┌─────────────────────────────────────────────────────────────────┐
│                   APScheduler  (every 15 min)                   │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Context Builder                             │
│          Prices · Technical Signals · News Sentiment            │
│                  Investment Memories (DB)                       │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                    LangGraph Pipeline                           │
│                                                                 │
│   reason ──► decide ──► risk_check ──► narrate                 │
│                              │              │                   │
│                           (blocked)      remember               │
│                              │              │                   │
│                             END          execute                │
└─────────────────────────────────────────────────────┬───────────┘
                                                      │
                          ┌───────────────────────────┤
                          ▼                           ▼
                   PostgreSQL                   WebSocket
                   (trades, memory)          (live dashboard)
```

Each cycle, Phantom:

1. **Fetches** live OHLCV data and computes RSI-14, MACD, SMA-20, and volume signals for 14 NSE stocks
2. **Scores** news sentiment per stock via LLM-powered headline analysis (NewsAPI + Google RSS fallback)
3. **Reasons** — writes 2–3 paragraphs of analysis considering signals, sentiment, and stored theses
4. **Decides** — outputs a structured `BUY / SELL / HOLD` with confidence score and rationale
5. **Risk-checks** — enforces position limits, cash reserve, max positions, and sector concentration
6. **Narrates** — explains the decision in plain English, no financial jargon
7. **Remembers** — persists an investment thesis with target price and stop loss
8. **Executes** — updates the paper portfolio and broadcasts the trade live over WebSocket

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | Python 3.12 · FastAPI · Uvicorn |
| **AI Pipeline** | LangChain 0.2 · LangGraph 0.2 |
| **LLM** | Anthropic API |
| **Database** | PostgreSQL 16 · SQLAlchemy 2 · Alembic |
| **Cache** | Redis 7 |
| **Scheduler** | APScheduler 3 |
| **Market Data** | yfinance |
| **News** | NewsAPI · Google RSS (fallback) |
| **Frontend** | Next.js 14 · TypeScript · Tailwind CSS · Recharts |
| **Infrastructure** | Docker Compose |

---

## Watchlist (14 Stocks · 5 Sectors)

| Sector | Symbols |
|---|---|
| 🖥️ IT | INFY · TCS · WIPRO |
| 🏦 Banking | HDFCBANK · ICICIBANK · SBIN |
| ⚡ Energy | RELIANCE · ONGC |
| 🚗 Auto | MARUTI · TATAMOTORS · M&M |
| 🛒 FMCG | HINDUNILVR · ITC · NESTLEIND |

---

## Risk Controls

Phantom enforces hard constraints before every trade:

| Rule | Limit |
|---|---|
| Max position size | 20% of portfolio |
| Max sector exposure | 40% of portfolio |
| Minimum cash reserve | 10% of portfolio |
| Max simultaneous positions | 5 |
| Minimum LLM confidence to trade | 65% |

---

## Setup

### Prerequisites

- [Docker](https://docker.com/) & Docker Compose
- [Node.js](https://nodejs.org/) 20+
- [Anthropic API key](https://console.anthropic.com/)
- [NewsAPI key](https://newsapi.org/) *(free tier works)*

### 1 · Configure environment

```bash
git clone https://github.com/chidanandh/phantom.git
cd phantom

cp .env.example .env
```

Open `.env` and fill in your keys:

```env
ANTHROPIC_API_KEY=sk-ant-your-key-here
NEWS_API_KEY=your-newsapi-key-here
```

### 2 · Start the backend

```bash
docker compose up --build -d
```

First-time database setup:

```bash
# Apply schema migrations
docker compose exec api alembic upgrade head

# Seed a ₹1,00,000 paper portfolio
docker compose exec api python -c "
from app.database import SessionLocal
from app.portfolio.models import Portfolio
db = SessionLocal()
db.add(Portfolio(cash=100000))
db.commit()
print('Portfolio seeded.')
"
```

API is live at → **http://localhost:8001**

### 3 · Start the frontend

```bash
cd frontend
npm install
npm run dev
```

Dashboard is live at → **http://localhost:3000**

The agent will begin trading automatically at the next 15-minute interval during market hours (Mon–Fri 9:15–15:30 IST).

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | *(required)* | Anthropic API key |
| `NEWS_API_KEY` | *(required)* | NewsAPI.org key |
| `DATABASE_URL` | `postgresql://phantom:phantom@db:5432/phantom` | PostgreSQL connection string |
| `REDIS_URL` | `redis://redis:6379` | Redis connection string |
| `INITIAL_PORTFOLIO_VALUE` | `100000` | Starting cash in ₹ |
| `MAX_POSITION_PCT` | `0.20` | Max single-stock allocation |
| `MAX_SECTOR_PCT` | `0.40` | Max sector allocation |
| `MIN_CASH_PCT` | `0.10` | Minimum cash reserve |
| `MAX_POSITIONS` | `5` | Max open positions |
| `AGENT_CYCLE_MINUTES` | `15` | Agent run frequency |
| `MIN_CONFIDENCE_TO_TRADE` | `0.65` | Min LLM confidence to act |

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `GET` | `/portfolio` | Live portfolio snapshot with P&L |
| `GET` | `/portfolio/trades` | Trade history (latest 50) |
| `GET` | `/signals/{symbol}` | Technical signals for a stock |
| `GET` | `/memories` | All stored investment theses |
| `WS` | `/ws/feed` | Live agent feed (trades + heartbeat) |

---

## Project Structure

```
phantom/
├── backend/
│   ├── app/
│   │   ├── agent/
│   │   │   ├── context_builder.py   # Assembles agent state
│   │   │   ├── graph.py             # LangGraph node wiring
│   │   │   ├── memory.py            # Investment thesis CRUD
│   │   │   ├── nodes.py             # reason / decide / risk / narrate
│   │   │   ├── prompts.py           # LLM prompt templates
│   │   │   └── state.py             # PhantomState TypedDict
│   │   ├── api/                     # REST route handlers
│   │   ├── data/                    # Prices · signals · sentiment
│   │   ├── portfolio/               # Models · executor · snapshots
│   │   ├── scheduler/               # APScheduler job
│   │   ├── websocket/               # ConnectionManager · broadcast
│   │   ├── config.py
│   │   ├── database.py
│   │   └── main.py
│   ├── alembic/                     # Database migrations
│   ├── tests/                       # 13 test modules
│   └── requirements.txt
├── frontend/
│   ├── app/
│   │   └── components/              # AgentFeed · Portfolio · SignalBoard · TradeHistory · PerfChart · MemoryViewer
│   ├── lib/                         # API helpers · types · WebSocket hook
│   └── package.json
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## Running Tests

```bash
cd backend
pip install -r requirements.txt
pytest -v
```

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

<div align="center">

Built by **Chidanandh R** · [chidhanand07d@gmail.com](mailto:chidhanand07d@gmail.com)

</div>
