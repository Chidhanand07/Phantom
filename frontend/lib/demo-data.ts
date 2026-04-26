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
