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
    <span
      className={`text-xs px-2 py-0.5 rounded-full border ${styles[status] ?? styles.active}`}
    >
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
      <h2 className="text-sm font-semibold uppercase tracking-widest text-[#555] mb-4">
        Agent Memory
      </h2>

      {memories.length === 0 ? (
        <div className="text-[#555] text-sm text-center py-6">
          No stored theses yet
        </div>
      ) : (
        <div className="space-y-3">
          {[...active, ...past].map((m) => (
            <div
              key={m.id}
              className="bg-[#111114] border border-[#2a2a2e] rounded-lg p-3"
            >
              <div className="flex items-center justify-between mb-2">
                <span className="font-medium text-[#e8e6e1]">
                  {m.stock.replace(".NS", "")}
                </span>
                <StatusBadge status={m.thesis_status} />
              </div>
              <p className="text-xs text-[#888] leading-relaxed italic mb-2">
                &ldquo;{m.thesis}&rdquo;
              </p>
              <div className="flex gap-4 text-xs text-[#555]">
                <span>Entry ₹{m.price.toLocaleString("en-IN")}</span>
                <span className="text-green-600">
                  Target ₹{m.target_price.toLocaleString("en-IN")}
                </span>
                <span className="text-red-600">
                  Stop ₹{m.stop_loss.toLocaleString("en-IN")}
                </span>
              </div>
              <div className="text-xs text-[#444] mt-1">
                {new Date(m.timestamp).toLocaleDateString("en-IN", {
                  day: "numeric",
                  month: "short",
                })}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
