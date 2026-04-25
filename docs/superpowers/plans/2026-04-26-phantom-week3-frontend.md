# Phantom Week 3 — Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Prerequisite:** Week 2 plan complete. Backend running on `http://localhost:8000`. WebSocket `/ws/feed` emitting heartbeats.

**Goal:** Build the Next.js 14 dark dashboard — demo mode first (so you can develop without waiting for market hours), then all 6 components, then wire the live WebSocket last.

**Architecture:** Next.js App Router with TypeScript. Components fetch REST on load, then subscribe to WebSocket for live updates. Demo mode is a mock WebSocket server that replays pre-recorded decisions — built Day 15, used for all Day 16–18 component development. Live WS wired on Day 19.

**Tech Stack:** Next.js 14, TypeScript, Tailwind CSS, recharts (performance chart), wscat-compatible WebSocket, Jest + React Testing Library

---

## File Map

| File | Responsibility |
|---|---|
| `frontend/lib/types.ts` | Shared TypeScript interfaces |
| `frontend/lib/demo-data.ts` | Pre-recorded agent decisions for demo mode |
| `frontend/scripts/demo-server.js` | Node.js mock WS server that replays demo-data |
| `frontend/lib/useWebSocket.ts` | WS hook — connects, reconnects, dispatches messages |
| `frontend/lib/api.ts` | REST fetch helpers |
| `frontend/app/layout.tsx` | Root layout — dark theme, fonts |
| `frontend/app/page.tsx` | Main dashboard — grid of all 6 components |
| `frontend/app/components/AgentFeed.tsx` | Live narration stream with typewriter animation |
| `frontend/app/components/Portfolio.tsx` | Holdings table + cash + P&L |
| `frontend/app/components/TradeHistory.tsx` | All trades with collapsible reasoning |
| `frontend/app/components/SignalBoard.tsx` | RSI/MACD/sentiment grid for all stocks |
| `frontend/app/components/MemoryViewer.tsx` | Agent's stored theses for held positions |
| `frontend/app/components/PerfChart.tsx` | Portfolio value vs NIFTY50 over time (recharts) |

---

### Task 1: Next.js project setup

**Files:**
- Create: `frontend/` (Next.js 14 project)
- Create: `frontend/lib/types.ts`

- [ ] **Step 1: Scaffold Next.js project**

```bash
cd /Users/chidanandh/Desktop/Phantom
npx create-next-app@14 frontend \
  --typescript \
  --tailwind \
  --eslint \
  --app \
  --no-src-dir \
  --import-alias "@/*"
```

When prompted, accept all defaults.

- [ ] **Step 2: Install additional dependencies**

```bash
cd frontend
npm install recharts
npm install -D @types/recharts
```

- [ ] **Step 3: Set environment variables**

Create `frontend/.env.local`:
```bash
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws/feed
NEXT_PUBLIC_API_URL=http://localhost:8000
```

- [ ] **Step 4: Create `frontend/lib/types.ts`**

```typescript
export interface TradeDecision {
  action: "BUY" | "SELL" | "HOLD";
  symbol: string;
  quantity: number;
  price: number;
  confidence: number;
  rationale: string;
}

export interface PositionSnapshot {
  symbol: string;
  quantity: number;
  avg_price: number;
  current_price: number;
  market_value: number;
  unrealized_pnl: number;
  pnl_pct: number;
  sector: string;
}

export interface PortfolioSnapshot {
  cash: number;
  total_value: number;
  unrealized_pnl: number;
  total_pnl_pct: number;
  positions: PositionSnapshot[];
}

export interface Trade {
  id: string;
  symbol: string;
  action: "BUY" | "SELL";
  quantity: number;
  price: number;
  confidence: number;
  rationale: string;
  narration: string;
  executed_at: string;
}

export interface TechnicalSignals {
  symbol: string;
  rsi_value: number;
  rsi_signal: "oversold" | "overbought" | "neutral";
  macd_signal: "bullish_crossover" | "bearish_crossover" | "neutral";
  macd_value: number;
  sma20_signal: "above" | "below";
  sma20_value: number;
  current_price: number;
  volume_signal: "spike" | "normal";
  volume_ratio: number;
}

export interface TradeMemory {
  id: string;
  stock: string;
  action: string;
  price: number;
  quantity: number;
  timestamp: string;
  thesis: string;
  signals_at_entry: Record<string, unknown>;
  target_price: number;
  stop_loss: number;
  thesis_status: "active" | "played_out" | "invalidated";
}

// WebSocket message types
export type WsMessage =
  | { type: "trade"; narration: string; decision: TradeDecision; portfolio: PortfolioSnapshot }
  | { type: "reasoning"; text: string }
  | { type: "heartbeat"; timestamp: string; market_open: boolean }
  | { type: "portfolio_update"; portfolio: PortfolioSnapshot };
```

- [ ] **Step 5: Create `frontend/lib/api.ts`**

