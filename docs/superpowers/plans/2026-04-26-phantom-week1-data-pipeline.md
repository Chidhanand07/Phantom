# Phantom Week 1 — Data Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the data pipeline that fetches live NSE market data, computes technical signals, scores news sentiment, and assembles a clean `PhantomState` context object ready for the LangGraph agent.

**Architecture:** Bottom-up — Docker infrastructure first, then Pydantic config, then DB models, then data fetchers, then signal/sentiment engines, then portfolio state, then the context builder that ties everything into a single PhantomState. Each layer is tested and committed before the next begins.

**Tech Stack:** Python 3.12, Docker Compose, PostgreSQL 16, Redis 7, FastAPI, SQLAlchemy 2.0, Alembic, yfinance, numpy 1.x + pandas-ta, LangChain + Claude Haiku (sentiment), APScheduler, Pydantic Settings, pytest + fakeredis + pytest-mock

---

## File Map

| File | Responsibility |
|---|---|
| `docker-compose.yml` | Runs FastAPI + PostgreSQL + Redis locally |
| `backend/Dockerfile` | Backend container image |
| `backend/requirements.txt` | All Python dependencies pinned |
| `.env.example` | Template for required env vars |
| `.gitignore` | Exclude secrets + build artifacts |
| `backend/app/config.py` | Pydantic Settings — validated at startup |
| `backend/app/database.py` | SQLAlchemy engine + SessionLocal factory |
| `backend/app/portfolio/models.py` | ORM models: Portfolio, Position, Trade, TradeMemory, AgentLog |
| `backend/alembic.ini` | Alembic config |
| `backend/alembic/env.py` | Migration environment |
| `backend/alembic/versions/001_initial.py` | Initial migration |
| `backend/app/data/fetcher.py` | yfinance OHLCV fetch + Redis 15-min cache |
| `backend/app/data/signals.py` | RSI-14, MACD, SMA-20, volume delta → TechnicalSignals |
| `backend/app/data/sentiment.py` | NewsAPI + LangChain scorer + RSS fallback + 1hr cache |
| `backend/app/portfolio/portfolio.py` | PortfolioSnapshot from DB state |
| `backend/app/scheduler/scheduler.py` | APScheduler — every 15min during IST market hours |
| `backend/app/agent/context_builder.py` | Assembles full PhantomState from all data sources |
| `backend/app/agent/state.py` | PhantomState TypedDict + all dataclasses |
| `backend/app/main.py` | Minimal FastAPI app (health check only at this stage) |
| `backend/tests/conftest.py` | pytest fixtures: in-memory DB, fakeredis |
| `backend/tests/test_models.py` | ORM model tests |
| `backend/tests/test_fetcher.py` | Fetcher unit tests (mocked yfinance) |
| `backend/tests/test_signals.py` | Signals unit tests (fixed DataFrame) |
| `backend/tests/test_sentiment.py` | Sentiment tests (mocked NewsAPI + LLM) |
| `backend/tests/test_portfolio.py` | Portfolio snapshot tests |
| `backend/tests/test_context_builder.py` | Context builder integration test |

---

### Task 1: Project scaffold

**Files:**
- Create: `.gitignore`
- Create: `docker-compose.yml`
- Create: `backend/Dockerfile`
- Create: `backend/requirements.txt`
- Create: `.env.example`

- [ ] **Step 1: Initialize git repo**

```bash
cd /Users/chidanandh/Desktop/Phantom
git init
```

Expected output: `Initialized empty Git repository in /Users/chidanandh/Desktop/Phantom/.git/`

- [ ] **Step 2: Create `.gitignore`**

```
.env
__pycache__/
*.pyc
*.pyo
.pytest_cache/
.venv/
venv/
node_modules/
.next/
*.egg-info/
dist/
.DS_Store
pgdata/
.superpowers/
```

- [ ] **Step 3: Create `docker-compose.yml`**

```yaml
version: '3.9'

services:
  api:
    build: ./backend
    ports:
      - "8000:8000"
    env_file: .env
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_started
    volumes:
      - ./backend:/app
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: phantom
      POSTGRES_PASSWORD: phantom
      POSTGRES_DB: phantom
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U phantom"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

volumes:
  pgdata:
```

- [ ] **Step 4: Create `backend/Dockerfile`**

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
```

- [ ] **Step 5: Create `backend/requirements.txt`**

```
fastapi==0.111.0
uvicorn[standard]==0.29.0
sqlalchemy==2.0.30
alembic==1.13.1
psycopg2-binary==2.9.9
redis==5.0.4
pydantic==2.7.1
pydantic-settings==2.2.1
yfinance==0.2.40
pandas==2.2.2
numpy==1.26.4
pandas-ta==0.3.14b0
langchain==0.2.1
langchain-anthropic==0.1.15
anthropic==0.28.0
newsapi-python==0.2.7
apscheduler==3.10.4
feedparser==6.0.11
pytz==2024.1
pytest==8.2.0
pytest-asyncio==0.23.6
pytest-mock==3.14.0
fakeredis==2.23.2
```

- [ ] **Step 6: Create `.env.example`**

```bash
# LLM
ANTHROPIC_API_KEY=sk-ant-...

# Database
DATABASE_URL=postgresql://phantom:phantom@localhost:5432/phantom

# Redis
REDIS_URL=redis://localhost:6379

