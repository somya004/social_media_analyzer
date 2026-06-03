"use client";

import { useState } from "react";
import type { AnalyzeYouTubeResponse, AnalyzeInstagramResponse } from "@/lib/api";

type CardData = AnalyzeYouTubeResponse | AnalyzeInstagramResponse;

function fmt(n: number | null | undefined): string {
  if (n == null) return "—";
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return n.toLocaleString();
}

function fmtDuration(s: number | null): string {
  if (s == null) return "—";
  const m = Math.floor(s / 60);
  const sec = s % 60;
  return `${m}:${String(sec).padStart(2, "0")}`;
}

function StatPill({ icon, label, value }: { icon: string; label: string; value: string }) {
  return (
    <div className="flex flex-col items-center gap-0.5 bg-white/5 rounded-xl px-3 py-2.5 min-w-0">
      <span className="text-base leading-none">{icon}</span>
      <span className="text-sm font-semibold text-white">{value}</span>
      <span className="text-[10px] text-zinc-500 uppercase tracking-wide">{label}</span>
    </div>
  );
}

function HashtagRow({ tags }: { tags: string[] }) {
  const [open, setOpen] = useState(false);
  const show = open ? tags : tags.slice(0, 5);
  if (!tags.length) return null;
  return (
    <div className="flex flex-wrap gap-1.5">
      {show.map((t) => (
        <span key={t} className="text-[11px] font-mono px-2 py-0.5 rounded-full bg-white/5 text-zinc-400 border border-white/8">
          {t}
        </span>
      ))}
      {!open && tags.length > 5 && (
        <button onClick={() => setOpen(true)} className="text-[11px] font-mono text-zinc-500 hover:text-zinc-300 transition-colors px-2 py-0.5">
          +{tags.length - 5}
        </button>
      )}
    </div>
  );
}

const STYLE = {
  youtube: {
    border: "border-red-500/20",
    bg: "from-red-950/30 to-transparent",
    badge: "bg-red-500/15 text-red-400 border-red-500/25",
    dot: "bg-red-400",
    label: "text-yt",
    ring: "shadow-red-900/20",
  },
  instagram: {
    border: "border-purple-500/20",
    bg: "from-purple-950/30 to-transparent",
    badge: "bg-purple-500/15 text-purple-400 border-purple-500/25",
    dot: "bg-purple-400",
    label: "text-ig",
    ring: "shadow-purple-900/20",
  },
};

export default function VideoCard({ data }: { data: CardData }) {
  const s = STYLE[data.source];
  const yt = data.source === "youtube" ? (data as AnalyzeYouTubeResponse) : null;
  const ig = data.source === "instagram" ? (data as AnalyzeInstagramResponse) : null;

  const title = yt?.title ?? ig?.shortcode ?? "Untitled";
  const creator = yt?.creator ?? ig?.creator ?? null;

  return (
    <div className={`card-hover glass rounded-2xl overflow-hidden border ${s.border} shadow-lg ${s.ring} animate-scale-in`}>
      {/* Gradient top strip */}
      <div className={`h-1 w-full bg-gradient-to-r ${s.bg.replace("from-", "from-").replace("to-transparent", "to-transparent")} 
        ${data.source === "youtube" ? "bg-gradient-to-r from-red-500 to-red-700" : "bg-gradient-to-r from-purple-500 to-fuchsia-600"}`} />

      <div className="p-4 flex flex-col gap-4">
        {/* Title row */}
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <span className={`text-[10px] font-mono font-bold uppercase tracking-widest ${s.label}`}>
              {data.source} · Video {data.video_id}
            </span>
            <h3 className="text-sm font-semibold text-white leading-snug mt-0.5 line-clamp-2">
              {title}
            </h3>
            {creator && <p className="text-xs text-zinc-500 mt-0.5">@{creator}</p>}
          </div>
          <span className={`shrink-0 text-[10px] font-mono font-bold border rounded-lg px-2 py-1 ${s.badge}`}>
            {data.video_id}
          </span>
        </div>

        {/* Stats grid */}
        <div className="grid grid-cols-3 gap-2">
          <StatPill icon="👁" label="Views" value={fmt(data.views)} />
          <StatPill icon="❤️" label="Likes" value={fmt(data.likes)} />
          {ig ? (
            <StatPill icon="💬" label="Comments" value={fmt(ig.comments)} />
          ) : (
            <StatPill icon="⏱" label="Duration" value={fmtDuration(data.duration)} />
          )}
        </div>

        {/* Secondary stats */}
        <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-zinc-500 font-mono">
          {ig?.engagement_rate != null && (
            <span className="text-emerald-400">⚡ {ig.engagement_rate.toFixed(2)}% engagement</span>
          )}
          {ig?.followers != null && <span>{fmt(ig.followers)} followers</span>}
          {data.upload_date && <span>📅 {data.upload_date.slice(0, 10)}</span>}
          {data.source === "youtube" && data.duration != null && (
            <span>⏱ {fmtDuration(data.duration)}</span>
          )}
        </div>

        {/* Indexed indicator */}
        <div className="flex items-center gap-1.5 text-[11px] font-mono text-zinc-500">
          <span className={`w-1.5 h-1.5 rounded-full ${s.dot}`} />
          {data.chunks_stored} chunks indexed
        </div>

        {/* Hashtags */}
        <HashtagRow tags={data.hashtags} />
      </div>
    </div>
  );
}