```typescript
const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function fetchPortfolio(): Promise<import("./types").PortfolioSnapshot> {
  const res = await fetch(`${BASE}/portfolio`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch portfolio");
  return res.json();
}

export async function fetchTrades(): Promise<import("./types").Trade[]> {
  const res = await fetch(`${BASE}/portfolio/trades`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch trades");
  return res.json();
}

export async function fetchSignals(symbol: string): Promise<import("./types").TechnicalSignals> {
  const res = await fetch(`${BASE}/signals/${symbol}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Failed to fetch signals for ${symbol}`);
  return res.json();
}

export async function fetchMemories(): Promise<import("./types").TradeMemory[]> {
  const res = await fetch(`${BASE}/memories`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch memories");
  return res.json();
}

export const WATCHLIST = [
  "INFY.NS", "TCS.NS", "WIPRO.NS",
  "HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS",
  "RELIANCE.NS", "ONGC.NS",
  "MARUTI.NS", "TATAMOTORS.NS", "M&M.NS",
  "HINDUNILVR.NS", "ITC.NS", "NESTLEIND.NS",
];
```

- [ ] **Step 6: Configure Tailwind for dark theme**

Update `frontend/tailwind.config.ts`:
```typescript
import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        phantom: {
          bg: "#0d0d0f",
          card: "#1a1a1e",
          border: "#2a2a2e",
          purple: "#a78bfa",
          teal: "#6ee7b7",
          gold: "#fcd34d",
          blue: "#93c5fd",
          red: "#f87171",
          green: "#4ade80",
          muted: "#555",
          text: "#e8e6e1",
          subtext: "#888",
        },
      },
      fontFamily: {
        mono: ["'Courier New'", "monospace"],
      },
    },
  },
  plugins: [],
};

export default config;
```

- [ ] **Step 7: Create root layout**

Replace `frontend/app/layout.tsx`:
```typescript
import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Phantom — AI Portfolio Manager",
  description: "An autonomous AI that manages a virtual ₹1,00,000 portfolio on NSE markets",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-[#0d0d0f] text-[#e8e6e1] min-h-screen antialiased">
        {children}
      </body>
    </html>
  );
}
```

Update `frontend/app/globals.css` to keep only base Tailwind directives:
```css
@tailwind base;
@tailwind components;
@tailwind utilities;

* {
  box-sizing: border-box;
}

::-webkit-scrollbar {
  width: 4px;
}
::-webkit-scrollbar-track {
  background: #1a1a1e;
}
::-webkit-scrollbar-thumb {
  background: #2a2a2e;
  border-radius: 2px;
}
```

- [ ] **Step 8: Verify Next.js starts**

```bash
cd frontend
npm run dev
```

Open http://localhost:3000. Expected: Next.js default page loads (no errors in terminal).

- [ ] **Step 9: Commit**

```bash
cd ..
git add frontend/
git commit -m "feat: next.js 14 project scaffold — tailwind dark theme, types, api helpers"
```

---

### Task 2: Demo mode — pre-recorded data + mock WS server

**Files:**
- Create: `frontend/lib/demo-data.ts`
- Create: `frontend/scripts/demo-server.js`

- [ ] **Step 1: Create `frontend/lib/demo-data.ts`**

