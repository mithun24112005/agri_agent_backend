import { fromThreadMessageLike, type ChatModelAdapter, type CompleteAttachment, type ThreadAssistantMessagePart, type ThreadMessage, type ThreadMessageLike } from "@assistant-ui/react";
import { chatApi } from "@/lib/api/chat";
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
  async *run({ messages, abortSignal, unstable_threadId }) {
    const userMessage = [...messages].reverse().find((message) => message.role === "user");
    if (!userMessage || !unstable_threadId) throw new Error("Choose a conversation before sending a message.");
    const query = getText(userMessage);
    if (!query) throw new Error("Please add a question before sending.");

    const metadata = { custom: { selected_agents: [], agent_responses: {} } };

    // 1. Initial running tool call while LangGraph backend is processing
    const initialRoutingPart: ThreadAssistantMessagePart = {
      type: "tool-call",
      toolCallId: `call-${Date.now()}-routing`,
      toolName: "routing",
      args: { query },
      argsText: JSON.stringify({ query }),
    };
    yield { content: [initialRoutingPart], metadata };

    // 2. Fetch response from gateway API
    const result = await chatApi.send(query, unstable_threadId, getImageFile(userMessage), abortSignal);

    // 3. Extract agents and responses
    const selectedAgents = (
      result.selected_agents && result.selected_agents.length > 0
        ? result.selected_agents
        : Object.keys(result.agent_responses || {})
    ).filter(Boolean);

    const agentsToDisplay = selectedAgents.length > 0 ? selectedAgents : ["general_agent"];
    const custom = {
      selected_agents: agentsToDisplay,
      agent_responses: result.agent_responses || {},
    };

    // 4. Construct completed tool parts for all invoked agents
    const toolParts: ThreadAssistantMessagePart[] = agentsToDisplay.map((agent, index) => ({
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

    // 6. Smooth progressive streaming of response text
    const chunkSize = 24;
    if (responseText.length <= chunkSize) {
      yield {
        content: [
          ...toolParts,
          {
            type: "text",
            text: responseText,
            status: { type: "complete" },
          },
        ],
        metadata: { custom },
      };
    } else {
      for (let i = chunkSize; i < responseText.length; i += chunkSize) {
        if (abortSignal.aborted) throw new DOMException("The response was stopped.", "AbortError");
        yield {
          content: [
            ...toolParts,
            {
              type: "text",
              text: responseText.slice(0, i),
              status: { type: "running" },
            },
          ],
          metadata: { custom },
        };
        await new Promise((resolve) => setTimeout(resolve, 14));
      }

      yield {
        content: [
          ...toolParts,
          {
            type: "text",
            text: responseText,
            status: { type: "complete" },
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
