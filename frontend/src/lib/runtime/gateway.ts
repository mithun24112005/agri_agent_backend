import { fromThreadMessageLike, type ChatModelAdapter, type CompleteAttachment, type ThreadAssistantMessagePart, type ThreadMessage, type ThreadMessageLike } from "@assistant-ui/react";
import { chatApi } from "@/lib/api/chat";
import { sessionsApi } from "@/lib/api/sessions";
import type { ChatMessage } from "@/types/api";

function getText(message: ThreadMessage): string {
  return message.content.filter((part) => part.type === "text").map((part) => part.text).join("\n").trim();
}

function getImageFileFromAttachment(attachment: CompleteAttachment): File | undefined {
  return attachment.file;
}

function getImageFile(message: ThreadMessage): File | undefined {
  if (message.role === "user") {
    for (const attachment of message.attachments ?? []) {
      const file = getImageFileFromAttachment(attachment);
      if (file) return file;
    }
  }
  return undefined;
}

function splitResponseIntoChunks(text: string): string[] {
  const tokens = text.match(/\S+\s*/g) ?? [text];
  const chunks: string[] = [];
  let current = "";

  for (const token of tokens) {
    current += token;
    if (current.length >= 28 || /\n\s*$/.test(token)) {
      chunks.push(current);
      current = "";
    }
  }

  if (current) chunks.push(current);
  return chunks.length > 0 ? chunks : [text];
}

function waitForStreamTick(signal: AbortSignal, milliseconds: number) {
  return new Promise<void>((resolve) => {
    if (signal.aborted) {
      resolve();
      return;
    }

    const timer = window.setTimeout(() => {
      signal.removeEventListener("abort", onAbort);
      resolve();
    }, milliseconds);
    const onAbort = () => {
      window.clearTimeout(timer);
      signal.removeEventListener("abort", onAbort);
      resolve();
    };
    signal.addEventListener("abort", onAbort, { once: true });
  });
}

let activeOrPendingSessionId: string | null = null;

export function setActiveSessionId(sessionId: string | null) {
  activeOrPendingSessionId = sessionId;
}

export function getActiveSessionId(): string | null {
  return activeOrPendingSessionId;
}

export const gatewayModelAdapter: ChatModelAdapter = {
  async *run({ messages, abortSignal, unstable_threadId }) {
    const userMessage = [...messages].reverse().find((message) => message.role === "user");
    if (!userMessage) throw new Error("Please add a question before sending.");
    const query = getText(userMessage);
    if (!query) throw new Error("Please add a question before sending.");

    let sessionId = unstable_threadId || activeOrPendingSessionId;
    if (!sessionId) {
      try {
        const newSession = await sessionsApi.create("New conversation");
        sessionId = newSession.id;
      } catch {
        throw new Error("Choose a conversation before sending a message.");
      }
    }
    setActiveSessionId(sessionId);

    const metadata = { custom: { selected_agents: [], agent_responses: {} } };

    // 1. Initial pending state for natural assistant loading indicator
    yield {
      content: [
        {
          type: "text",
          text: "",
          status: { type: "running" },
        },
      ],
      metadata,
    };

    // 2. Fetch response from gateway API
    const result = await chatApi.send(query, sessionId, getImageFile(userMessage), abortSignal);

    // 3. Extract genuinely invoked agents
    const selectedAgents = (
      result.selected_agents && result.selected_agents.length > 0
        ? result.selected_agents
        : Object.keys(result.agent_responses || {})
    ).filter(Boolean);

    const custom = {
      selected_agents: selectedAgents,
      agent_responses: result.agent_responses || {},
    };

    // 4. Construct tool parts only for genuinely invoked specialist agents
    const toolParts: ThreadAssistantMessagePart[] = selectedAgents.map((agent, index) => ({
      type: "tool-call",
      toolCallId: `call-${Date.now()}-${index}-${agent}`,
      toolName: agent,
      args: { query },
      argsText: JSON.stringify({ query }),
      result: result.agent_responses?.[agent] ?? null,
    }));

    // 5. Determine the response text to render
    const rawResponse = result.response?.trim();
    const fallbackResponse = Object.values(result.agent_responses || {}).find(
      (v): v is string => typeof v === "string" && v.trim().length > 0
    );
    const responseText = rawResponse || fallbackResponse || "Analysis completed.";

    // 6. Reveal the completed API response progressively through assistant-ui.
    // The gateway remains request/response based; this only improves perceived continuity.
    let streamedText = "";
    const chunks = splitResponseIntoChunks(responseText);

    for (const [index, chunk] of chunks.entries()) {
      if (abortSignal.aborted) return;
      streamedText += chunk;
      await waitForStreamTick(abortSignal, index === 0 ? 80 : 24);
      if (abortSignal.aborted) return;

      yield {
        content: [
          ...toolParts,
          {
            type: "text",
            text: streamedText,
            status: { type: index === chunks.length - 1 ? "complete" : "running" },
          },
        ],
        metadata: { custom },
      };
    }
  },
};

export function historyMessage(message: ChatMessage, index: number, sessionId: string): ThreadMessage {
  const id = `gateway-${sessionId}-${index}`;
  const like: ThreadMessageLike = {
    id,
    role: message.role,
    content: [{ type: "text", text: message.content }],
    createdAt: new Date(),
    status: message.role === "assistant" ? { type: "complete", reason: "stop" } : undefined,
    metadata: { custom: {} },
    ...(message.image ? {
      attachments: [{
        id: `${id}-image`,
        type: "image" as const,
        name: message.image.filename,
        contentType: message.image.content_type,
        content: [{ type: "image" as const, image: message.image.data_url, filename: message.image.filename }],
        status: { type: "complete" as const },
      }],
    } : {}),
  };
  return fromThreadMessageLike(like, id, { type: "complete", reason: "stop" });
}
