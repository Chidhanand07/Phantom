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
