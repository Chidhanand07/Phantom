"use client";

import { useCallback, useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import type { TooltipContentProps } from "recharts/types/component/Tooltip";
import type { ValueType, NameType } from "recharts/types/component/DefaultTooltipContent";
import { useWebSocket } from "@/lib/useWebSocket";
import type { WsMessage } from "@/lib/types";

interface DataPoint {
  time: string;
  portfolio: number;
}

const INITIAL_VALUE = 100000;

function CustomTooltip({
  active,
  payload,
  label,
}: TooltipContentProps<ValueType, NameType>) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-[#1a1a1e] border border-[#2a2a2e] rounded-lg p-2 text-xs">
      <div className="text-[#555] mb-1">{label}</div>
      {payload.map((p) => (
        <div key={p.name as string} style={{ color: p.color }}>
          {p.name}:{" "}
          ₹
          {Number(p.value).toLocaleString("en-IN", {
            maximumFractionDigits: 0,
          })}
        </div>
      ))}
    </div>
  );
}

export default function PerfChart() {
  const [data, setData] = useState<DataPoint[]>([
    { time: "Start", portfolio: INITIAL_VALUE },
  ]);
  const wsUrl =
    process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000/ws/feed";

  const handleMessage = useCallback((msg: WsMessage) => {
    if (msg.type === "trade" || msg.type === "portfolio_update") {
      const time = new Date().toLocaleTimeString("en-IN", {
        hour: "2-digit",
        minute: "2-digit",
      });
      setData((prev) =>
        [...prev, { time, portfolio: msg.portfolio.total_value }].slice(-50),
      );
    }
  }, []);

  useWebSocket({ url: wsUrl, onMessage: handleMessage });

  const pnl = data[data.length - 1].portfolio - INITIAL_VALUE;
  const pnlPct = (pnl / INITIAL_VALUE) * 100;
  const positive = pnl >= 0;

  return (
    <div className="bg-[#1a1a1e] border border-[#2a2a2e] rounded-xl p-4">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-sm font-semibold uppercase tracking-widest text-[#555]">
          Performance
        </h2>
        <div
          className={`text-sm font-semibold ${positive ? "text-green-400" : "text-red-400"}`}
        >
          {positive ? "+" : ""}₹
          {Math.abs(pnl).toLocaleString("en-IN", { maximumFractionDigits: 0 })}
          <span className="text-xs ml-1 opacity-70">
            ({positive ? "+" : ""}
            {pnlPct.toFixed(2)}%)
          </span>
        </div>
      </div>
      <ResponsiveContainer width="100%" height={180}>
        <LineChart
          data={data}
          margin={{ top: 5, right: 5, left: 0, bottom: 5 }}
        >
          <XAxis
            dataKey="time"
            tick={{ fill: "#555", fontSize: 10 }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            tick={{ fill: "#555", fontSize: 10 }}
            axisLine={false}
            tickLine={false}
            tickFormatter={(v: number) => `₹${(v / 1000).toFixed(0)}k`}
            domain={["auto", "auto"]}
          />
          <Tooltip content={CustomTooltip} />
          <Line
            type="monotone"
            dataKey="portfolio"
            name="Portfolio"
            stroke="#a78bfa"
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4, fill: "#a78bfa" }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
