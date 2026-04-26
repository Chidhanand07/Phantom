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

export type WsMessage =
  | { type: "trade"; narration: string; decision: TradeDecision; portfolio: PortfolioSnapshot }
  | { type: "reasoning"; text: string }
  | { type: "heartbeat"; timestamp: string; market_open: boolean }
  | { type: "portfolio_update"; portfolio: PortfolioSnapshot };