# News
NEWS_API_KEY=your_newsapi_key_here

# Portfolio limits
INITIAL_PORTFOLIO_VALUE=100000
MAX_POSITION_PCT=0.20
MAX_SECTOR_PCT=0.40
MIN_CASH_PCT=0.10
MAX_POSITIONS=5

# Agent
AGENT_CYCLE_MINUTES=15
MIN_CONFIDENCE_TO_TRADE=0.65

# Frontend
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws/feed
NEXT_PUBLIC_API_URL=http://localhost:8000
```

- [ ] **Step 7: Create backend package structure**

```bash
mkdir -p backend/app/{agent,data,portfolio,scheduler,websocket,api}
mkdir -p backend/tests
touch backend/app/__init__.py
touch backend/app/agent/__init__.py
touch backend/app/data/__init__.py
touch backend/app/portfolio/__init__.py
touch backend/app/scheduler/__init__.py
touch backend/app/websocket/__init__.py
touch backend/app/api/__init__.py
touch backend/tests/__init__.py
```

- [ ] **Step 8: Start Docker services and verify**

First copy `.env.example` to `.env` and fill in real values:
```bash
cp .env.example .env
# Edit .env — fill ANTHROPIC_API_KEY and NEWS_API_KEY with real values
```

Then start:
```bash
docker compose up -d db redis
```

Wait 10 seconds, then verify:
```bash
docker compose ps
```

Expected: both `phantom-db-1` and `phantom-redis-1` show `healthy` / `running`.

- [ ] **Step 9: Commit**

```bash
git add .gitignore docker-compose.yml backend/Dockerfile backend/requirements.txt .env.example backend/app backend/tests
git commit -m "feat: project scaffold — docker, requirements, package structure"
```

---

### Task 2: Pydantic config + database session factory

**Files:**
- Create: `backend/app/config.py`
- Create: `backend/app/database.py`

- [ ] **Step 1: Write failing test for config**

Create `backend/tests/test_config.py`:
```python
import pytest
import os

def test_settings_load_from_env(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@localhost/db")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379")
    monkeypatch.setenv("NEWS_API_KEY", "test-key")

    # Re-import to pick up monkeypatched env
    import importlib
    import backend.app.config as cfg_module
    importlib.reload(cfg_module)
    from backend.app.config import Settings
    s = Settings()

    assert s.anthropic_api_key == "sk-ant-test"
    assert s.max_position_pct == 0.20
    assert s.max_positions == 5
    assert s.min_confidence_to_trade == 0.65

def test_settings_missing_required_field():
    from pydantic_settings import BaseSettings
    from pydantic import ValidationError
    import backend.app.config as cfg_module
    # Ensure required field raises if missing
    with pytest.raises((ValidationError, Exception)):
        from backend.app.config import Settings
        Settings(anthropic_api_key=None, database_url=None, news_api_key=None)
```

- [ ] **Step 2: Run test — confirm it fails**

```bash
cd backend
pip install -r requirements.txt
pytest tests/test_config.py -v
```

Expected: `ModuleNotFoundError: No module named 'backend.app.config'`

- [ ] **Step 3: Create `backend/app/config.py`**

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    anthropic_api_key: str
    database_url: str
    news_api_key: str
    redis_url: str = "redis://localhost:6379"

    initial_portfolio_value: float = 100000.0
    max_position_pct: float = 0.20
    max_sector_pct: float = 0.40
    min_cash_pct: float = 0.10
    max_positions: int = 5

    agent_cycle_minutes: int = 15
    min_confidence_to_trade: float = 0.65

    next_public_ws_url: str = "ws://localhost:8000/ws/feed"
    next_public_api_url: str = "http://localhost:8000"

    model_config = {"env_file": ".env", "case_sensitive": False}


settings = Settings()
```

- [ ] **Step 4: Create `backend/app/database.py`**

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 5: Run test — confirm pass**

```bash
pytest tests/test_config.py -v
```

Expected: both tests pass. (The second test may pass loosely — validation behaviour is acceptable as long as missing fields raise.)

- [ ] **Step 6: Commit**

```bash
git add backend/app/config.py backend/app/database.py backend/tests/test_config.py
git commit -m "feat: pydantic settings config + sqlalchemy session factory"
```

---

### Task 3: SQLAlchemy models + Alembic migration

**Files:**
- Create: `backend/app/portfolio/models.py`
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Create: `backend/alembic/versions/001_initial.py`
- Create: `backend/tests/test_models.py`
- Create: `backend/tests/conftest.py`

- [ ] **Step 1: Write failing test**

Create `backend/tests/conftest.py`:
```python
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

@pytest.fixture
def db_engine():
    engine = create_engine("sqlite:///:memory:")
    from app.portfolio.models import Base
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)

@pytest.fixture
def db(db_engine):
    Session = sessionmaker(bind=db_engine)
    session = Session()
    yield session
    session.close()
```

