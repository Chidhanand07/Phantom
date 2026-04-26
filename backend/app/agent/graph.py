import logging

import redis
from langgraph.graph import END, StateGraph
from sqlalchemy.orm import Session

from app.agent.memory import write_buy_memory, update_sell_memory
from app.agent.nodes import (
    decision_node, narration_node, reasoning_node,
    risk_check_node, route_risk,
)
from app.agent.state import PhantomState
from app.portfolio.executor import execute_trade

logger = logging.getLogger(__name__)


def _make_memory_executor_node(db: Session, r: redis.Redis):
    def memory_writer_node(state: PhantomState) -> dict:
        decision = state.get("decision")
        if decision is None or decision.action == "HOLD":
            return {}

        signals = state["signals"].get(decision.symbol)
        if decision.action == "BUY" and signals:
            try:
                write_buy_memory(decision, signals, state["reasoning"], db, r)
            except Exception as e:
                logger.warning("Memory write failed: %s", e)
        elif decision.action == "SELL":
            try:
                outcome = "played_out" if decision.confidence > 0.6 else "invalidated"
                update_sell_memory(decision, outcome, db, r)
            except Exception as e:
                logger.warning("Memory update failed: %s", e)

        return {}

    def trade_executor_node(state: PhantomState) -> dict:
        decision = state.get("decision")
        if decision is None or decision.action == "HOLD":
            logger.info("HOLD — no trade executed")
            return {}

        try:
            execute_trade(decision, state["narration"], state["reasoning"], db)
            logger.info(
                "Executed %s %d %s @ %.2f",
                decision.action, decision.quantity, decision.symbol, decision.price,
            )
        except Exception as e:
            logger.error("Trade execution failed: %s", e)

        return {}

    return memory_writer_node, trade_executor_node


def build_graph(db: Session, r: redis.Redis):
    memory_writer_node, trade_executor_node = _make_memory_executor_node(db, r)

    graph = StateGraph(PhantomState)
    graph.add_node("reason", reasoning_node)
    graph.add_node("decide", decision_node)
    graph.add_node("risk_check", risk_check_node)
    graph.add_node("narrate", narration_node)
    graph.add_node("remember", memory_writer_node)
    graph.add_node("execute", trade_executor_node)

    graph.set_entry_point("reason")
    graph.add_edge("reason", "decide")
    graph.add_edge("decide", "risk_check")
    graph.add_conditional_edges("risk_check", route_risk, {
        "approved": "narrate",
        "blocked": END,
    })
    graph.add_edge("narrate", "remember")
    graph.add_edge("remember", "execute")
    graph.add_edge("execute", END)

    return graph.compile()