```typescript
import type { WsMessage } from "./types";

export const DEMO_MESSAGES: WsMessage[] = [
  {
    type: "heartbeat",
    timestamp: new Date().toISOString(),
    market_open: true,
  },
  {
    type: "reasoning",
    text: "Scanning 14 stocks across 5 sectors. INFY.NS RSI at 27.4 — deeply oversold. Q3 results beat estimates by 8% last week. News sentiment +0.72. Volume spike 2.3x average. This looks compelling.",
  },
  {
    type: "trade",
    narration:
      "I'm buying Infosys because their stock has dipped while the business got stronger — they just beat their Q3 estimates by 8% and investors haven't caught up yet. Think of it like a sale on a stock that's usually expensive. The heavy trading volume today tells me other smart money is noticing too.",
    decision: {
      action: "BUY",
      symbol: "INFY.NS",
      quantity: 12,
      price: 1487.5,
      confidence: 0.83,
      rationale: "RSI oversold at 27.4, Q3 beat, volume spike 2.3x",
    },
    portfolio: {
      cash: 82150.0,
      total_value: 100035.0,
      unrealized_pnl: 35.0,
      total_pnl_pct: 0.035,
      positions: [
        {
          symbol: "INFY.NS",
          quantity: 12,
          avg_price: 1487.5,
          current_price: 1490.25,
          market_value: 17883.0,
          unrealized_pnl: 33.0,
          pnl_pct: 0.18,
          sector: "IT",
        },
      ],
    },
  },
  {
    type: "heartbeat",
    timestamp: new Date().toISOString(),
    market_open: true,
  },
  {
    type: "reasoning",
    text: "Reliance MACD showing bullish crossover. JioFiber subscriber numbers out today — strong. Sentiment +0.65. Price dipped 2.8% this week on broader market sell-off, not company-specific. Cash at 82% — room to add a position.",
  },
  {
    type: "trade",
    narration:
      "Reliance Industries just announced their JioFiber subscriber count crossed 10 million — that's a telecom land grab happening in real time. The stock dipped this week because the whole market was nervous about global rates, not because anything went wrong at the company. I'm treating that dip as a discount.",
    decision: {
      action: "BUY",
      symbol: "RELIANCE.NS",
      quantity: 8,
      price: 2834.0,
      confidence: 0.77,
      rationale: "MACD bullish crossover, JioFiber expansion, dip on macro noise",
    },
    portfolio: {
      cash: 59422.0,
      total_value: 100487.0,
      unrealized_pnl: 487.0,
      total_pnl_pct: 0.487,
      positions: [
        {
          symbol: "INFY.NS",
          quantity: 12,
          avg_price: 1487.5,
          current_price: 1502.0,
          market_value: 18024.0,
          unrealized_pnl: 174.0,
          pnl_pct: 1.16,
          sector: "IT",
        },
        {
          symbol: "RELIANCE.NS",
          quantity: 8,
          avg_price: 2834.0,
          current_price: 2841.25,
          market_value: 22730.0,
          unrealized_pnl: 58.0,
          pnl_pct: 0.26,
          sector: "Energy",
        },
      ],
    },
  },
  {
    type: "reasoning",
    text: "Reviewing INFY position. Bought 8 days ago. Thesis: Q3 beat would drive re-rating. Stock up 3.2% since entry. Target was ₹1,650. Current price ₹1,535 — thesis is directionally right but hasn't fully played out. Holding.",
  },
  {
    type: "trade",
    narration:
      "My Infosys position is up 3.2% since I bought it — the thesis is working but hasn't fully played out yet. I originally bought because the market underreacted to their strong Q3 results. The stock still has room to re-rate. Holding for now.",
    decision: {
      action: "HOLD",
      symbol: "",
      quantity: 0,
      price: 0,
      confidence: 0.6,
      rationale: "INFY thesis in progress, not yet at target",
    },
    portfolio: {
      cash: 59422.0,
      total_value: 101200.0,
      unrealized_pnl: 1200.0,
      total_pnl_pct: 1.2,
      positions: [
        {
          symbol: "INFY.NS",
          quantity: 12,
          avg_price: 1487.5,
          current_price: 1535.0,
          market_value: 18420.0,
          unrealized_pnl: 570.0,
          pnl_pct: 3.2,
          sector: "IT",
        },
        {
          symbol: "RELIANCE.NS",
          quantity: 8,
          avg_price: 2834.0,
          current_price: 2862.0,
          market_value: 22896.0,
          unrealized_pnl: 224.0,
          pnl_pct: 0.96,
          sector: "Energy",
        },
      ],
    },
  },
  {
    type: "trade",
    narration:
      "Selling Infosys now — my thesis from 8 days ago has played out. I bought because the market underreacted to their Q3 beat. The stock is up 10.3% since then and is now fairly valued. Taking profit here before the next earnings cycle creates uncertainty.",
    decision: {
      action: "SELL",
      symbol: "INFY.NS",
      quantity: 12,
      price: 1640.5,
      confidence: 0.81,
      rationale: "Thesis played out — 10.3% gain, approaching fair value",
    },
    portfolio: {
      cash: 79108.0,
      total_value: 102350.0,
      unrealized_pnl: 2350.0,
      total_pnl_pct: 2.35,
      positions: [
        {
          symbol: "RELIANCE.NS",
          quantity: 8,
          avg_price: 2834.0,
          current_price: 2914.0,
          market_value: 23312.0,
          unrealized_pnl: 640.0,
          pnl_pct: 2.82,
          sector: "Energy",
        },
      ],
    },
  },
];
```

- [ ] **Step 2: Create `frontend/scripts/demo-server.js`**

```javascript
const { WebSocketServer } = require("ws");

const PORT = 8001;
const wss = new WebSocketServer({ port: PORT });

const messages = [
  { type: "heartbeat", timestamp: new Date().toISOString(), market_open: true },
  {
    type: "reasoning",
    text: "Scanning 14 stocks. INFY.NS RSI at 27.4 — deeply oversold. Q3 results beat estimates by 8%. Volume spike 2.3x.",
  },
  {
    type: "trade",
    narration:
      "I'm buying Infosys because their stock has dipped while the business got stronger. They just beat Q3 estimates by 8% and investors haven't caught up yet. The heavy volume today tells me other smart money is noticing too.",
    decision: { action: "BUY", symbol: "INFY.NS", quantity: 12, price: 1487.5, confidence: 0.83, rationale: "RSI oversold, Q3 beat" },
    portfolio: {
      cash: 82150, total_value: 100035, unrealized_pnl: 35, total_pnl_pct: 0.035,
      positions: [{ symbol: "INFY.NS", quantity: 12, avg_price: 1487.5, current_price: 1490.25, market_value: 17883, unrealized_pnl: 33, pnl_pct: 0.18, sector: "IT" }],
    },
  },
  { type: "heartbeat", timestamp: new Date().toISOString(), market_open: true },
  {
    type: "trade",
    narration:
      "Reliance Industries just announced their JioFiber subscriber count crossed 10 million. The stock dipped this week on market noise, not company-specific issues. I'm treating the dip as a discount.",
    decision: { action: "BUY", symbol: "RELIANCE.NS", quantity: 8, price: 2834.0, confidence: 0.77, rationale: "MACD crossover, JioFiber growth" },
    portfolio: {
      cash: 59422, total_value: 100487, unrealized_pnl: 487, total_pnl_pct: 0.487,
      positions: [
        { symbol: "INFY.NS", quantity: 12, avg_price: 1487.5, current_price: 1502, market_value: 18024, unrealized_pnl: 174, pnl_pct: 1.16, sector: "IT" },
        { symbol: "RELIANCE.NS", quantity: 8, avg_price: 2834, current_price: 2841.25, market_value: 22730, unrealized_pnl: 58, pnl_pct: 0.26, sector: "Energy" },
      ],
    },
  },
  {
    type: "trade",
    narration:
      "Selling Infosys — my thesis from 8 days ago has played out. Bought on the Q3 beat, stock is up 10.3%. Taking profit before the next earnings cycle creates uncertainty.",
    decision: { action: "SELL", symbol: "INFY.NS", quantity: 12, price: 1640.5, confidence: 0.81, rationale: "Thesis played out — 10.3% gain" },
    portfolio: {
      cash: 79108, total_value: 102350, unrealized_pnl: 2350, total_pnl_pct: 2.35,
      positions: [{ symbol: "RELIANCE.NS", quantity: 8, avg_price: 2834, current_price: 2914, market_value: 23312, unrealized_pnl: 640, pnl_pct: 2.82, sector: "Energy" }],
    },
  },
];

console.log(`Demo WS server running on ws://localhost:${PORT}`);

