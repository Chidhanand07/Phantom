import fakeredis
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

import app.main  # ensure module is loaded before patching
from app.main import app
from app.database import get_db
from app.portfolio.models import Portfolio, Trade


def _seed_portfolio(db, cash=100000.0):
    db.add(Portfolio(cash=cash))
    db.commit()


def test_health():
    with patch("app.main.create_scheduler") as mock_create:
        mock_sched = MagicMock()
        mock_create.return_value = mock_sched
        client = TestClient(app)
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_get_portfolio_returns_cash(threadsafe_db):
    db = threadsafe_db
    _seed_portfolio(db)
    r = fakeredis.FakeRedis()

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    try:
        with patch("app.main.create_scheduler") as mock_create:
            mock_sched = MagicMock()
            mock_create.return_value = mock_sched
            with patch("app.api.portfolio._get_redis", return_value=r):
                with patch("app.api.portfolio.fetch_all_prices", return_value={}):
                    client = TestClient(app)
                    response = client.get("/portfolio")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert data["cash"] == 100000.0
    assert data["positions"] == []


def test_get_trades_empty(threadsafe_db):
    db = threadsafe_db
    _seed_portfolio(db)

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    try:
        with patch("app.main.create_scheduler") as mock_create:
            mock_sched = MagicMock()
            mock_create.return_value = mock_sched
            client = TestClient(app)
            response = client.get("/portfolio/trades")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == []


def test_get_memories_empty(threadsafe_db):
    db = threadsafe_db

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    try:
        with patch("app.main.create_scheduler") as mock_create:
            mock_sched = MagicMock()
            mock_create.return_value = mock_sched
            client = TestClient(app)
            response = client.get("/memories")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == []
