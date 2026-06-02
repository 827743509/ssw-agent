import { Client } from "@langchain/langgraph-sdk";

export type AgentId = "supervisor" | "text_to_sql_agent" | "default_agent";

export type StreamProgress = {
  node?: string;
  detail: string;
};

export type StreamCallbacks = {
  onToken: (token: string) => void;
  onProgress: (progress: StreamProgress) => void;
  onDone: () => void;
  onError: (message: string) => void;
};

const apiUrl = import.meta.env.VITE_LANGGRAPH_API_URL || "http://127.0.0.1:2024";

const client = new Client({
  apiUrl,
});

function readContentPart(part: unknown): string {
  if (typeof part === "string") {
    return part;
  }

  if (part && typeof part === "object" && "text" in part) {
    const text = (part as { text?: unknown }).text;
    return typeof text === "string" ? text : "";
  }

  return "";
}

function extractTextFromMessage(message: unknown): string {
  if (!message || typeof message !== "object") {
    return "";
  }

  const content = (message as { content?: unknown }).content;
  if (typeof content === "string") {
    return content;
  }

  if (Array.isArray(content)) {
    return content.map(readContentPart).join("");
  }

  return "";
}

function extractToken(chunk: unknown): string {
  if (Array.isArray(chunk)) {
    return extractTextFromMessage(chunk[0]);
  }

  if (chunk && typeof chunk === "object") {
    const data = chunk as { data?: unknown; event?: unknown };
    if (Array.isArray(data.data)) {
      return extractTextFromMessage(data.data[0]);
    }

    return extractTextFromMessage(data.data);
  }

  return "";
}

function summarizeUpdate(chunk: unknown): StreamProgress | null {
  if (!chunk || typeof chunk !== "object") {
    return null;
  }

  const payload = "data" in chunk ? (chunk as { data?: unknown }).data : chunk;
  if (!payload || typeof payload !== "object") {
    return null;
  }

  const [node, value] = Object.entries(payload as Record<string, unknown>)[0] ?? [];
  if (!node) {
    return null;
  }

  if (value && typeof value === "object" && "messages" in value) {
    return { node, detail: "正在更新消息" };
  }

  return { node, detail: "正在处理" };
}

export async function streamAgentAnswer(
  agentId: AgentId,
  question: string,
  signal: AbortSignal,
  callbacks: StreamCallbacks,
): Promise<void> {
  try {
    const stream = client.runs.stream(null, agentId, {
      input: {
        messages: [{ role: "user", content: question }],
      },
      streamMode: ["messages-tuple", "updates"],
      streamSubgraphs: true,
      signal,
    });

    for await (const chunk of stream) {
      if (signal.aborted) {
        break;
      }

      const event = typeof chunk === "object" && chunk && "event" in chunk
        ? String((chunk as { event?: unknown }).event)
        : "";

      if (event.includes("messages")) {
        const token = extractToken(chunk);
        if (token) {
          callbacks.onToken(token);
        }
        continue;
      }

      if (event.includes("updates")) {
        const progress = summarizeUpdate(chunk);
        if (progress) {
          callbacks.onProgress(progress);
        }
      }
    }

    callbacks.onDone();
  } catch (error) {
    if (signal.aborted) {
      callbacks.onDone();
      return;
    }

    callbacks.onError(error instanceof Error ? error.message : "流式请求失败");
  }
}

export function getLangGraphApiUrl(): string {
  return apiUrl;
}