wss.on("connection", (ws) => {
  console.log("Client connected");
  let index = 0;

  const send = () => {
    if (index < messages.length) {
      ws.send(JSON.stringify(messages[index]));
      index++;
      setTimeout(send, index === 1 ? 500 : 4000); // first message fast, then every 4s
    } else {
      // Loop: replay heartbeats
      setTimeout(() => {
        ws.send(JSON.stringify({ type: "heartbeat", timestamp: new Date().toISOString(), market_open: true }));
        setTimeout(send.bind(null, 0), 60000); // reset after heartbeat
      }, 5000);
    }
  };

  send();
  ws.on("close", () => console.log("Client disconnected"));
});
```

- [ ] **Step 3: Test demo server**

```bash
cd frontend
node scripts/demo-server.js &
# In another terminal:
npx wscat -c ws://localhost:8001
```

Expected: receives JSON messages every few seconds, including trades with narrations.

Kill the demo server: `kill %1` or `pkill -f demo-server`

- [ ] **Step 4: Commit**

```bash
cd ..
git add frontend/lib/demo-data.ts frontend/scripts/demo-server.js
git commit -m "feat: demo mode data + mock websocket server for offline development"
```

---

### Task 3: useWebSocket hook

**Files:**
- Create: `frontend/lib/useWebSocket.ts`

- [ ] **Step 1: Create `frontend/lib/useWebSocket.ts`**

```typescript
"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { WsMessage } from "./types";

interface UseWebSocketOptions {
  url: string;
  onMessage: (msg: WsMessage) => void;
}

export function useWebSocket({ url, onMessage }: UseWebSocketOptions) {
  const [connected, setConnected] = useState(false);
  const [marketOpen, setMarketOpen] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const onMessageRef = useRef(onMessage);
  onMessageRef.current = onMessage;

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => setConnected(true);

    ws.onmessage = (event) => {
      try {
        const msg: WsMessage = JSON.parse(event.data);
        if (msg.type === "heartbeat") {
          setMarketOpen(msg.market_open);
        }
        onMessageRef.current(msg);
      } catch {
        // ignore malformed messages
      }
    };

    ws.onclose = () => {
      setConnected(false);
      reconnectTimer.current = setTimeout(connect, 3000);
    };

    ws.onerror = () => {
      ws.close();
    };
  }, [url]);

  useEffect(() => {
    connect();
    return () => {
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
    };
  }, [connect]);

  return { connected, marketOpen };
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/lib/useWebSocket.ts
git commit -m "feat: websocket hook with automatic reconnect"
```

---

### Task 4: AgentFeed component (hero component)

**Files:**
- Create: `frontend/app/components/AgentFeed.tsx`

- [ ] **Step 1: Start demo server for development**

```bash
cd frontend
node scripts/demo-server.js &
```

Set `NEXT_PUBLIC_WS_URL=ws://localhost:8001` in `.env.local` temporarily for demo mode.

- [ ] **Step 2: Create `frontend/app/components/AgentFeed.tsx`**