Create `backend/tests/test_models.py`:
```python
from datetime import datetime
from app.portfolio.models import Portfolio, Position, Trade, TradeMemory, AgentLog


def test_portfolio_creation(db):
    p = Portfolio(cash=100000.0)
    db.add(p)
    db.commit()
    db.refresh(p)
    assert p.id is not None
    assert p.cash == 100000.0


def test_position_creation(db):
    pos = Position(symbol="INFY.NS", quantity=10, avg_price=1500.0, sector="IT")
    db.add(pos)
    db.commit()
    db.refresh(pos)
    assert pos.id is not None
    assert pos.symbol == "INFY.NS"


def test_trade_creation(db):
    t = Trade(
        symbol="INFY.NS",
        action="BUY",
        quantity=10,
        price=1500.0,
        confidence=0.8,
        rationale="Oversold RSI",
        narration="Buying Infosys because...",
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    assert t.id is not None
    assert t.action == "BUY"


def test_trade_memory_creation(db):
    m = TradeMemory(
        stock="INFY.NS",
        action="BUY",
        price=1500.0,
        quantity=10,
        thesis="Q3 beats estimates",
        signals_at_entry={"rsi": 28.0},
        target_price=1700.0,
        stop_loss=1400.0,
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    assert m.thesis_status == "active"
    assert m.id is not None


def test_agent_log_creation(db):
    log = AgentLog(market_open=True, action_taken="BUY", symbol="INFY.NS", duration_seconds=2.3)
    db.add(log)
    db.commit()
    assert log.id is not None
```

- [ ] **Step 2: Run test — confirm it fails**

```bash
pytest tests/test_models.py -v
```

Expected: `ModuleNotFoundError: No module named 'app.portfolio.models'`

- [ ] **Step 3: Create `backend/app/portfolio/models.py`**

```python
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Portfolio(Base):
    __tablename__ = "portfolio"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cash: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class Position(Base):
    __tablename__ = "positions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    avg_price: Mapped[float] = mapped_column(Float, nullable=False)
    sector: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class Trade(Base):
    __tablename__ = "trades"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    symbol: Mapped[str] = mapped_column(String, nullable=False)
    action: Mapped[str] = mapped_column(String, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    rationale: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    narration: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    reasoning: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    executed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class TradeMemory(Base):
    __tablename__ = "trade_memories"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    stock: Mapped[str] = mapped_column(String, nullable=False)
    action: Mapped[str] = mapped_column(String, nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    thesis: Mapped[str] = mapped_column(String, nullable=False)
    signals_at_entry: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    target_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    stop_loss: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    thesis_status: Mapped[str] = mapped_column(String, default="active")


class AgentLog(Base):
    __tablename__ = "agent_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cycle_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    market_open: Mapped[bool] = mapped_column(Boolean, default=True)
    action_taken: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    symbol: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    duration_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
```

- [ ] **Step 4: Run tests — confirm pass**

```bash
pytest tests/test_models.py -v
```

Expected: 5 tests pass.

- [ ] **Step 5: Set up Alembic**

```bash
cd backend
alembic init alembic
```

- [ ] **Step 6: Update `backend/alembic/env.py`**

Replace the content of `backend/alembic/env.py` with:
```python
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.portfolio.models import Base
from app.config import settings

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

- [ ] **Step 7: Generate and run initial migration**

```bash
cd backend
alembic revision --autogenerate -m "initial"
alembic upgrade head
```

Expected: migration file created in `alembic/versions/`, then `INFO  [alembic.runtime.migration] Running upgrade  -> <hash>, initial`

Verify tables exist:
```bash
psql postgresql://phantom:phantom@localhost:5432/phantom -c "\dt"
```

Expected: lists `portfolio`, `positions`, `trades`, `trade_memories`, `agent_logs`.

- [ ] **Step 8: Seed initial portfolio row**

```bash
psql postgresql://phantom:phantom@localhost:5432/phantom \
  -c "INSERT INTO portfolio (cash) VALUES (100000.0) ON CONFLICT DO NOTHING;"
```

- [ ] **Step 9: Commit**

```bash
git add backend/app/portfolio/models.py backend/tests/conftest.py backend/tests/test_models.py \
  backend/alembic.ini backend/alembic/
git commit -m "feat: sqlalchemy models + alembic migration + seed portfolio"
```

---

### Task 4: Watchlist constants + yfinance fetcher

**Files:**
- Create: `backend/app/data/fetcher.py`
- Create: `backend/tests/test_fetcher.py`

- [ ] **Step 1: Write failing test**

Create `backend/tests/test_fetcher.py`:
```python
import json
import pytest
import pandas as pd
import fakeredis
from unittest.mock import patch, MagicMock
from app.data.fetcher import fetch_price, fetch_all_prices, is_market_open, WATCHLIST, SECTORS


def make_mock_history():
    return pd.DataFrame({
        "Open": [1490.0],
        "High": [1510.0],
        "Low": [1485.0],
        "Close": [1500.0],
        "Volume": [1000000],
    })


def test_fetch_price_live(monkeypatch):
    r = fakeredis.FakeRedis()
    mock_ticker = MagicMock()
    mock_ticker.history.return_value = make_mock_history()

    with patch("app.data.fetcher.yf.Ticker", return_value=mock_ticker):
        result = fetch_price("INFY.NS", r)

    assert result is not None
    assert result["symbol"] == "INFY.NS"
    assert result["close"] == 1500.0
    assert result["volume"] == 1000000


