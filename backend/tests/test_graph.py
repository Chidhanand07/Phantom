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

    hold_json = json.dumps({
        "action": "HOLD", "symbol": "", "quantity": 0,
        "price": 0.0, "confidence": 0.5, "rationale": "Watching"
    })

    with patch("app.agent.nodes.ChatAnthropic") as MockLLM:
        instance = MockLLM.return_value
        # reasoning call returns text, decision call returns JSON, narration call returns text
        instance.invoke.side_effect = [
            MagicMock(content="Market is flat, waiting."),
            MagicMock(content=hold_json),
            MagicMock(content="Watching markets."),
        ]
        graph = build_graph(db, r)
        with patch("app.agent.context_builder.fetch_all_prices", return_value={}):
            with patch("app.agent.context_builder.compute_signals", return_value=None):
                with patch("app.agent.context_builder.get_all_sentiments", return_value={}):
                    from app.agent.context_builder import build_phantom_state
                    state = build_phantom_state(db, r)
        result = graph.invoke(state)

    assert result["narration"] == "Watching markets."
    assert result["decision"].action == "HOLD"
