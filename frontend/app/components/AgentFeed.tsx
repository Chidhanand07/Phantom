"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useWebSocket } from "@/lib/useWebSocket";
import type { WsMessage, TradeDecision } from "@/lib/types";

interface FeedEntry {
  id: string;
  type: "trade" | "reasoning" | "heartbeat";
  narration?: string;
  reasoning?: string;
  decision?: TradeDecision;
  timestamp: string;
}

function TypewriterText({ text, onDone }: { text: string; onDone?: () => void }) {
  const [displayed, setDisplayed] = useState("");
  const indexRef = useRef(0);

  useEffect(() => {
    setDisplayed("");
    indexRef.current = 0;
    const interval = setInterval(() => {
      if (indexRef.current < text.length) {
        setDisplayed(text.slice(0, indexRef.current + 1));
        indexRef.current++;
      } else {
        clearInterval(interval);
        onDone?.();
      }
    }, 18);
    return () => clearInterval(interval);
  }, [text, onDone]);

  return (
    <span>
      {displayed}
      <span className="animate-pulse text-[#a78bfa]">▍</span>
    </span>
  );
}

function DecisionBadge({ decision }: { decision: TradeDecision }) {
  const colors = {
    BUY: "bg-green-900/40 text-green-400 border-green-800",
    SELL: "bg-red-900/40 text-red-400 border-red-800",
    HOLD: "bg-gray-800 text-gray-400 border-gray-700",
  };
  return (
    <div
      className={`inline-flex items-center gap-2 px-3 py-1 rounded-full border text-xs font-semibold mt-2 ${colors[decision.action]}`}
    >
      <span>{decision.action}</span>
      {decision.symbol && <span>{decision.symbol}</span>}
      {decision.quantity > 0 && <span>× {decision.quantity}</span>}
      {decision.price > 0 && (
        <span>@ ₹{decision.price.toLocaleString("en-IN")}</span>
      )}
      <span className="opacity-60">
        {(decision.confidence * 100).toFixed(0)}% confidence
      </span>
    </div>
  );
}

export default function AgentFeed() {
  const [entries, setEntries] = useState<FeedEntry[]>([]);
  const bottomRef = useRef<HTMLDivElement>(null);
  const wsUrl =
    process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000/ws/feed";

  const handleMessage = useCallback((msg: WsMessage) => {
    if (msg.type === "heartbeat") return;

    setEntries((prev) => {
      const entry: FeedEntry = {
        id: `${Date.now()}-${Math.random()}`,
        type: msg.type as FeedEntry["type"],
        timestamp: new Date().toLocaleTimeString("en-IN", {
          hour: "2-digit",
          minute: "2-digit",
        }),
        narration: msg.type === "trade" ? msg.narration : undefined,
        reasoning: msg.type === "reasoning" ? msg.text : undefined,
        decision: msg.type === "trade" ? msg.decision : undefined,
      };
      return [entry, ...prev].slice(0, 50);
    });
  }, []);

  const { connected, marketOpen } = useWebSocket({
    url: wsUrl,
    onMessage: handleMessage,
  });

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [entries]);

  return (
    <div className="bg-[#1a1a1e] border border-[#2a2a2e] rounded-xl p-4 flex flex-col h-full min-h-[400px]">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-sm font-semibold uppercase tracking-widest text-[#555]">
          Live Agent Feed
        </h2>
        <div className="flex items-center gap-2">
          {marketOpen && (
            <span className="text-xs text-green-400 bg-green-900/30 px-2 py-0.5 rounded-full border border-green-800">
              Market Open
            </span>
          )}
          <span
            className={`w-2 h-2 rounded-full ${connected ? "bg-green-400" : "bg-red-500"}`}
          />
          <span className="text-xs text-[#555]">
            {connected ? "Connected" : "Reconnecting..."}
          </span>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto space-y-3 pr-1">
        {entries.length === 0 && (
          <div className="flex items-center justify-center h-32 text-[#555] text-sm">
            Waiting for Phantom to speak...
          </div>
        )}
        {entries.map((entry) => (
          <div
            key={entry.id}
            className="border-l-2 border-[#2a2a2e] pl-3 py-1"
          >
            <div className="text-xs text-[#555] mb-1">{entry.timestamp}</div>
            {entry.type === "trade" && entry.narration && (
              <>
                <p className="text-sm text-[#e8e6e1] leading-relaxed">
                  <TypewriterText text={entry.narration} />
                </p>
                {entry.decision && (
                  <DecisionBadge decision={entry.decision} />
                )}
              </>
            )}
            {entry.type === "reasoning" && entry.reasoning && (
              <p className="text-xs text-[#666] italic leading-relaxed">
                {entry.reasoning}
              </p>
            )}
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
