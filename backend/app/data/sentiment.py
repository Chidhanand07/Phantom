import logging
from typing import Optional

import feedparser
import redis
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from newsapi import NewsApiClient

from app.config import settings
from app.data.fetcher import WATCHLIST

logger = logging.getLogger(__name__)
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
    except Exception as e:
        logger.warning("NewsAPI fetch failed for %s: %s", symbol, e)
        return []


def fetch_headlines_rss(symbol: str) -> list[str]:
    company = COMPANY_NAMES.get(symbol, symbol.replace(".NS", ""))
    query = company.replace(" ", "+")
    url = f"https://news.google.com/rss/search?q={query}+stock&hl=en-IN&gl=IN"
    try:
        feed = feedparser.parse(url)
        return [e.title for e in feed.entries[:10]]
    except Exception as e:
        logger.warning("RSS fetch failed for %s: %s", symbol, e)
        return []


def score_sentiment(symbol: str, headlines: list[str]) -> float:
    if not headlines:
        return 0.0
    llm = ChatAnthropic(
        model="claude-haiku-4-5-20251001",
        api_key=settings.anthropic_api_key,
        max_tokens=10,
    )
    chain = _SENTIMENT_PROMPT | llm
    company = COMPANY_NAMES.get(symbol, symbol)
    try:
        result = chain.invoke({"company": company, "headlines": "\n".join(headlines)})
        return _clamp_score(float(result.content.strip()))
    except (ValueError, AttributeError, Exception) as e:
        logger.warning("Sentiment scoring failed for %s: %s", symbol, e)
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