def test_fetch_price_cached(monkeypatch):
    r = fakeredis.FakeRedis()
    cached = {"symbol": "INFY.NS", "close": 1234.0, "open": 1230.0, "high": 1240.0, "low": 1220.0, "volume": 500000}
    r.setex("price:INFY.NS", 900, json.dumps(cached))

    with patch("app.data.fetcher.yf.Ticker") as mock_ticker:
        result = fetch_price("INFY.NS", r)
        mock_ticker.assert_not_called()

    assert result["close"] == 1234.0


def test_fetch_price_sets_cache():
    r = fakeredis.FakeRedis()
    mock_ticker = MagicMock()
    mock_ticker.history.return_value = make_mock_history()

    with patch("app.data.fetcher.yf.Ticker", return_value=mock_ticker):
        fetch_price("INFY.NS", r)

    assert r.exists("price:INFY.NS")
    ttl = r.ttl("price:INFY.NS")
    assert 800 < ttl <= 900


def test_watchlist_has_15_stocks():
    tradeable = [s for s in WATCHLIST if s != "^NSEI"]
    assert len(tradeable) == 14  # 15 - NIFTY


def test_sectors_cover_all_watchlist():
    all_sector_stocks = [s for stocks in SECTORS.values() for s in stocks]
    tradeable = [s for s in WATCHLIST if s != "^NSEI"]
    assert set(all_sector_stocks) == set(tradeable)


def test_is_market_open_returns_bool():
    result = is_market_open()
    assert isinstance(result, bool)
```

- [ ] **Step 2: Run test — confirm it fails**

```bash
pytest tests/test_fetcher.py -v
```

Expected: `ModuleNotFoundError: No module named 'app.data.fetcher'`

- [ ] **Step 3: Create `backend/app/data/fetcher.py`**

```python
import json
from datetime import datetime
from typing import Optional

import pytz
import redis
import yfinance as yf

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

    ticker = yf.Ticker(symbol)
    hist = ticker.history(period="2d", interval="15m")
    if hist.empty:
        return None

    latest = hist.iloc[-1]
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
```

- [ ] **Step 4: Run tests — confirm pass**

```bash
pytest tests/test_fetcher.py -v
```

Expected: 6 tests pass.

- [ ] **Step 5: Commit**

```bash
git add backend/app/data/fetcher.py backend/tests/test_fetcher.py
git commit -m "feat: yfinance fetcher with 15-min redis cache"
```

---

### Task 5: Technical signal engine

**Files:**
- Create: `backend/app/data/signals.py`
- Create: `backend/tests/test_signals.py`

- [ ] **Step 1: Write failing test**

Create `backend/tests/test_signals.py`:
```python
import json
import numpy as np
import pandas as pd
import fakeredis
from unittest.mock import patch
from app.data.signals import compute_signals, TechnicalSignals


def _make_df(n=100, trend="flat") -> pd.DataFrame:
    """Build a synthetic OHLCV DataFrame for testing."""
    np.random.seed(42)
    base = 1500.0
    if trend == "oversold":
        closes = np.linspace(1800, 1300, n) + np.random.randn(n) * 5
    elif trend == "overbought":
        closes = np.linspace(1200, 1900, n) + np.random.randn(n) * 5
    else:
        closes = base + np.random.randn(n) * 20

    volumes = np.random.randint(500_000, 2_000_000, n)
    # Make last bar a volume spike
    volumes[-1] = int(volumes[-5:].mean() * 2.5)

    return pd.DataFrame({
        "Open": closes * 0.995,
        "High": closes * 1.01,
        "Low": closes * 0.99,
        "Close": closes,
        "Volume": volumes,
    })


def test_compute_signals_returns_dataclass():
    r = fakeredis.FakeRedis()
    df = _make_df()
    with patch("app.data.signals.yf.download", return_value=df):
        result = compute_signals("INFY.NS", r)
    assert isinstance(result, TechnicalSignals)
    assert result.symbol == "INFY.NS"


def test_rsi_oversold_detected():
    r = fakeredis.FakeRedis()
    df = _make_df(n=100, trend="oversold")
    with patch("app.data.signals.yf.download", return_value=df):
        result = compute_signals("INFY.NS", r)
    assert result.rsi_signal == "oversold"
    assert result.rsi_value < 30


def test_rsi_overbought_detected():
    r = fakeredis.FakeRedis()
    df = _make_df(n=100, trend="overbought")
    with patch("app.data.signals.yf.download", return_value=df):
        result = compute_signals("INFY.NS", r)
    assert result.rsi_signal == "overbought"
    assert result.rsi_value > 70


def test_volume_spike_detected():
    r = fakeredis.FakeRedis()
    df = _make_df()
    with patch("app.data.signals.yf.download", return_value=df):
        result = compute_signals("INFY.NS", r)
    assert result.volume_signal == "spike"


def test_signals_cached():
    r = fakeredis.FakeRedis()
    df = _make_df()
    with patch("app.data.signals.yf.download", return_value=df) as mock_dl:
        compute_signals("INFY.NS", r)
        compute_signals("INFY.NS", r)
        assert mock_dl.call_count == 1  # second call served from cache


def test_signals_cache_ttl():
    r = fakeredis.FakeRedis()
    df = _make_df()
    with patch("app.data.signals.yf.download", return_value=df):
        compute_signals("INFY.NS", r)
    ttl = r.ttl("signals:INFY.NS")
    assert 800 < ttl <= 900
