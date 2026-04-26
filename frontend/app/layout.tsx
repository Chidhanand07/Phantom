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
