const { WebSocketServer } = require("ws");

const PORT = 9001;
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
      setTimeout(send, index === 1 ? 500 : 4000);
    } else {
      setTimeout(() => {
        ws.send(JSON.stringify({ type: "heartbeat", timestamp: new Date().toISOString(), market_open: true }));
      }, 5000);
    }
  };

  send();
  ws.on("close", () => console.log("Client disconnected"));
});