```typescript
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

  return <span>{displayed}<span className="animate-pulse text-phantom-purple">▍</span></span>;
}

function DecisionBadge({ decision }: { decision: TradeDecision }) {
  const colors = {
    BUY: "bg-green-900/40 text-green-400 border-green-800",
    SELL: "bg-red-900/40 text-red-400 border-red-800",
    HOLD: "bg-gray-800 text-gray-400 border-gray-700",
  };
  return (
    <div className={`inline-flex items-center gap-2 px-3 py-1 rounded-full border text-xs font-semibold mt-2 ${colors[decision.action]}`}>
      <span>{decision.action}</span>
      {decision.symbol && <span>{decision.symbol}</span>}
      {decision.quantity > 0 && <span>× {decision.quantity}</span>}
      {decision.price > 0 && <span>@ ₹{decision.price.toLocaleString("en-IN")}</span>}
      <span className="opacity-60">{(decision.confidence * 100).toFixed(0)}% confidence</span>
    </div>
  );
}

export default function AgentFeed() {
  const [entries, setEntries] = useState<FeedEntry[]>([]);
  const bottomRef = useRef<HTMLDivElement>(null);
  const wsUrl = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000/ws/feed";

  const handleMessage = useCallback((msg: WsMessage) => {
    if (msg.type === "heartbeat") return;

    setEntries((prev) => {
      const entry: FeedEntry = {
        id: `${Date.now()}-${Math.random()}`,
        type: msg.type as FeedEntry["type"],
        timestamp: new Date().toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" }),
        narration: msg.type === "trade" ? msg.narration : undefined,
        reasoning: msg.type === "reasoning" ? msg.text : undefined,
        decision: msg.type === "trade" ? msg.decision : undefined,
      };
      return [entry, ...prev].slice(0, 50); // keep last 50
    });
  }, []);

  const { connected, marketOpen } = useWebSocket({ url: wsUrl, onMessage: handleMessage });

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [entries]);

  return (
    <div className="bg-[#1a1a1e] border border-[#2a2a2e] rounded-xl p-4 flex flex-col h-full min-h-[400px]">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-sm font-semibold uppercase tracking-widest text-[#555]">Live Agent Feed</h2>
        <div className="flex items-center gap-2">
          {marketOpen && (
            <span className="text-xs text-green-400 bg-green-900/30 px-2 py-0.5 rounded-full border border-green-800">
              Market Open
            </span>
          )}
          <span className={`w-2 h-2 rounded-full ${connected ? "bg-green-400" : "bg-red-500"}`} />
          <span className="text-xs text-[#555]">{connected ? "Connected" : "Reconnecting..."}</span>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto space-y-3 pr-1">
        {entries.length === 0 && (
          <div className="flex items-center justify-center h-32 text-[#555] text-sm">
            Waiting for Phantom to speak...
          </div>
        )}
        {entries.map((entry) => (
          <div key={entry.id} className="border-l-2 border-[#2a2a2e] pl-3 py-1">
            <div className="text-xs text-[#555] mb-1">{entry.timestamp}</div>
            {entry.type === "trade" && entry.narration && (
              <>
                <p className="text-sm text-[#e8e6e1] leading-relaxed">
                  <TypewriterText text={entry.narration} />
                </p>
                {entry.decision && <DecisionBadge decision={entry.decision} />}
              </>
            )}
            {entry.type === "reasoning" && entry.reasoning && (
              <p className="text-xs text-[#666] italic leading-relaxed">{entry.reasoning}</p>
            )}
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Add to page and verify visually**

Replace `frontend/app/page.tsx` temporarily:
```typescript
import AgentFeed from "./components/AgentFeed";

export default function Home() {
  return (
    <main className="p-6 max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold text-[#a78bfa] mb-6">Phantom</h1>
      <AgentFeed />
    </main>
  );
}
```

Visit http://localhost:3000. With demo server running, you should see narration entries appearing with typewriter animation. Verify:
- Text types character by character
- BUY shows green badge, SELL shows red
- Feed scrolls as new entries arrive

- [ ] **Step 4: Commit**

```bash
cd ..
git add frontend/app/components/AgentFeed.tsx
git commit -m "feat: AgentFeed — live narration stream with typewriter animation"
```

---

### Task 5: Portfolio component

**Files:**
- Create: `frontend/app/components/Portfolio.tsx`

- [ ] **Step 1: Create `frontend/app/components/Portfolio.tsx`**

```typescript
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
      {prefix}₹{Math.abs(value).toLocaleString("en-IN", { maximumFractionDigits: 0 })}
      {pct !== undefined && (
        <span className="text-xs ml-1 opacity-70">({prefix}{pct.toFixed(2)}%)</span>
      )}
    </span>
  );
}

