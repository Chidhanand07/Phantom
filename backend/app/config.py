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

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "case_sensitive": False}


settings = Settings()
