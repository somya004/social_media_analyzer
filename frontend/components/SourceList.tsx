"use client";

import { useState } from "react";
import type { SourceCitation } from "@/lib/api";

const STYLE: Record<string, { bg: string; text: string; border: string; label: string }> = {
  youtube: { bg: "bg-red-500/10", text: "text-red-400", border: "border-red-500/20", label: "YT" },
  instagram: { bg: "bg-purple-500/10", text: "text-purple-400", border: "border-purple-500/20", label: "IG" },
};
const FALLBACK = { bg: "bg-zinc-500/10", text: "text-zinc-400", border: "border-zinc-500/20", label: "?" };

export default function SourceList({ sources }: { sources: SourceCitation[] }) {
  const [expanded, setExpanded] = useState<number | null>(null);
  if (!sources.length) return null;

  return (
    <div className="flex flex-col gap-1.5 mt-2">
      <p className="text-[10px] font-mono text-zinc-600 uppercase tracking-wider px-0.5">
        {sources.length} source{sources.length !== 1 ? "s" : ""}
      </p>
      {sources.map((src, i) => {
        const st = STYLE[src.source] ?? FALLBACK;
        const open = expanded === i;
        return (
          <button
            key={src.chunk_id}
            onClick={() => setExpanded(open ? null : i)}
            className={`text-left w-full rounded-xl border px-3 py-2 transition-all duration-200
              hover:brightness-125 ${st.bg} ${st.border}`}
          >
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-2 min-w-0">
                <span className={`text-[10px] font-mono font-bold px-1.5 py-0.5 rounded ${st.bg} ${st.text} border ${st.border} shrink-0`}>
                  {st.label}
                </span>
                <span className="text-[11px] font-mono text-zinc-400 truncate">
                  {src.title || src.video_id}
                </span>
              </div>
              <div className="flex items-center gap-1.5 shrink-0">
                <div className="flex gap-0.5">
                  {[1,2,3,4,5].map(n => (
                    <span key={n} className={`w-1 h-2 rounded-full ${n <= Math.round(src.score * 5) ? st.text.replace("text-", "bg-") : "bg-zinc-700"}`} />
                  ))}
                </div>
                <span className="text-[10px] text-zinc-600">{open ? "▲" : "▼"}</span>
              </div>
            </div>
            {open && (
              <p className={`mt-2 text-xs font-mono leading-relaxed border-t pt-2 ${st.text} ${st.border} opacity-80 animate-fade-up`}>
                {src.evidence}
              </p>
            )}
          </button>
        );
      })}
    </div>
  );
}