```

- [ ] **Step 2: Run test — confirm it fails**

```bash
pytest tests/test_signals.py -v
```

Expected: `ModuleNotFoundError: No module named 'app.data.signals'`

- [ ] **Step 3: Create `backend/app/data/signals.py`**

```python
import json
from dataclasses import asdict, dataclass
from typing import Literal, Optional

import numpy as np
import pandas as pd
import redis
import yfinance as yf

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
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
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

    df = yf.download(symbol, period="30d", interval="15m", auto_adjust=True, progress=False)
    if df.empty or len(df) < 30:
        return None

    closes = df["Close"].squeeze()
    volumes = df["Volume"].squeeze()

    rsi_val = _compute_rsi(closes)
    rsi_signal: Literal["oversold", "overbought", "neutral"]
    if rsi_val < 30:
        rsi_signal = "oversold"
    elif rsi_val > 70:
        rsi_signal = "overbought"
    else:
        rsi_signal = "neutral"

    macd_val, macd_hist, macd_signal = _compute_macd(closes)

    sma20 = float(closes.rolling(20).mean().iloc[-1])
    current_price = float(closes.iloc[-1])
    sma20_signal: Literal["above", "below"] = "above" if current_price > sma20 else "below"

    vol_avg = float(volumes.rolling(5).mean().iloc[-1])
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
```

- [ ] **Step 4: Run tests — confirm pass**

```bash
pytest tests/test_signals.py -v
```

Expected: 6 tests pass.

- [ ] **Step 5: Commit**

```bash
git add backend/app/data/signals.py backend/tests/test_signals.py
git commit -m "feat: technical signal engine — RSI, MACD, SMA-20, volume delta"
```

---

### Task 6: News sentiment pipeline

**Files:**
- Create: `backend/app/data/sentiment.py`
- Create: `backend/tests/test_sentiment.py`

- [ ] **Step 1: Write failing test**

Create `backend/tests/test_sentiment.py`:
```python
import fakeredis
from unittest.mock import MagicMock, patch
from app.data.sentiment import get_sentiment, get_all_sentiments, COMPANY_NAMES


def test_sentiment_cached():
    r = fakeredis.FakeRedis()
    r.setex("sentiment:INFY.NS", 3600, "0.75")

    with patch("app.data.sentiment.fetch_headlines_newsapi") as mock_api:
        score = get_sentiment("INFY.NS", r)
        mock_api.assert_not_called()

    assert score == 0.75


def test_sentiment_fetches_and_scores(monkeypatch):
    r = fakeredis.FakeRedis()
    mock_response = MagicMock()
    mock_response.content = "0.65"

    with patch("app.data.sentiment.fetch_headlines_newsapi", return_value=["Infosys beats Q3 estimates"]):
        with patch("app.data.sentiment.ChatAnthropic") as MockLLM:
            mock_chain_result = MagicMock()
            mock_chain_result.content = "0.65"
            MockLLM.return_value.__or__ = MagicMock()
            # Patch score_sentiment directly
            with patch("app.data.sentiment.score_sentiment", return_value=0.65):
                score = get_sentiment("INFY.NS", r)

    assert isinstance(score, float)


def test_nifty_always_neutral():
    r = fakeredis.FakeRedis()
    score = get_sentiment("^NSEI", r)
    assert score == 0.0


def test_sentiment_clamped():
    r = fakeredis.FakeRedis()
    with patch("app.data.sentiment.fetch_headlines_newsapi", return_value=["great news"]):
        with patch("app.data.sentiment.score_sentiment", return_value=1.5):
            # score_sentiment is called inside get_sentiment — patch it
            pass
    # Direct clamp test
    from app.data.sentiment import _clamp_score
    assert _clamp_score(1.5) == 1.0
    assert _clamp_score(-2.0) == -1.0
    assert _clamp_score(0.5) == 0.5


def test_company_names_cover_watchlist():
    from app.data.fetcher import WATCHLIST
    tradeable = [s for s in WATCHLIST if s != "^NSEI"]
    for sym in tradeable:
        assert sym in COMPANY_NAMES, f"Missing company name for {sym}"
```

- [ ] **Step 2: Run test — confirm it fails**

```bash
pytest tests/test_sentiment.py -v
```

Expected: `ModuleNotFoundError: No module named 'app.data.sentiment'`

- [ ] **Step 3: Create `backend/app/data/sentiment.py`**

```python
import redis
import feedparser
from newsapi import NewsApiClient
from langchain_anthropic import ChatAnthropic
from langchain.prompts import ChatPromptTemplate
from app.config import settings
from app.data.fetcher import WATCHLIST

_SENTIMENT_TTL = 3600  # 1 hour

COMPANY_NAMES: dict[str, str] = {
    "INFY.NS": "Infosys",
    "TCS.NS": "TCS Tata Consultancy",
    "WIPRO.NS": "Wipro",
    "HDFCBANK.NS": "HDFC Bank",
    "ICICIBANK.NS": "ICICI Bank",
    "SBIN.NS": "SBI State Bank India",
    "RELIANCE.NS": "Reliance Industries",
    "ONGC.NS": "ONGC Oil Natural Gas",
    "MARUTI.NS": "Maruti Suzuki",
    "TATAMOTORS.NS": "Tata Motors",
    "M&M.NS": "Mahindra Mahindra",
    "HINDUNILVR.NS": "Hindustan Unilever HUL",
    "ITC.NS": "ITC Limited",
    "NESTLEIND.NS": "Nestle India",
}