export default function Portfolio() {
  const [portfolio, setPortfolio] = useState<PortfolioSnapshot | null>(null);
  const wsUrl = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000/ws/feed";

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
      <h2 className="text-sm font-semibold uppercase tracking-widest text-[#555] mb-4">Portfolio</h2>

      <div className="grid grid-cols-3 gap-3 mb-4">
        <div className="bg-[#111114] rounded-lg p-3 text-center">
          <div className="text-lg font-bold text-[#c4b5fd]">
            ₹{portfolio.total_value.toLocaleString("en-IN", { maximumFractionDigits: 0 })}
          </div>
          <div className="text-xs text-[#555] mt-1">Total Value</div>
        </div>
        <div className="bg-[#111114] rounded-lg p-3 text-center">
          <div className="text-lg font-bold text-[#93c5fd]">
            ₹{portfolio.cash.toLocaleString("en-IN", { maximumFractionDigits: 0 })}
          </div>
          <div className="text-xs text-[#555] mt-1">Cash</div>
        </div>
        <div className="bg-[#111114] rounded-lg p-3 text-center">
          <div className="text-lg font-bold">
            <PnlValue value={portfolio.unrealized_pnl} pct={portfolio.total_pnl_pct} />
          </div>
          <div className="text-xs text-[#555] mt-1">Unrealized P&L</div>
        </div>
      </div>

      {portfolio.positions.length === 0 ? (
        <div className="text-[#555] text-sm text-center py-4">No open positions</div>
      ) : (
        <table className="w-full text-sm">
          <thead>
            <tr className="text-xs text-[#555] border-b border-[#2a2a2e]">
              <th className="text-left py-2">Symbol</th>
              <th className="text-right py-2">Qty</th>
              <th className="text-right py-2">Avg</th>
              <th className="text-right py-2">LTP</th>
              <th className="text-right py-2">P&L</th>
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
                <td className="py-2 text-right text-[#888]">₹{pos.avg_price.toLocaleString("en-IN")}</td>
                <td className="py-2 text-right text-[#e8e6e1]">₹{pos.current_price.toLocaleString("en-IN")}</td>
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
```

- [ ] **Step 2: Commit**

```bash
git add frontend/app/components/Portfolio.tsx
git commit -m "feat: Portfolio component — holdings table with live P&L updates"
```

---

### Task 6: TradeHistory component

**Files:**
- Create: `frontend/app/components/TradeHistory.tsx`

- [ ] **Step 1: Create `frontend/app/components/TradeHistory.tsx`**

```typescript
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
        <span className={`text-xs font-bold px-2 py-0.5 rounded ${isBuy ? "bg-green-900/40 text-green-400" : "bg-red-900/40 text-red-400"}`}>
          {trade.action}
        </span>
        <span className="font-medium text-[#e8e6e1] flex-1">{trade.symbol.replace(".NS", "")}</span>
        <span className="text-[#888] text-sm">{trade.quantity} × ₹{trade.price.toLocaleString("en-IN")}</span>
        <span className="text-[#555] text-xs">{new Date(trade.executed_at).toLocaleString("en-IN", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })}</span>
        <span className="text-[#555] text-xs">{expanded ? "▲" : "▼"}</span>
      </button>
      {expanded && (
        <div className="px-2 pb-3 space-y-2">
          {trade.narration && (
            <p className="text-sm text-[#aaa] leading-relaxed italic">"{trade.narration}"</p>
          )}
          <div className="text-xs text-[#555]">
            Confidence: {trade.confidence ? `${(trade.confidence * 100).toFixed(0)}%` : "—"}
            {trade.rationale && <> · {trade.rationale}</>}
          </div>
        </div>
      )}
    </div>
  );
}

