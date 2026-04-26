import fakeredis
from unittest.mock import patch
from app.data.sentiment import get_sentiment, get_all_sentiments, COMPANY_NAMES, _clamp_score
from app.data.fetcher import WATCHLIST


def test_sentiment_cached():
    r = fakeredis.FakeRedis()
    r.setex("sentiment:INFY.NS", 3600, "0.75")

    with patch("app.data.sentiment.fetch_headlines_newsapi") as mock_api:
        score = get_sentiment("INFY.NS", r)
        mock_api.assert_not_called()

    assert score == 0.75


def test_sentiment_live():
    r = fakeredis.FakeRedis()
    with patch("app.data.sentiment.fetch_headlines_newsapi", return_value=["Infosys beats Q3 estimates"]):
        with patch("app.data.sentiment.score_sentiment", return_value=0.65):
            score = get_sentiment("INFY.NS", r)
    assert score == 0.65


def test_sentiment_rss_fallback():
    r = fakeredis.FakeRedis()
    with patch("app.data.sentiment.fetch_headlines_newsapi", return_value=[]):
        with patch("app.data.sentiment.fetch_headlines_rss", return_value=["TCS gains market share"]):
            with patch("app.data.sentiment.score_sentiment", return_value=0.3) as mock_score:
                score = get_sentiment("TCS.NS", r)
    mock_score.assert_called_once_with("TCS.NS", ["TCS gains market share"])
    assert score == 0.3


def test_nifty_always_neutral():
    r = fakeredis.FakeRedis()
    score = get_sentiment("^NSEI", r)
    assert score == 0.0


def test_clamp_score():
    assert _clamp_score(1.5) == 1.0
    assert _clamp_score(-2.0) == -1.0
    assert _clamp_score(0.5) == 0.5
    assert _clamp_score(float("nan")) == 0.0


def test_company_names_cover_watchlist():
    tradeable = [s for s in WATCHLIST if s != "^NSEI"]
    for sym in tradeable:
        assert sym in COMPANY_NAMES, f"Missing company name for {sym}"


def test_sentiment_stored_in_cache():
    r = fakeredis.FakeRedis()
    with patch("app.data.sentiment.fetch_headlines_newsapi", return_value=["Infosys up 5%"]):
        with patch("app.data.sentiment.score_sentiment", return_value=0.4):
            get_sentiment("INFY.NS", r)
    ttl = r.ttl("sentiment:INFY.NS")
    assert 3500 < ttl <= 3600
