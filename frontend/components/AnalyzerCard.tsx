"use client";

import { useState } from "react";
import type { AnalyzeYouTubeResponse, AnalyzeInstagramResponse } from "@/lib/api";

type Platform = "youtube" | "instagram";
type Status = "idle" | "loading" | "done" | "error";

interface Props {
  platform: Platform;
  onResult: (data: AnalyzeYouTubeResponse | AnalyzeInstagramResponse) => void;
  onAnalyze: (url: string) => Promise<AnalyzeYouTubeResponse | AnalyzeInstagramResponse>;
}

const CONFIG = {
  youtube: {
    label: "YouTube",
    placeholder: "https://www.youtube.com/watch?v=...",
    icon: (
      <svg viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5">
        <path d="M23.5 6.19a3.02 3.02 0 00-2.12-2.14C19.54 3.5 12 3.5 12 3.5s-7.54 0-9.38.55A3.02 3.02 0 00.5 6.19C0 8.04 0 12 0 12s0 3.96.5 5.81a3.02 3.02 0 002.12 2.14C4.46 20.5 12 20.5 12 20.5s7.54 0 9.38-.55a3.02 3.02 0 002.12-2.14C24 15.96 24 12 24 12s0-3.96-.5-5.81zM9.75 15.5v-7l6.5 3.5-6.5 3.5z"/>
      </svg>
    ),
    gradientClass: "yt-gradient yt-glow",
    labelClass: "text-yt",
    ringClass: "focus:border-red-500/60",
    btnClass: "from-red-600 to-red-500 hover:from-red-500 hover:to-red-400 shadow-red-900/40",
    badgeClass: "bg-red-500/15 text-red-400 border border-red-500/25",
    validate: (url: string) =>
      url.includes("youtube.com") || url.includes("youtu.be")
        ? null
        : "Must be a YouTube URL",
  },
  instagram: {
    label: "Instagram",
    placeholder: "https://www.instagram.com/reel/...",
    icon: (
      <svg viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5">
        <path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zM12 0C8.741 0 8.333.014 7.053.072 2.695.272.273 2.69.073 7.052.014 8.333 0 8.741 0 12c0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98C8.333 23.986 8.741 24 12 24c3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98C15.668.014 15.259 0 12 0zm0 5.838a6.162 6.162 0 100 12.324 6.162 6.162 0 000-12.324zM12 16a4 4 0 110-8 4 4 0 010 8zm6.406-11.845a1.44 1.44 0 100 2.881 1.44 1.44 0 000-2.881z"/>
      </svg>
    ),
    gradientClass: "ig-gradient ig-glow",
    labelClass: "text-ig",
    ringClass: "focus:border-purple-500/60",
    btnClass: "from-purple-600 to-fuchsia-600 hover:from-purple-500 hover:to-fuchsia-500 shadow-purple-900/40",
    badgeClass: "bg-purple-500/15 text-purple-400 border border-purple-500/25",
    validate: (url: string) =>
      url.includes("instagram.com") ? null : "Must be an Instagram URL",
  },
};

export default function AnalyzerCard({ platform, onResult, onAnalyze }: Props) {
  const [url, setUrl] = useState("");
  const [status, setStatus] = useState<Status>("idle");
  const [error, setError] = useState<string | null>(null);
  const cfg = CONFIG[platform];

  async function handleAnalyze() {
    const trimmed = url.trim();
    if (!trimmed) { setError("URL is required"); return; }
    const validationError = cfg.validate(trimmed);
    if (validationError) { setError(validationError); return; }

    setStatus("loading");
    setError(null);
    try {
      const result = await onAnalyze(trimmed);
      onResult(result);
      setStatus("done");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Analysis failed");
      setStatus("error");
    }
  }

  return (
    <div className={`card-hover glass rounded-2xl p-5 flex flex-col gap-4 border transition-all duration-300 ${cfg.gradientClass}`}>
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className={`p-2 rounded-xl ${cfg.badgeClass}`}>
          <span className={cfg.labelClass}>{cfg.icon}</span>
        </div>
        <div>
          <h3 className={`font-semibold text-sm ${cfg.labelClass}`}>{cfg.label}</h3>
          <p className="text-xs text-zinc-500">Analyze a {cfg.label} video</p>
        </div>
        {status === "done" && (
          <div className="ml-auto flex items-center gap-1.5 text-xs text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 rounded-full px-3 py-1 animate-fade-in">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
            Indexed
          </div>
        )}
      </div>

      {/* Input */}
      <div className="flex flex-col gap-1.5">
        <input
          type="url"
          placeholder={cfg.placeholder}
          value={url}
          onChange={(e) => { setUrl(e.target.value); setError(null); }}
          onKeyDown={(e) => e.key === "Enter" && handleAnalyze()}
          disabled={status === "loading"}
          className={`w-full bg-black/30 border rounded-xl px-4 py-2.5 text-sm font-mono
            text-white placeholder-zinc-600 outline-none transition-all duration-200
            disabled:opacity-50 border-white/10 ${cfg.ringClass}
            ${error ? "border-red-500/60" : ""}`}
        />
        {error && (
          <p className="text-xs text-red-400 font-mono pl-1 animate-fade-in">{error}</p>
        )}
      </div>

      {/* Button */}
      <button
        onClick={handleAnalyze}
        disabled={status === "loading" || !url.trim()}
        className={`btn-spring w-full bg-gradient-to-r ${cfg.btnClass} text-white font-semibold
          text-sm py-2.5 rounded-xl shadow-lg disabled:opacity-40 disabled:cursor-not-allowed
          disabled:transform-none transition-all duration-200`}
      >
        {status === "loading" ? (
          <span className="flex items-center justify-center gap-2">
            <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            Analyzing...
          </span>
        ) : (
          `Analyze ${cfg.label}`
        )}
      </button>
    </div>
  );
}
