"use client";

import { useState } from "react";

interface Props {
  onSubmit: (youtubeUrl: string, instagramUrl: string) => void;
  loading: boolean;
}

export default function UrlInput({ onSubmit, loading }: Props) {
  const [youtubeUrl, setYoutubeUrl] = useState("");
  const [instagramUrl, setInstagramUrl] = useState("");

  function handleSubmit() {
    if (!youtubeUrl.trim() || !instagramUrl.trim()) return;
    onSubmit(youtubeUrl.trim(), instagramUrl.trim());
  }

  return (
    <div className="bg-surface-raised border border-surface-border rounded-lg p-5 flex flex-col gap-4">
      <h2 className="font-mono text-sm text-zinc-400 uppercase tracking-widest">
        Content Sources
      </h2>

      <div className="flex flex-col gap-3">
        <div className="flex flex-col gap-1">
          <label className="text-xs font-mono text-zinc-500">YouTube URL</label>
          <input
            type="url"
            placeholder="https://www.youtube.com/watch?v=..."
            value={youtubeUrl}
            onChange={(e) => setYoutubeUrl(e.target.value)}
            className="bg-surface border border-surface-border rounded px-3 py-2 text-sm font-mono
                       text-white placeholder-zinc-600 focus:outline-none focus:border-accent
                       transition-colors"
          />
        </div>

        <div className="flex flex-col gap-1">
          <label className="text-xs font-mono text-zinc-500">Instagram Reel URL</label>
          <input
            type="url"
            placeholder="https://www.instagram.com/reel/..."
            value={instagramUrl}
            onChange={(e) => setInstagramUrl(e.target.value)}
            className="bg-surface border border-surface-border rounded px-3 py-2 text-sm font-mono
                       text-white placeholder-zinc-600 focus:outline-none focus:border-accent
                       transition-colors"
          />
        </div>
      </div>

      <button
        onClick={handleSubmit}
        disabled={loading || !youtubeUrl.trim() || !instagramUrl.trim()}
        className="bg-accent text-black font-mono font-bold text-sm px-5 py-2 rounded
                   hover:bg-accent-dim transition-colors disabled:opacity-40 disabled:cursor-not-allowed
                   self-end"
      >
        {loading ? "Processing..." : "Analyze"}
      </button>
    </div>
  );
}
