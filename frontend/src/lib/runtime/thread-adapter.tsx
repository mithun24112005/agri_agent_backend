/* eslint-disable react-refresh/only-export-components -- runtime adapter and provider are a cohesive integration boundary. */
import { createAssistantStream } from "assistant-stream";
import { useMemo, type ReactNode } from "react";
import {
  RuntimeAdapterProvider,
  useAui,
  type RemoteThreadListAdapter,
  type ThreadHistoryAdapter,
} from "@assistant-ui/react";
import { sessionsApi } from "@/lib/api/sessions";
import { chatApi } from "@/lib/api/chat";
import { historyMessage } from "./gateway";
import { gatewayAttachmentAdapter } from "./attachments";

function ThreadAdapters({ children }: { children?: ReactNode }) {
  const aui = useAui();
  const history = useMemo<ThreadHistoryAdapter>(() => ({
    async load() {
      const { remoteId } = aui.threadListItem.getState();
      if (!remoteId) return { messages: [] };
      const response = await chatApi.history(remoteId);
      const messages = response.messages.map((message, index) => ({
        message: historyMessage(message, index, remoteId),
        parentId: index === 0 ? null : `gateway-${remoteId}-${index - 1}`,
      }));
      return { messages };
    },
    async append() {
      // FastAPI persists the user and assistant messages as part of POST /api/chat.
      // The history adapter is intentionally read-only to avoid duplicate writes.
    },
  }), [aui]);

  return <RuntimeAdapterProvider adapters={{ history }}>{children}</RuntimeAdapterProvider>;
}

export const gatewayThreadListAdapter: RemoteThreadListAdapter = {
  async list() {
    const sessions = await sessionsApi.list();
    return {
      threads: sessions.map((session) => ({
        status: "regular" as const,
        remoteId: session.id,
        externalId: session.id,
        title: session.title,
        lastMessageAt: new Date(session.updatedAt),
        custom: { createdAt: session.createdAt },
      })),
    };
  },
  async initialize() {
    const session = await sessionsApi.create("New conversation");
    return { remoteId: session.id, externalId: session.id };
  },
  async rename(remoteId, title) {
    await sessionsApi.rename(remoteId, title.trim() || "New conversation");
  },
  async archive() {
    // The gateway has no archive concept; the UI does not expose archive controls.
  },
  async unarchive() {},
  async delete(remoteId) {
    await sessionsApi.remove(remoteId);
  },
  async fetch(remoteId) {
    const session = await sessionsApi.get(remoteId);
    return { status: "regular", remoteId: session.id, externalId: session.id, title: session.title, lastMessageAt: new Date(session.updatedAt), custom: { createdAt: session.createdAt } };
  },
  async generateTitle(_remoteId, messages) {
    const firstUser = messages.find((message) => message.role === "user");
    const text = typeof firstUser?.content === "string" ? firstUser.content : firstUser?.content.find((part) => part.type === "text")?.text ?? "New conversation";
    return createAssistantStream(async (controller) => controller.appendText(text.replace(/\s+/g, " ").slice(0, 42) || "New conversation"));
  },
  unstable_Provider: ThreadAdapters,
  unstable_useAdapters: () => ({ attachments: gatewayAttachmentAdapter }),
};
