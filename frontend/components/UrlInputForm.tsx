"use client";

import { useState } from "react";

interface Props {
  onSubmit: (youtubeUrl: string, instagramUrl: string) => void;
  loading: boolean;
}

export default function UrlInputForm({ onSubmit, loading }: Props) {
  const [youtubeUrl, setYoutubeUrl] = useState("");
  const [instagramUrl, setInstagramUrl] = useState("");
  const [fieldErrors, setFieldErrors] = useState<{
    youtube?: string;
    instagram?: string;
  }>({});

  function validate(): boolean {
    const errors: { youtube?: string; instagram?: string } = {};
    if (!youtubeUrl.trim()) {
      errors.youtube = "YouTube URL is required";
    } else if (
      !youtubeUrl.includes("youtube.com") &&
      !youtubeUrl.includes("youtu.be")
    ) {
      errors.youtube = "Must be a YouTube URL";
    }
    if (!instagramUrl.trim()) {
      errors.instagram = "Instagram URL is required";
    } else if (!instagramUrl.includes("instagram.com")) {
      errors.instagram = "Must be an Instagram URL";
    }
    setFieldErrors(errors);
    return Object.keys(errors).length === 0;
  }

  function handleSubmit() {
    if (!validate() || loading) return;
    onSubmit(youtubeUrl.trim(), instagramUrl.trim());
  }

  const canSubmit =
    !loading && youtubeUrl.trim().length > 0 && instagramUrl.trim().length > 0;

  return (
    <div className="bg-surface-card border border-surface-border rounded-xl p-5 flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-zinc-300 uppercase tracking-widest font-mono">
          Content Sources
        </h2>
        {loading && (
          <span className="text-xs text-accent font-mono animate-pulse">
            Analyzing...
          </span>
        )}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div className="flex flex-col gap-1">
          <label className="text-xs font-mono text-zinc-500">
            YouTube URL
          </label>
          <input
            type="url"
            placeholder="https://www.youtube.com/watch?v=..."
            value={youtubeUrl}
            onChange={(e) => {
              setYoutubeUrl(e.target.value);
              if (fieldErrors.youtube)
                setFieldErrors((p) => ({ ...p, youtube: undefined }));
            }}
            onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
            disabled={loading}
            className={`bg-surface border rounded px-3 py-2 text-sm font-mono text-white
              placeholder-zinc-600 focus:outline-none transition-colors disabled:opacity-40
              ${fieldErrors.youtube
                ? "border-red-500 focus:border-red-400"
                : "border-surface-border focus:border-accent"
              }`}
          />
          {fieldErrors.youtube && (
            <span className="text-xs text-red-400 font-mono">
              {fieldErrors.youtube}
            </span>
          )}
        </div>

        <div className="flex flex-col gap-1">
          <label className="text-xs font-mono text-zinc-500">
            Instagram Reel URL
          </label>
          <input
            type="url"
            placeholder="https://www.instagram.com/reel/..."
            value={instagramUrl}
            onChange={(e) => {
              setInstagramUrl(e.target.value);
              if (fieldErrors.instagram)
                setFieldErrors((p) => ({ ...p, instagram: undefined }));
            }}
            onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
            disabled={loading}
            className={`bg-surface border rounded px-3 py-2 text-sm font-mono text-white
              placeholder-zinc-600 focus:outline-none transition-colors disabled:opacity-40
              ${fieldErrors.instagram
                ? "border-red-500 focus:border-red-400"
                : "border-surface-border focus:border-accent"
              }`}
          />
          {fieldErrors.instagram && (
            <span className="text-xs text-red-400 font-mono">
              {fieldErrors.instagram}
            </span>
          )}
        </div>
      </div>

      <div className="flex justify-end">
        <button
          onClick={handleSubmit}
          disabled={!canSubmit}
          className="hover-lift btn-bounce bg-accent text-black font-mono font-semibold
            text-sm px-6 py-2 rounded-lg disabled:opacity-40 disabled:cursor-not-allowed
            disabled:transform-none disabled:shadow-none"
        >
          {loading ? (
            <span className="flex items-center gap-2">
              <span className="w-3.5 h-3.5 border-2 border-black/30 border-t-black rounded-full animate-spin" />
              Analyzing
            </span>
          ) : (
            "Analyze"
          )}
        </button>
      </div>
    </div>
  );
}