_SENTIMENT_PROMPT = ChatPromptTemplate.from_template(
    "You are a financial sentiment analyst. Given these news headlines about {company}, "
    "return a single float between -1.0 (very negative) and +1.0 (very positive). "
    "Return ONLY the number, nothing else.\n\nHeadlines:\n{headlines}\n\nScore:"
)


def _clamp_score(v: float) -> float:
    return max(-1.0, min(1.0, v))


def fetch_headlines_newsapi(symbol: str) -> list[str]:
    company = COMPANY_NAMES.get(symbol, symbol)
    try:
        client = NewsApiClient(api_key=settings.news_api_key)
        resp = client.get_everything(q=company, language="en", page_size=10, sort_by="publishedAt")
        return [a["title"] for a in resp.get("articles", [])]
    except Exception:
        return []


def fetch_headlines_rss(symbol: str) -> list[str]:
    company = COMPANY_NAMES.get(symbol, symbol.replace(".NS", ""))
    query = company.replace(" ", "+")
    url = f"https://news.google.com/rss/search?q={query}+stock&hl=en-IN&gl=IN"
    try:
        feed = feedparser.parse(url)
        return [e.title for e in feed.entries[:10]]
    except Exception:
        return []


def score_sentiment(symbol: str, headlines: list[str]) -> float:
    if not headlines:
        return 0.0
    llm = ChatAnthropic(
        model="claude-haiku-4-5-20251001",
        anthropic_api_key=settings.anthropic_api_key,
        max_tokens=10,
    )
    chain = _SENTIMENT_PROMPT | llm
    company = COMPANY_NAMES.get(symbol, symbol)
    result = chain.invoke({"company": company, "headlines": "\n".join(headlines)})
    try:
        return _clamp_score(float(result.content.strip()))
    except (ValueError, AttributeError):
        return 0.0


def get_sentiment(symbol: str, r: redis.Redis) -> float:
    if symbol == "^NSEI":
        return 0.0

    cache_key = f"sentiment:{symbol}"
    cached = r.get(cache_key)
    if cached:
        return float(cached)

    headlines = fetch_headlines_newsapi(symbol)
    if not headlines:
        headlines = fetch_headlines_rss(symbol)

    score = score_sentiment(symbol, headlines)
    r.setex(cache_key, _SENTIMENT_TTL, str(score))
    return score


def get_all_sentiments(r: redis.Redis) -> dict[str, float]:
    return {sym: get_sentiment(sym, r) for sym in WATCHLIST if sym != "^NSEI"}
```

- [ ] **Step 4: Run tests — confirm pass**

```bash
pytest tests/test_sentiment.py -v
```

Expected: 5 tests pass.

- [ ] **Step 5: Commit**

```bash
git add backend/app/data/sentiment.py backend/tests/test_sentiment.py
git commit -m "feat: news sentiment pipeline — NewsAPI + LangChain + RSS fallback + 1hr cache"
```

---

### Task 7: Portfolio state management

**Files:**
- Create: `backend/app/portfolio/portfolio.py`
- Create: `backend/tests/test_portfolio.py`

- [ ] **Step 1: Write failing test**

Create `backend/tests/test_portfolio.py`:
```python
from app.portfolio.models import Portfolio, Position
from app.portfolio.portfolio import get_portfolio_snapshot, PortfolioSnapshot


def _seed(db):
    db.add(Portfolio(cash=80000.0))
    db.add(Position(symbol="INFY.NS", quantity=10, avg_price=1500.0, sector="IT"))
    db.add(Position(symbol="TCS.NS", quantity=5, avg_price=3800.0, sector="IT"))
    db.commit()


def test_snapshot_cash(db):
    _seed(db)
    prices = {"INFY.NS": {"close": 1600.0}, "TCS.NS": {"close": 4000.0}}
    snap = get_portfolio_snapshot(db, prices)
    assert snap.cash == 80000.0


def test_snapshot_total_value(db):
    _seed(db)
    prices = {"INFY.NS": {"close": 1600.0}, "TCS.NS": {"close": 4000.0}}
    snap = get_portfolio_snapshot(db, prices)
    # 80000 + 10*1600 + 5*4000 = 80000 + 16000 + 20000 = 116000
    assert snap.total_value == pytest.approx(116000.0)


def test_snapshot_pnl(db):
    _seed(db)
    prices = {"INFY.NS": {"close": 1600.0}, "TCS.NS": {"close": 4000.0}}
    snap = get_portfolio_snapshot(db, prices)
    # Holdings value: 10*1600 + 5*4000 = 36000; cost basis: 10*1500 + 5*3800 = 34000
    assert snap.unrealized_pnl == pytest.approx(2000.0)


def test_snapshot_positions(db):
    _seed(db)
    prices = {"INFY.NS": {"close": 1600.0}, "TCS.NS": {"close": 4000.0}}
    snap = get_portfolio_snapshot(db, prices)
    assert len(snap.positions) == 2


def test_snapshot_no_positions(db):
    db.add(Portfolio(cash=100000.0))
    db.commit()
    snap = get_portfolio_snapshot(db, {})
    assert snap.total_value == 100000.0
    assert snap.positions == []


