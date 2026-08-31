import { fromThreadMessageLike, type ChatModelAdapter, type CompleteAttachment, type ThreadMessage, type ThreadMessageLike } from "@assistant-ui/react";
import { chatApi } from "@/lib/api/chat";
import { activityStore } from "./activity";
import type { AgentName } from "@/types/api";
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

export const gatewayModelAdapter: ChatModelAdapter = {
  async run({ messages, abortSignal, unstable_threadId }) {
    const userMessage = [...messages].reverse().find((message) => message.role === "user");
    if (!userMessage || !unstable_threadId) throw new Error("Choose a conversation before sending a message.");
    const query = getText(userMessage);
    if (!query) throw new Error("Please add a question before sending.");

    activityStore.set({ status: "processing", agents: [], selectedCount: 0 });
    try {
      const result = await chatApi.send(query, unstable_threadId, getImageFile(userMessage), abortSignal);
      const agents = result.selected_agents.filter((agent): agent is AgentName => ["disease_agent", "crop_agent", "general_agent"].includes(agent));
      activityStore.set({ status: "complete", agents, selectedCount: agents.length });
      return {
        content: [{ type: "text", text: result.response }],
        metadata: { custom: { selected_agents: agents, agent_responses: result.agent_responses } },
      };
    } catch (error) {
      const isAbort = error instanceof Error && error.name === "AbortError";
      activityStore.set(isAbort ? { status: "idle", agents: [], selectedCount: 0 } : { status: "error", agents: [], selectedCount: 0 });
      throw error;
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
