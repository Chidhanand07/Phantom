import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-test")
os.environ.setdefault("DATABASE_URL", "postgresql://u:p@localhost/test")
os.environ.setdefault("NEWS_API_KEY", "test-news-key")


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
    session.rollback()
    session.close()


@pytest.fixture
def threadsafe_db_engine():
    """SQLite engine safe for use across threads (for TestClient tests)."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    from app.portfolio.models import Base
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture
def threadsafe_db(threadsafe_db_engine):
    Session = sessionmaker(bind=threadsafe_db_engine)
    session = Session()
    yield session
    session.rollback()
    session.close()