import pytest
```

- [ ] **Step 2: Run test — confirm it fails**

```bash
pytest tests/test_portfolio.py -v
```

Expected: `ModuleNotFoundError: No module named 'app.portfolio.portfolio'`

- [ ] **Step 3: Create `backend/app/portfolio/portfolio.py`**

```python
from dataclasses import dataclass, field
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.portfolio.models import Portfolio, Position


@dataclass
class PositionSnapshot:
    symbol: str
    quantity: int
    avg_price: float
    current_price: float
    sector: str
    market_value: float
    unrealized_pnl: float
    pnl_pct: float


@dataclass
class PortfolioSnapshot:
    cash: float
    positions: list[PositionSnapshot]
    total_value: float
    unrealized_pnl: float
    initial_value: float = 100000.0

    @property
    def holdings_value(self) -> float:
        return sum(p.market_value for p in self.positions)

    @property
    def total_pnl_pct(self) -> float:
        return (self.total_value - self.initial_value) / self.initial_value * 100


def get_portfolio_snapshot(db: Session, prices: dict[str, dict]) -> PortfolioSnapshot:
    portfolio = db.execute(select(Portfolio)).scalar_one_or_none()
    cash = portfolio.cash if portfolio else 100000.0

    positions_rows = db.execute(select(Position)).scalars().all()
    position_snapshots = []
    total_pnl = 0.0

    for pos in positions_rows:
        price_data = prices.get(pos.symbol, {})
        current_price = price_data.get("close", pos.avg_price)
        market_value = pos.quantity * current_price
        cost_basis = pos.quantity * pos.avg_price
        pnl = market_value - cost_basis
        pnl_pct = (pnl / cost_basis * 100) if cost_basis else 0.0
        total_pnl += pnl

        position_snapshots.append(PositionSnapshot(
            symbol=pos.symbol,
            quantity=pos.quantity,
            avg_price=pos.avg_price,
            current_price=current_price,
            sector=pos.sector or "",
            market_value=market_value,
            unrealized_pnl=pnl,
            pnl_pct=pnl_pct,
        ))

    total_value = cash + sum(p.market_value for p in position_snapshots)

    return PortfolioSnapshot(
        cash=cash,
        positions=position_snapshots,
        total_value=total_value,
        unrealized_pnl=total_pnl,
    )
```

- [ ] **Step 4: Run tests — confirm pass**

```bash
pytest tests/test_portfolio.py -v
```

Expected: 5 tests pass.

- [ ] **Step 5: Commit**

```bash
git add backend/app/portfolio/portfolio.py backend/tests/test_portfolio.py
git commit -m "feat: portfolio snapshot — holdings, P&L, market value from DB"
```

---

### Task 8: PhantomState + context builder

**Files:**
- Create: `backend/app/agent/state.py`
- Create: `backend/app/agent/context_builder.py`
- Create: `backend/tests/test_context_builder.py`

- [ ] **Step 1: Write failing test**

Create `backend/tests/test_context_builder.py`:
```python
import fakeredis
from unittest.mock import patch, MagicMock
from app.agent.context_builder import build_phantom_state
from app.agent.state import PhantomState
from app.portfolio.models import Portfolio
from app.data.signals import TechnicalSignals


def _seed_portfolio(db):
    db.add(Portfolio(cash=100000.0))
    db.commit()


def _make_signals(sym="INFY.NS") -> TechnicalSignals:
    return TechnicalSignals(
        symbol=sym, rsi_value=45.0, rsi_signal="neutral",
        macd_signal="neutral", macd_value=0.0, macd_hist=0.0,
        sma20_signal="above", sma20_value=1450.0,
        current_price=1500.0, volume_signal="normal", volume_ratio=1.0,
    )


def test_build_phantom_state_returns_state(db):
    _seed_portfolio(db)
    r = fakeredis.FakeRedis()

    with patch("app.agent.context_builder.fetch_all_prices", return_value={"INFY.NS": {"close": 1500.0}}):
        with patch("app.agent.context_builder.compute_signals", return_value=_make_signals()):
            with patch("app.agent.context_builder.get_all_sentiments", return_value={"INFY.NS": 0.3}):
                state = build_phantom_state(db, r)

    assert isinstance(state, PhantomState)
    assert state.portfolio.cash == 100000.0
    assert state.reasoning == ""
    assert state.risk_approved is False


def test_build_phantom_state_includes_signals(db):
    _seed_portfolio(db)
    r = fakeredis.FakeRedis()

    with patch("app.agent.context_builder.fetch_all_prices", return_value={}):
        with patch("app.agent.context_builder.compute_signals", return_value=_make_signals("INFY.NS")):
            with patch("app.agent.context_builder.get_all_sentiments", return_value={"INFY.NS": 0.5}):
                state = build_phantom_state(db, r)

    assert "INFY.NS" in state.signals
    assert state.signals["INFY.NS"].rsi_value == 45.0


def test_build_phantom_state_sentiment_included(db):
    _seed_portfolio(db)
    r = fakeredis.FakeRedis()

    with patch("app.agent.context_builder.fetch_all_prices", return_value={}):
        with patch("app.agent.context_builder.compute_signals", return_value=None):
            with patch("app.agent.context_builder.get_all_sentiments", return_value={"RELIANCE.NS": 0.8}):
                state = build_phantom_state(db, r)

    assert state.sentiment.get("RELIANCE.NS") == 0.8
