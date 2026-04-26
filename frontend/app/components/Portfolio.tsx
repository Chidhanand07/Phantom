"use client";

import { useCallback, useEffect, useState } from "react";
import { fetchPortfolio } from "@/lib/api";
import { useWebSocket } from "@/lib/useWebSocket";
import type { PortfolioSnapshot, WsMessage } from "@/lib/types";

function PnlValue({ value, pct }: { value: number; pct?: number }) {
  const positive = value >= 0;
  const color = positive ? "text-green-400" : "text-red-400";
  const prefix = positive ? "+" : "";
  return (
    <span className={color}>
      {prefix}
      ₹{Math.abs(value).toLocaleString("en-IN", { maximumFractionDigits: 0 })}
      {pct !== undefined && (
        <span className="text-xs ml-1 opacity-70">
          ({prefix}
          {pct.toFixed(2)}%)
        </span>
      )}
    </span>
  );
}

export default function Portfolio() {
  const [portfolio, setPortfolio] = useState<PortfolioSnapshot | null>(null);
  const wsUrl =
    process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000/ws/feed";

  useEffect(() => {
    fetchPortfolio().then(setPortfolio).catch(console.error);
  }, []);

  const handleMessage = useCallback((msg: WsMessage) => {
    if (msg.type === "trade" || msg.type === "portfolio_update") {
      setPortfolio(msg.portfolio);
    }
  }, []);

  useWebSocket({ url: wsUrl, onMessage: handleMessage });

  if (!portfolio) {
    return (
      <div className="bg-[#1a1a1e] border border-[#2a2a2e] rounded-xl p-4 animate-pulse h-48" />
    );
  }

  return (
    <div className="bg-[#1a1a1e] border border-[#2a2a2e] rounded-xl p-4">
      <h2 className="text-sm font-semibold uppercase tracking-widest text-[#555] mb-4">
        Portfolio
      </h2>

      <div className="grid grid-cols-3 gap-3 mb-4">
        <div className="bg-[#111114] rounded-lg p-3 text-center">
          <div className="text-lg font-bold text-[#c4b5fd]">
            ₹
            {portfolio.total_value.toLocaleString("en-IN", {
              maximumFractionDigits: 0,
            })}
          </div>
          <div className="text-xs text-[#555] mt-1">Total Value</div>
        </div>
        <div className="bg-[#111114] rounded-lg p-3 text-center">
          <div className="text-lg font-bold text-[#93c5fd]">
            ₹
            {portfolio.cash.toLocaleString("en-IN", {
              maximumFractionDigits: 0,
            })}
          </div>
          <div className="text-xs text-[#555] mt-1">Cash</div>
        </div>
        <div className="bg-[#111114] rounded-lg p-3 text-center">
          <div className="text-lg font-bold">
            <PnlValue
              value={portfolio.unrealized_pnl}
              pct={portfolio.total_pnl_pct}
            />
          </div>
          <div className="text-xs text-[#555] mt-1">Unrealized P&amp;L</div>
        </div>
      </div>

      {portfolio.positions.length === 0 ? (
        <div className="text-[#555] text-sm text-center py-4">
          No open positions
        </div>
      ) : (
        <table className="w-full text-sm">
          <thead>
            <tr className="text-xs text-[#555] border-b border-[#2a2a2e]">
              <th className="text-left py-2">Symbol</th>
              <th className="text-right py-2">Qty</th>
              <th className="text-right py-2">Avg</th>
              <th className="text-right py-2">LTP</th>
              <th className="text-right py-2">P&amp;L</th>
            </tr>
          </thead>
          <tbody>
            {portfolio.positions.map((pos) => (
              <tr key={pos.symbol} className="border-b border-[#1a1a1e]">
                <td className="py-2 font-medium text-[#e8e6e1]">
                  {pos.symbol.replace(".NS", "")}
                  <span className="text-xs text-[#555] ml-1">{pos.sector}</span>
                </td>
                <td className="py-2 text-right text-[#888]">{pos.quantity}</td>
                <td className="py-2 text-right text-[#888]">
                  ₹{pos.avg_price.toLocaleString("en-IN")}
                </td>
                <td className="py-2 text-right text-[#e8e6e1]">
                  ₹{pos.current_price.toLocaleString("en-IN")}
                </td>
                <td className="py-2 text-right">
                  <PnlValue value={pos.unrealized_pnl} pct={pos.pnl_pct} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
