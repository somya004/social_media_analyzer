const BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000/api";

export interface AnalyzeYouTubeResponse {
  video_id: string;
  source: "youtube";
  title: string | null;
  creator: string | null;
  upload_date: string | null;
  duration: number | null;
  views: number | null;
  likes: number | null;
  hashtags: string[];
  thumbnail_url: string | null;
  transcript_chars: number;
  chunks_stored: number;
  transcript_available: boolean;
}

export interface AnalyzeInstagramResponse {
  video_id: string;
  source: "instagram";
  shortcode: string | null;
  creator: string | null;
  creator_full_name: string | null;
  followers: number | null;
  upload_date: string | null;
  duration: number | null;
  views: number | null;
  likes: number | null;
  comments: number | null;
  engagement_rate: number | null;
  hashtags: string[];
  thumbnail_url: string | null;
  caption_chars: number;
  chunks_stored: number;
  caption_available: boolean;
}

export interface SourceCitation {
  video_id: string;
  source: string;
  chunk_id: string;
  title: string;
  evidence: string;
  score: number;
}

async function handleError(res: Response): Promise<never> {
  let detail = `HTTP ${res.status}`;
  try {
    const body = await res.json();
    detail = body.detail ?? detail;
  } catch { /* not JSON */ }
  throw new Error(detail);
}

export async function analyzeYouTube(url: string): Promise<AnalyzeYouTubeResponse> {
  const res = await fetch(`${BASE_URL}/analyze/youtube`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url, video_id: "A" }),
  });
  if (!res.ok) await handleError(res);
  return res.json();
}

export async function analyzeInstagram(url: string): Promise<AnalyzeInstagramResponse> {
  const res = await fetch(`${BASE_URL}/analyze/instagram`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url, video_id: "B" }),
  });
  if (!res.ok) await handleError(res);
  return res.json();
}

export interface StreamHandlers {
  onStart: (sessionId: string) => void;
  onToken: (token: string) => void;
  onSources: (sources: SourceCitation[]) => void;
  onDone: (sessionId: string) => void;
  onError: (message: string) => void;
}

export async function streamChat(
  question: string,
  sessionId: string | null,
  handlers: StreamHandlers
): Promise<void> {
  let res: Response;
  try {
    res = await fetch(`${BASE_URL}/chat/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, session_id: sessionId }),
    });
  } catch {
    handlers.onError("Cannot reach the API server. Is the backend running?");
    return;
  }

  if (!res.ok || !res.body) {
    handlers.onError(`Server returned ${res.status}`);
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const blocks = buffer.split("\n\n");
    buffer = blocks.pop() ?? "";

    for (const block of blocks) {
      let eventType = "";
      let dataLine = "";
      for (const line of block.split("\n")) {
        if (line.startsWith("event:")) eventType = line.slice(6).trim();
        if (line.startsWith("data:")) dataLine = line.slice(5).trim();
      }
      if (!eventType || !dataLine) continue;
      try {
        const payload = JSON.parse(dataLine);
        switch (eventType) {
          case "start": handlers.onStart(payload.session_id ?? ""); break;
          case "token": handlers.onToken(payload.token ?? ""); break;
          case "sources": handlers.onSources(payload.sources ?? []); break;
          case "done": handlers.onDone(payload.session_id ?? ""); break;
          case "error": handlers.onError(payload.message ?? "Unknown error"); break;
        }
      } catch { /* skip malformed */ }
    }
  }
}