```

- [ ] **Step 2: Run test — confirm it fails**

```bash
pytest tests/test_context_builder.py -v
```

Expected: `ModuleNotFoundError: No module named 'app.agent.state'`

- [ ] **Step 3: Create `backend/app/agent/state.py`**

```python
from dataclasses import dataclass, field
from typing import Any, Literal, Optional, TypedDict
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
```

- [ ] **Step 4: Create `backend/app/agent/context_builder.py`**

```python
from sqlalchemy.orm import Session
from sqlalchemy import select
import redis

from app.agent.state import PhantomState, TradeMemoryData
from app.data.fetcher import fetch_all_prices, WATCHLIST
from app.data.signals import compute_signals
from app.data.sentiment import get_all_sentiments
from app.portfolio.portfolio import get_portfolio_snapshot
from app.portfolio.models import TradeMemory, Position


def _get_memories_for_positions(db: Session, r: redis.Redis) -> list[TradeMemoryData]:
    held = db.execute(select(Position)).scalars().all()
    held_symbols = {p.symbol for p in held}

    memories = []
    for sym in held_symbols:
        row = db.execute(
            select(TradeMemory)
            .where(TradeMemory.stock == sym, TradeMemory.thesis_status == "active")
        ).scalar_one_or_none()
        if row:
            memories.append(TradeMemoryData(
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
            ))
    return memories


def build_phantom_state(db: Session, r: redis.Redis) -> PhantomState:
    prices = fetch_all_prices(r)
    portfolio = get_portfolio_snapshot(db, prices)

    signals: dict = {}
    for sym in WATCHLIST:
        if sym == "^NSEI":
            continue
        sig = compute_signals(sym, r)
        if sig is not None:
            signals[sym] = sig

    sentiment = get_all_sentiments(r)
    memories = _get_memories_for_positions(db, r)

    return PhantomState(
        portfolio=portfolio,
        signals=signals,
        sentiment=sentiment,
        memories=memories,
        reasoning="",
        decision=None,
        narration="",
        risk_approved=False,
        risk_notes="",
    )
```

- [ ] **Step 5: Run tests — confirm pass**

```bash
pytest tests/test_context_builder.py -v
```

Expected: 3 tests pass.

- [ ] **Step 6: Commit**

```bash
git add backend/app/agent/state.py backend/app/agent/context_builder.py backend/tests/test_context_builder.py
git commit -m "feat: PhantomState TypedDict + context builder assembles clean agent state"
```

---

### Task 9: APScheduler + minimal FastAPI app

**Files:**
- Create: `backend/app/scheduler/scheduler.py`
- Create: `backend/app/main.py`

- [ ] **Step 1: Create `backend/app/main.py`** (minimal — just health check for now)

```python
from fastapi import FastAPI

app = FastAPI(title="Phantom", version="0.1.0")


@app.get("/health")
def health():
    return {"status": "ok"}
```

- [ ] **Step 2: Create `backend/app/scheduler/scheduler.py`**

```python
import logging
import time
from datetime import datetime

import pytz
import redis
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session

from app.agent.context_builder import build_phantom_state
from app.config import settings
from app.database import SessionLocal
from app.portfolio.models import AgentLog

logger = logging.getLogger(__name__)
IST = pytz.timezone("Asia/Kolkata")


def is_market_open() -> bool:
    from app.data.fetcher import is_market_open as _check
    return _check()


def run_agent_cycle() -> None:
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
        logger.info("Context built — portfolio cash: %.2f", state["portfolio"].cash)

        # Agent graph invocation will be wired here in Week 2
        log.action_taken = "CONTEXT_BUILT"

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

- [ ] **Step 3: Wire scheduler into FastAPI app**

Update `backend/app/main.py`:
```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.scheduler.scheduler import create_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = create_scheduler()
    scheduler.start()
    yield
    scheduler.shutdown()


app = FastAPI(title="Phantom", version="0.1.0", lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok"}
```

- [ ] **Step 4: Start full Docker stack and verify**

```bash
docker compose up --build -d
```

Wait 30 seconds, then:
```bash
curl http://localhost:8000/health
```

Expected:
```json
{"status": "ok"}
```

Check logs to confirm scheduler started:
```bash
docker compose logs api | grep -i scheduler
```

- [ ] **Step 5: Run full test suite**

```bash
cd backend
pytest tests/ -v
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add backend/app/main.py backend/app/scheduler/scheduler.py
git commit -m "feat: apscheduler runs agent cycle every 15min during IST market hours"
```

---

### Week 1 Verification

Run this to confirm Week 1 is complete:

```bash
cd backend
pytest tests/ -v --tb=short
```

Expected: all tests pass with no errors.

Manual smoke test (run during market hours, or just verify context builds):
```bash
docker compose exec api python -c "
import redis
from app.database import SessionLocal
from app.agent.context_builder import build_phantom_state
from app.config import settings

r = redis.Redis.from_url(settings.redis_url, decode_responses=True)
db = SessionLocal()
state = build_phantom_state(db, r)
print('Cash:', state['portfolio'].cash)
print('Signals count:', len(state['signals']))
print('Sentiment keys:', list(state['sentiment'].keys())[:3])
db.close()
"
```

Expected: prints cash=100000.0, signal count for available symbols, sentiment keys list.

Week 1 is complete when this runs without errors.
