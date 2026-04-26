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