export default function TradeHistory() {
  const [trades, setTrades] = useState<Trade[]>([]);
  const wsUrl = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000/ws/feed";

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
        <div className="text-[#555] text-sm text-center py-6">No trades yet</div>
      ) : (
        <div>{trades.map((t) => <TradeRow key={t.id} trade={t} />)}</div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/app/components/TradeHistory.tsx
git commit -m "feat: TradeHistory component — expandable trades with narration"
```

---

### Task 7: SignalBoard + MemoryViewer components

**Files:**
- Create: `frontend/app/components/SignalBoard.tsx`
- Create: `frontend/app/components/MemoryViewer.tsx`

- [ ] **Step 1: Create `frontend/app/components/SignalBoard.tsx`**

```typescript
"use client";

import { useEffect, useState } from "react";
import { fetchSignals, WATCHLIST } from "@/lib/api";
import type { TechnicalSignals } from "@/lib/types";

function RsiBar({ value, signal }: { value: number; signal: string }) {
  const color =
    signal === "oversold" ? "bg-green-500" : signal === "overbought" ? "bg-red-500" : "bg-[#555]";
  return (
    <div className="flex items-center gap-2">
      <div className="w-16 h-1.5 bg-[#2a2a2e] rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full`} style={{ width: `${value}%` }} />
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
  return <span className={`w-2 h-2 rounded-full inline-block ${colors[signal] ?? "bg-[#555]"}`} />;
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
        })
      );
      setSignals(results);
      setLoading(false);
    };
    load();
    const interval = setInterval(load, 15 * 60 * 1000); // refresh every 15min
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="bg-[#1a1a1e] border border-[#2a2a2e] rounded-xl p-4">
      <h2 className="text-sm font-semibold uppercase tracking-widest text-[#555] mb-4">Signal Board</h2>
      {loading ? (
        <div className="text-[#555] text-sm text-center py-6">Loading signals...</div>
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
                  <td className="py-2 font-medium text-[#e8e6e1]">{sym.replace(".NS", "")}</td>
                  <td className="py-2 text-right text-[#888]">₹{sig.current_price.toLocaleString("en-IN")}</td>
                  <td className="py-2 flex justify-end">
                    <RsiBar value={sig.rsi_value} signal={sig.rsi_signal} />
                  </td>
                  <td className="py-2 text-center">
                    <MacdDot signal={sig.macd_signal} />
                  </td>
                  <td className="py-2 text-center text-xs">
                    {sig.volume_signal === "spike" ? (
                      <span className="text-yellow-400">⚡ {sig.volume_ratio.toFixed(1)}x</span>
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
```

- [ ] **Step 2: Create `frontend/app/components/MemoryViewer.tsx`**

```typescript
"use client";

import { useEffect, useState } from "react";
import { fetchMemories } from "@/lib/api";
import type { TradeMemory } from "@/lib/types";

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    active: "bg-blue-900/40 text-blue-400 border-blue-800",
    played_out: "bg-green-900/40 text-green-400 border-green-800",
    invalidated: "bg-red-900/40 text-red-400 border-red-800",
  };
  return (
    <span className={`text-xs px-2 py-0.5 rounded-full border ${styles[status] ?? styles.active}`}>
      {status.replace("_", " ")}
    </span>
  );
}

export default function MemoryViewer() {
  const [memories, setMemories] = useState<TradeMemory[]>([]);

  useEffect(() => {
    fetchMemories().then(setMemories).catch(console.error);
  }, []);

  const active = memories.filter((m) => m.thesis_status === "active");
  const past = memories.filter((m) => m.thesis_status !== "active");

  return (
    <div className="bg-[#1a1a1e] border border-[#2a2a2e] rounded-xl p-4">
      <h2 className="text-sm font-semibold uppercase tracking-widest text-[#555] mb-4">Agent Memory</h2>

      {memories.length === 0 ? (
        <div className="text-[#555] text-sm text-center py-6">No stored theses yet</div>
      ) : (
        <div className="space-y-3">
          {[...active, ...past].map((m) => (
            <div key={m.id} className="bg-[#111114] border border-[#2a2a2e] rounded-lg p-3">
              <div className="flex items-center justify-between mb-2">
                <span className="font-medium text-[#e8e6e1]">{m.stock.replace(".NS", "")}</span>
                <StatusBadge status={m.thesis_status} />
              </div>
              <p className="text-xs text-[#888] leading-relaxed italic mb-2">"{m.thesis}"</p>
              <div className="flex gap-4 text-xs text-[#555]">
                <span>Entry ₹{m.price.toLocaleString("en-IN")}</span>
                <span className="text-green-600">Target ₹{m.target_price.toLocaleString("en-IN")}</span>
                <span className="text-red-600">Stop ₹{m.stop_loss.toLocaleString("en-IN")}</span>
              </div>
              <div className="text-xs text-[#444] mt-1">
                {new Date(m.timestamp).toLocaleDateString("en-IN", { day: "numeric", month: "short" })}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/app/components/SignalBoard.tsx frontend/app/components/MemoryViewer.tsx
git commit -m "feat: SignalBoard RSI/MACD grid + MemoryViewer agent theses"
```

---

### Task 8: PerfChart component

**Files:**
- Create: `frontend/app/components/PerfChart.tsx`

- [ ] **Step 1: Create `frontend/app/components/PerfChart.tsx`**

```typescript
"use client";

import { useCallback, useEffect, useState } from "react";
import { LineChart, Line, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer } from "recharts";
import { useWebSocket } from "@/lib/useWebSocket";
import type { WsMessage } from "@/lib/types";

interface DataPoint {
  time: string;
  portfolio: number;
}

const INITIAL_VALUE = 100000;

function CustomTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-[#1a1a1e] border border-[#2a2a2e] rounded-lg p-2 text-xs">
      <div className="text-[#555] mb-1">{label}</div>
      {payload.map((p: any) => (
        <div key={p.name} style={{ color: p.color }}>
          {p.name}: ₹{Number(p.value).toLocaleString("en-IN", { maximumFractionDigits: 0 })}
        </div>
      ))}
    </div>
  );
}

export default function PerfChart() {
  const [data, setData] = useState<DataPoint[]>([
    { time: "Start", portfolio: INITIAL_VALUE },
  ]);
  const wsUrl = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000/ws/feed";

  const handleMessage = useCallback((msg: WsMessage) => {
    if (msg.type === "trade" || msg.type === "portfolio_update") {
      const time = new Date().toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" });
      setData((prev) => [
        ...prev,
        { time, portfolio: msg.portfolio.total_value },
      ].slice(-50));
    }
  }, []);

  useWebSocket({ url: wsUrl, onMessage: handleMessage });

  const pnl = data[data.length - 1].portfolio - INITIAL_VALUE;
  const pnlPct = (pnl / INITIAL_VALUE) * 100;
  const positive = pnl >= 0;

  return (
    <div className="bg-[#1a1a1e] border border-[#2a2a2e] rounded-xl p-4">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-sm font-semibold uppercase tracking-widest text-[#555]">Performance</h2>
        <div className={`text-sm font-semibold ${positive ? "text-green-400" : "text-red-400"}`}>
          {positive ? "+" : ""}₹{Math.abs(pnl).toLocaleString("en-IN", { maximumFractionDigits: 0 })}
          <span className="text-xs ml-1 opacity-70">({positive ? "+" : ""}{pnlPct.toFixed(2)}%)</span>
        </div>
      </div>
      <ResponsiveContainer width="100%" height={180}>
        <LineChart data={data} margin={{ top: 5, right: 5, left: 0, bottom: 5 }}>
          <XAxis dataKey="time" tick={{ fill: "#555", fontSize: 10 }} axisLine={false} tickLine={false} />
          <YAxis
            tick={{ fill: "#555", fontSize: 10 }}
            axisLine={false}
            tickLine={false}
            tickFormatter={(v) => `₹${(v / 1000).toFixed(0)}k`}
            domain={["auto", "auto"]}
          />
          <Tooltip content={<CustomTooltip />} />
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
```

- [ ] **Step 2: Commit**

```bash
git add frontend/app/components/PerfChart.tsx
git commit -m "feat: PerfChart — portfolio value over time with recharts"
```

---

### Task 9: Main dashboard page

**Files:**
- Modify: `frontend/app/page.tsx`

- [ ] **Step 1: Build the full dashboard layout**

Replace `frontend/app/page.tsx`:
```typescript
import AgentFeed from "./components/AgentFeed";
import MemoryViewer from "./components/MemoryViewer";
import PerfChart from "./components/PerfChart";
import Portfolio from "./components/Portfolio";
import SignalBoard from "./components/SignalBoard";
import TradeHistory from "./components/TradeHistory";

export default function Home() {
  return (
    <main className="min-h-screen bg-[#0d0d0f] p-4 md:p-6">
      <header className="mb-6">
        <h1 className="text-3xl font-bold bg-gradient-to-r from-[#a78bfa] to-[#60a5fa] bg-clip-text text-transparent">
          Phantom
        </h1>
        <p className="text-[#555] text-sm italic mt-1">"A portfolio that thinks for itself."</p>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Left column — hero feed */}
        <div className="lg:col-span-2 flex flex-col gap-4">
          <AgentFeed />
          <PerfChart />
          <TradeHistory />
        </div>

        {/* Right column — data panels */}
        <div className="flex flex-col gap-4">
          <Portfolio />
          <MemoryViewer />
          <SignalBoard />
        </div>
      </div>
    </main>
  );
}
```

- [ ] **Step 2: Visual verification with demo server**

Make sure demo server is running on port 8001 and `.env.local` points to it:
```bash
# .env.local
NEXT_PUBLIC_WS_URL=ws://localhost:8001
NEXT_PUBLIC_API_URL=http://localhost:8000
```

```bash
cd frontend && npm run dev
```

Open http://localhost:3000. Verify:
- Page loads without console errors
- Agent feed shows narrations with typewriter effect
- Portfolio updates when trades come in
- Trade history populates
- Performance chart draws a line as portfolio value changes
- Layout is readable on both desktop and mobile (resize browser)

- [ ] **Step 3: Commit**

```bash
cd ..
git add frontend/app/page.tsx
git commit -m "feat: main dashboard — 3-column layout with all 6 components"
```

---

### Task 10: Wire live WebSocket

**Files:**
- Modify: `frontend/.env.local`

- [ ] **Step 1: Stop demo server**

```bash
pkill -f demo-server.js
```

- [ ] **Step 2: Point to live backend**

Update `frontend/.env.local`:
```bash
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws/feed
NEXT_PUBLIC_API_URL=http://localhost:8000
```

- [ ] **Step 3: Verify backend is running**

```bash
docker compose ps
curl http://localhost:8000/health
curl http://localhost:8000/portfolio
```

- [ ] **Step 4: Open dashboard and verify live connection**

```bash
cd frontend && npm run dev
```

Open http://localhost:3000. Verify:
- Green connection dot appears
- Heartbeat received (check browser console: no WS errors)
- Portfolio loads real data from `/portfolio` endpoint
- Trades load from `/portfolio/trades`
- Signal board attempts to load signals (may fail outside market hours — that's OK)

- [ ] **Step 5: Smoke test full agent cycle**

Trigger one agent cycle manually (Docker container):
```bash
docker compose exec api python -c "
from unittest.mock import patch
from app.scheduler.scheduler import run_agent_cycle
with patch('app.data.fetcher.is_market_open', return_value=True):
    run_agent_cycle()
"
```

Watch the dashboard — within 30 seconds you should see:
- Narration appears in AgentFeed with typewriter effect
- Portfolio updates (if a trade was executed)
- Trade appears in TradeHistory

- [ ] **Step 6: Final commit**

```bash
git add frontend/.env.local
git commit -m "feat: wire live websocket — dashboard connected to backend feed"
```

---

### Week 3 Verification

```bash
# Backend healthy
curl http://localhost:8000/health

# All REST endpoints return JSON
curl http://localhost:8000/portfolio
curl http://localhost:8000/portfolio/trades
curl http://localhost:8000/memories

# Frontend builds without errors
cd frontend && npm run build
```

Expected: `npm run build` completes with no TypeScript or lint errors.

Manual check:
1. Start demo server, open dashboard — typewriter animation works, portfolio updates on trade messages
2. Switch to live backend — connection indicator shows green, REST data loads
3. Trigger one agent cycle manually — decision appears in dashboard in real time

Phantom is complete.
