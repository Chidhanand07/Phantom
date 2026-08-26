# Phantom 👻

**An autonomous AI portfolio manager for Indian equity markets.**

Phantom watches 14 NSE-listed stocks across 5 sectors, runs a multi-step reasoning pipeline powered by a large language model, and makes buy/sell/hold decisions every 15 minutes during market hours — all on a paper portfolio. Every decision is narrated in plain English and streamed live to a real-time dashboard.

> "A portfolio that thinks for itself."

---

## How it works

Every 15 minutes (Mon–Fri, 9:15–15:30 IST), Phantom:

1. **Fetches** live OHLCV prices and computes technical signals (RSI-14, MACD, SMA-20, volume) for all 14 stocks
2. **Reads** news headlines and scores sentiment per stock using an LLM
3. **Reasons** — writes 2–3 paragraphs of analysis like a fund manager would
4. **Decides** — outputs a structured BUY / SELL / HOLD decision with confidence score
5. **Risk-checks** — validates position size ≤20%, cash reserve ≥10%, max 5 positions, sector exposure ≤40%
6. **Narrates** — translates the decision into plain English (no jargon)
7. **Remembers** — stores an investment thesis with target price and stop loss
8. **Executes** — updates the paper portfolio and broadcasts the trade live via WebSocket

```
APScheduler (15 min)
  └─► Context Builder (prices + signals + sentiment + memories)
        └─► LangGraph Pipeline
              reason → decide → risk_check → narrate → remember → execute
                                    │
                                    └─► WebSocket → Next.js Dashboard
```

---

## Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.12 · FastAPI · Uvicorn |
| AI Pipeline | LangChain · LangGraph |
| LLM | Anthropic API |
| Database | PostgreSQL 16 · SQLAlchemy 2 · Alembic |
| Cache | Redis 7 |
| Scheduling | APScheduler 3 |
| Market Data | yfinance |
| News | NewsAPI · Google RSS (fallback) |
| Frontend | Next.js 14 · TypeScript · Tailwind CSS · Recharts |
| Infrastructure | Docker Compose |

---

## Watchlist

| Sector | Stocks |
|---|---|
| IT | INFY · TCS · WIPRO |
| Banking | HDFCBANK · ICICIBANK · SBIN |
| Energy | RELIANCE · ONGC |
| Auto | MARUTI · TATAMOTORS · M&M |
| FMCG | HINDUNILVR · ITC · NESTLEIND |

---

## Setup

### Prerequisites

- Docker & Docker Compose
- Node.js 20+
- An [Anthropic API key](https://console.anthropic.com/)
- A [NewsAPI key](https://newsapi.org/) (free tier works)

### 1. Clone and configure

```bash
git clone https://github.com/<your-username>/phantom.git
cd phantom

cp .env.example .env
# Edit .env — fill in ANTHROPIC_API_KEY and NEWS_API_KEY
```

### 2. Start the backend

```bash
docker compose up --build -d
```

On first run, initialise the database and seed the portfolio:

```bash
# Run migrations
docker compose exec api alembic upgrade head

# Seed a ₹1,00,000 paper portfolio
docker compose exec api python -c "
from app.database import SessionLocal
from app.portfolio.models import Portfolio
db = SessionLocal()
db.add(Portfolio(cash=100000))
db.commit()
print('Portfolio seeded')
"
```

The API is now live at **http://localhost:8001**

### 3. Start the frontend

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:3000** — the dashboard connects automatically.

---

## Configuration (`.env`)

| Variable | Default | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | — | Anthropic API key (required) |
| `NEWS_API_KEY` | — | NewsAPI key (required) |
| `DATABASE_URL` | `postgresql://phantom:phantom@db:5432/phantom` | Postgres connection |
| `REDIS_URL` | `redis://redis:6379` | Redis connection |
| `INITIAL_PORTFOLIO_VALUE` | `100000` | Starting cash in ₹ |
| `MAX_POSITION_PCT` | `0.20` | Max single position as % of portfolio |
| `MAX_SECTOR_PCT` | `0.40` | Max sector exposure as % of portfolio |
| `MIN_CASH_PCT` | `0.10` | Minimum cash reserve |
| `MAX_POSITIONS` | `5` | Max simultaneous open positions |
| `AGENT_CYCLE_MINUTES` | `15` | How often the agent runs (minutes) |
| `MIN_CONFIDENCE_TO_TRADE` | `0.65` | Minimum LLM confidence to execute a trade |

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `GET` | `/portfolio` | Current portfolio snapshot |
| `GET` | `/portfolio/trades` | Trade history (last 50) |
| `GET` | `/signals/{symbol}` | Technical signals for a stock |
| `GET` | `/memories` | All stored investment theses |
| `WS` | `/ws/feed` | Live agent feed (trades + heartbeat) |

---

## Project Structure

```
phantom/
├── backend/
│   ├── app/
│   │   ├── agent/           # LangGraph pipeline
│   │   │   ├── context_builder.py
│   │   │   ├── graph.py     # Node wiring
│   │   │   ├── memory.py    # Investment thesis CRUD
│   │   │   ├── nodes.py     # reason / decide / risk / narrate
│   │   │   ├── prompts.py   # LLM prompt templates
│   │   │   └── state.py     # PhantomState TypedDict
│   │   ├── api/             # REST routes
│   │   ├── data/            # yfinance · signals · sentiment
│   │   ├── portfolio/       # Models · executor · snapshot
│   │   ├── scheduler/       # APScheduler job
│   │   ├── websocket/       # ConnectionManager · broadcast
│   │   ├── config.py
│   │   ├── database.py
│   │   └── main.py
│   ├── alembic/             # DB migrations
│   ├── tests/               # 13 test modules
│   └── requirements.txt
├── frontend/
│   ├── app/
│   │   └── components/      # AgentFeed · Portfolio · SignalBoard · etc.
│   ├── lib/                 # API helpers · types · WebSocket hook
│   └── package.json
├── docker-compose.yml
└── .env.example
```

---

## Running tests

```bash
cd backend
pip install -r requirements.txt
pytest
```

---

## License

MIT
