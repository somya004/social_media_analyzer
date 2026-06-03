"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import MessageBubble from "@/components/MessageBubble";
import { streamChat } from "@/lib/api";
import type { SourceCitation } from "@/lib/api";

interface Message {
  id: number;
  role: "user" | "assistant";
  content: string;
  sources?: SourceCitation[];
  streaming?: boolean;
  error?: boolean;
}

interface Props {
  sessionId: string | null;
  onSessionId: (id: string) => void;
  disabled?: boolean;
}

let _id = 0;
const uid = () => ++_id;

export default function ChatPanel({ sessionId, onSessionId, disabled }: Props) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const patch = useCallback((id: number, update: Partial<Message>) => {
    setMessages(prev => prev.map(m => m.id === id ? { ...m, ...update } : m));
  }, []);

  async function handleSend() {
    const text = input.trim();
    if (!text || isStreaming || disabled) return;
    setInput("");

    const userMsgId = uid();
    const asstMsgId = uid();

    setMessages(prev => [
      ...prev,
      { id: userMsgId, role: "user", content: text },
      { id: asstMsgId, role: "assistant", content: "", streaming: true },
    ]);
    setIsStreaming(true);

    await streamChat(text, sessionId, {
      onStart(sid) { if (sid) onSessionId(sid); },
      onToken(token) {
        setMessages(prev => prev.map(m =>
          m.id === asstMsgId ? { ...m, content: m.content + token } : m
        ));
      },
      onSources(sources) { patch(asstMsgId, { sources }); },
      onDone(sid) {
        if (sid) onSessionId(sid);
        patch(asstMsgId, { streaming: false });
        setIsStreaming(false);
        setTimeout(() => inputRef.current?.focus(), 50);
      },
      onError(message) {
        patch(asstMsgId, { content: message, streaming: false, error: true });
        setIsStreaming(false);
      },
    });
  }

  const canSend = !isStreaming && !disabled && input.trim().length > 0;

  return (
    <div className="flex flex-col h-full glass chat-gradient rounded-2xl overflow-hidden border border-indigo-500/15 animate-pulse-glow">
      {/* Header */}
      <div className="px-5 py-3.5 border-b border-white/6 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-2.5">
          <div className="w-2 h-2 rounded-full bg-indigo-400 animate-pulse" />
          <span className="text-sm font-semibold text-chat">Chat</span>
        </div>
        {sessionId && (
          <span className="text-[10px] font-mono text-zinc-600 bg-white/5 px-2 py-1 rounded-lg">
            {sessionId.slice(0, 8)}…
          </span>
        )}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-3 min-h-0">
        {messages.length === 0 && (
          <div className="flex-1 flex flex-col items-center justify-center gap-3 py-8 opacity-50">
            <div className="w-12 h-12 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} className="w-6 h-6 text-indigo-400">
                <path strokeLinecap="round" strokeLinejoin="round" d="M8.625 12a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H8.25m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H12m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0h-.375M21 12c0 4.556-4.03 8.25-9 8.25a9.764 9.764 0 01-2.555-.337A5.972 5.972 0 015.41 20.97a5.969 5.969 0 01-.474-.065 4.48 4.48 0 00.978-2.025c.09-.457-.133-.901-.467-1.226C3.93 16.178 3 14.189 3 12c0-4.556 4.03-8.25 9-8.25s9 3.694 9 8.25z" />
              </svg>
            </div>
            <p className="text-xs font-mono text-zinc-500 text-center max-w-[180px]">
              {disabled
                ? "Analyze a video above to unlock chat"
                : "Ask anything about the analyzed content"}
            </p>
          </div>
        )}
        {messages.map(msg => (
          <MessageBubble
            key={msg.id}
            role={msg.role}
            content={msg.error ? `Error: ${msg.content}` : msg.content}
            sources={msg.sources}
            streaming={msg.streaming}
            error={msg.error}
          />
        ))}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="border-t border-white/6 p-3 flex gap-2 shrink-0">
        <input
          ref={inputRef}
          type="text"
          placeholder={disabled ? "Analyze a video first..." : "Ask about the content..."}
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === "Enter" && handleSend()}
          disabled={disabled || isStreaming}
          className="flex-1 bg-white/5 border border-white/10 rounded-xl px-3.5 py-2.5 text-sm
            font-mono text-white placeholder-zinc-600 outline-none
            focus:border-indigo-500/50 transition-colors disabled:opacity-40"
        />
        <button
          onClick={handleSend}
          disabled={!canSend}
          className="btn-spring bg-gradient-to-br from-indigo-600 to-indigo-700 hover:from-indigo-500
            hover:to-indigo-600 text-white font-semibold text-sm px-4 py-2.5 rounded-xl
            shadow-lg shadow-indigo-900/40 disabled:opacity-40 disabled:cursor-not-allowed
            disabled:transform-none transition-all duration-200"
        >
          Send
        </button>
      </div>
    </div>
  );
}
