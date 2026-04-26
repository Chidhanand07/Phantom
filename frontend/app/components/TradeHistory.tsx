"use client";

import { useCallback, useEffect, useState } from "react";
import { fetchTrades } from "@/lib/api";
import { useWebSocket } from "@/lib/useWebSocket";
import type { Trade, WsMessage } from "@/lib/types";

function TradeRow({ trade }: { trade: Trade }) {
  const [expanded, setExpanded] = useState(false);
  const isBuy = trade.action === "BUY";

  return (
    <div className="border-b border-[#1e1e22] last:border-0">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full text-left py-3 flex items-center gap-3 hover:bg-[#111114] transition-colors px-2 rounded"
      >
        <span
          className={`text-xs font-bold px-2 py-0.5 rounded ${isBuy ? "bg-green-900/40 text-green-400" : "bg-red-900/40 text-red-400"}`}
        >
          {trade.action}
        </span>
        <span className="font-medium text-[#e8e6e1] flex-1">
          {trade.symbol.replace(".NS", "")}
        </span>
        <span className="text-[#888] text-sm">
          {trade.quantity} × ₹{trade.price.toLocaleString("en-IN")}
        </span>
        <span className="text-[#555] text-xs">
          {new Date(trade.executed_at).toLocaleString("en-IN", {
            day: "numeric",
            month: "short",
            hour: "2-digit",
            minute: "2-digit",
          })}
        </span>
        <span className="text-[#555] text-xs">{expanded ? "▲" : "▼"}</span>
      </button>
      {expanded && (
        <div className="px-2 pb-3 space-y-2">
          {trade.narration && (
            <p className="text-sm text-[#aaa] leading-relaxed italic">
              &ldquo;{trade.narration}&rdquo;
            </p>
          )}
          <div className="text-xs text-[#555]">
            Confidence:{" "}
            {trade.confidence
              ? `${(trade.confidence * 100).toFixed(0)}%`
              : "—"}
            {trade.rationale && <> · {trade.rationale}</>}
          </div>
        </div>
      )}
    </div>
  );
}

export default function TradeHistory() {
  const [trades, setTrades] = useState<Trade[]>([]);
  const wsUrl =
    process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000/ws/feed";

  useEffect(() => {
    fetchTrades().then(setTrades).catch(console.error);
  }, []);

  const handleMessage = useCallback((msg: WsMessage) => {
    if (msg.type === "trade" && msg.decision.action !== "HOLD") {
      const newTrade: Trade = {
        id: Date.now().toString(),
        symbol: msg.decision.symbol,
        action: msg.decision.action as "BUY" | "SELL",
        quantity: msg.decision.quantity,
        price: msg.decision.price,
        confidence: msg.decision.confidence,
        rationale: msg.decision.rationale,
        narration: msg.narration,
        executed_at: new Date().toISOString(),
      };
      setTrades((prev) => [newTrade, ...prev]);
    }
  }, []);

  useWebSocket({ url: wsUrl, onMessage: handleMessage });

  return (
    <div className="bg-[#1a1a1e] border border-[#2a2a2e] rounded-xl p-4">
      <h2 className="text-sm font-semibold uppercase tracking-widest text-[#555] mb-4">
        Trade History
        <span className="ml-2 text-[#333]">({trades.length})</span>
      </h2>
      {trades.length === 0 ? (
        <div className="text-[#555] text-sm text-center py-6">
          No trades yet
        </div>
      ) : (
        <div>
          {trades.map((t) => (
            <TradeRow key={t.id} trade={t} />
          ))}
        </div>
      )}
    </div>
  );
}
