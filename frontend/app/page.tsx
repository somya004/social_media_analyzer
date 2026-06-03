"use client";

import { useState, useCallback } from "react";
import AnalyzerCard from "@/components/AnalyzerCard";
import VideoCard from "@/components/VideoCard";
import ChatPanel from "@/components/ChatPanel";
import LoadingState from "@/components/LoadingState";
import { analyzeYouTube, analyzeInstagram } from "@/lib/api";
import type { AnalyzeYouTubeResponse, AnalyzeInstagramResponse } from "@/lib/api";

type VideoState<T> = { status: "idle" } | { status: "loading" } | { status: "done"; data: T } | { status: "error"; message: string };

export default function Home() {
  const [ytState, setYtState] = useState<VideoState<AnalyzeYouTubeResponse>>({ status: "idle" });
  const [igState, setIgState] = useState<VideoState<AnalyzeInstagramResponse>>({ status: "idle" });
  const [sessionId, setSessionId] = useState<string | null>(null);

  const handleSessionId = useCallback((id: string) => {
    setSessionId(prev => prev ?? id);
  }, []);

  const bothDone =
    ytState.status === "done" || igState.status === "done";

  return (
    <div className="flex flex-col h-screen overflow-hidden dot-bg">
      {/* Header */}
      <header className="shrink-0 border-b border-white/6 bg-black/40 backdrop-blur px-6 py-3 flex items-center gap-4 z-10">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shadow-lg shadow-indigo-900/40">
            <span className="text-white text-xs font-bold">M</span>
          </div>
          <span className="font-bold text-white tracking-tight">MediaRAG</span>
        </div>
        <span className="text-xs text-zinc-600 font-mono hidden sm:block">/ social content analyst</span>
        <div className="ml-auto flex items-center gap-2">
          {ytState.status === "done" && (
            <span className="text-[10px] font-mono bg-red-500/10 text-red-400 border border-red-500/20 rounded-full px-3 py-1 animate-fade-in">
              YT indexed
            </span>
          )}
          {igState.status === "done" && (
            <span className="text-[10px] font-mono bg-purple-500/10 text-purple-400 border border-purple-500/20 rounded-full px-3 py-1 animate-fade-in">
              IG indexed
            </span>
          )}
        </div>
      </header>

      {/* Main split */}
      <div className="flex-1 flex overflow-hidden min-h-0">
        {/* Left — analysis */}
        <div className="flex flex-col gap-5 overflow-y-auto p-5 w-full lg:w-[60%] lg:border-r lg:border-white/5">

          {/* Analyzer cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <AnalyzerCard
              platform="youtube"
              onAnalyze={async (url) => {
                setYtState({ status: "loading" });
                try {
                  const data = await analyzeYouTube(url);
                  setYtState({ status: "done", data });
                  return data;
                } catch (err) {
                  const msg = err instanceof Error ? err.message : "Failed";
                  setYtState({ status: "error", message: msg });
                  throw err;
                }
              }}
              onResult={() => {}}
            />
            <AnalyzerCard
              platform="instagram"
              onAnalyze={async (url) => {
                setIgState({ status: "loading" });
                try {
                  const data = await analyzeInstagram(url);
                  setIgState({ status: "done", data });
                  return data;
                } catch (err) {
                  const msg = err instanceof Error ? err.message : "Failed";
                  setIgState({ status: "error", message: msg });
                  throw err;
                }
              }}
              onResult={() => {}}
            />
          </div>

          {/* Loading states */}
          {(ytState.status === "loading" || igState.status === "loading") && (
            <LoadingState message="Extracting transcript, building embeddings, indexing vectors..." />
          )}

          {/* Error banners */}
          {ytState.status === "error" && (
            <div className="bg-red-950/30 border border-red-500/20 rounded-xl px-4 py-3 animate-fade-in">
              <p className="text-xs font-mono text-red-400">YouTube: {ytState.message}</p>
            </div>
          )}
          {igState.status === "error" && (
            <div className="bg-purple-950/30 border border-purple-500/20 rounded-xl px-4 py-3 animate-fade-in">
              <p className="text-xs font-mono text-purple-400">Instagram: {igState.message}</p>
            </div>
          )}

          {/* Result cards */}
          {(ytState.status === "done" || igState.status === "done") && (
            <div className="flex flex-col gap-3">
              <div className="flex items-center gap-2">
                <div className="h-px flex-1 bg-white/5" />
                <span className="text-[10px] font-mono text-zinc-600 uppercase tracking-widest px-2">
                  Analysis Results
                </span>
                <div className="h-px flex-1 bg-white/5" />
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {ytState.status === "done" && <VideoCard data={ytState.data} />}
                {igState.status === "done" && <VideoCard data={igState.data} />}
              </div>
            </div>
          )}

          {/* Mobile chat */}
          <div className="lg:hidden flex flex-col min-h-[520px] mt-2">
            <ChatPanel
              sessionId={sessionId}
              onSessionId={handleSessionId}
              disabled={!bothDone}
            />
          </div>
        </div>

        {/* Right — chat (desktop only) */}
        <div className="hidden lg:flex flex-col flex-1 p-5 min-h-0">
          <ChatPanel
            sessionId={sessionId}
            onSessionId={handleSessionId}
            disabled={!bothDone}
          />
        </div>
      </div>
    </div>
  );
}
