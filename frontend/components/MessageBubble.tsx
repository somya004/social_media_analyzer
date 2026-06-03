import SourceList from "@/components/SourceList";
import type { SourceCitation } from "@/lib/api";

interface Props {
  role: "user" | "assistant";
  content: string;
  sources?: SourceCitation[];
  streaming?: boolean;
  error?: boolean;
}

export default function MessageBubble({ role, content, sources, streaming, error }: Props) {
  const isUser = role === "user";

  return (
    <div className={`flex flex-col gap-1.5 animate-fade-up ${isUser ? "items-end" : "items-start"}`}>
      <div className={`max-w-[88%] rounded-2xl px-4 py-3 text-sm leading-relaxed
        ${isUser
          ? "bg-gradient-to-br from-indigo-600 to-indigo-700 text-white font-medium shadow-lg shadow-indigo-900/30"
          : error
            ? "bg-red-950/40 border border-red-500/20 text-red-300 font-mono"
            : "glass text-zinc-200 font-mono border border-white/8"
        }`}
      >
        <span className="whitespace-pre-wrap">{content}</span>
        {streaming && !isUser && (
          <span className="inline-block w-0.5 h-4 bg-indigo-400 ml-0.5 align-middle animate-cursor-blink" />
        )}
      </div>
      {!isUser && sources && sources.length > 0 && (
        <div className="max-w-[88%] w-full px-1">
          <SourceList sources={sources} />
        </div>
      )}
    </div>
  );
}
