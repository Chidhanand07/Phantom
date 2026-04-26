"use client";

import { useEffect, useState } from "react";
import { fetchSignals, WATCHLIST } from "@/lib/api";
import type { TechnicalSignals } from "@/lib/types";

function RsiBar({ value, signal }: { value: number; signal: string }) {
  const color =
    signal === "oversold"
      ? "bg-green-500"
      : signal === "overbought"
        ? "bg-red-500"
        : "bg-[#555]";
  return (
    <div className="flex items-center gap-2">
      <div className="w-16 h-1.5 bg-[#2a2a2e] rounded-full overflow-hidden">
        <div
          className={`h-full ${color} rounded-full`}
          style={{ width: `${value}%` }}
        />
      </div>
      <span className="text-xs text-[#888]">{value.toFixed(0)}</span>
    </div>
  );
}

function MacdDot({ signal }: { signal: string }) {
  const colors: Record<string, string> = {
    bullish_crossover: "bg-green-400",
    bearish_crossover: "bg-red-400",
    neutral: "bg-[#555]",
  };
  return (
    <span
      className={`w-2 h-2 rounded-full inline-block ${colors[signal] ?? "bg-[#555]"}`}
    />
  );
}

export default function SignalBoard() {
  const [signals, setSignals] = useState<Record<string, TechnicalSignals>>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      const results: Record<string, TechnicalSignals> = {};
      await Promise.allSettled(
        WATCHLIST.map(async (sym) => {
          try {
            results[sym] = await fetchSignals(sym);
          } catch {
            // signal unavailable for this symbol
          }
        }),
      );
      setSignals(results);
      setLoading(false);
    };
    load();
    const interval = setInterval(load, 15 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="bg-[#1a1a1e] border border-[#2a2a2e] rounded-xl p-4">
      <h2 className="text-sm font-semibold uppercase tracking-widest text-[#555] mb-4">
        Signal Board
      </h2>
      {loading ? (
        <div className="text-[#555] text-sm text-center py-6">
          Loading signals...
        </div>
      ) : (
        <table className="w-full text-sm">
          <thead>
            <tr className="text-xs text-[#555] border-b border-[#2a2a2e]">
              <th className="text-left py-2">Symbol</th>
              <th className="text-right py-2">Price</th>
              <th className="text-right py-2">RSI</th>
              <th className="text-center py-2">MACD</th>
              <th className="text-center py-2">Vol</th>
            </tr>
          </thead>
          <tbody>
            {WATCHLIST.map((sym) => {
              const sig = signals[sym];
              if (!sig) return null;
              return (
                <tr key={sym} className="border-b border-[#1a1a1e]">
                  <td className="py-2 font-medium text-[#e8e6e1]">
                    {sym.replace(".NS", "")}
                  </td>
                  <td className="py-2 text-right text-[#888]">
                    ₹{sig.current_price.toLocaleString("en-IN")}
                  </td>
                  <td className="py-2">
                    <div className="flex justify-end">
                      <RsiBar value={sig.rsi_value} signal={sig.rsi_signal} />
                    </div>
                  </td>
                  <td className="py-2 text-center">
                    <MacdDot signal={sig.macd_signal} />
                  </td>
                  <td className="py-2 text-center text-xs">
                    {sig.volume_signal === "spike" ? (
                      <span className="text-yellow-400">
                        ⚡ {sig.volume_ratio.toFixed(1)}x
                      </span>
                    ) : (
                      <span className="text-[#555]">—</span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </div>
  );
}
