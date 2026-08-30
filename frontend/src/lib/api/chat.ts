import { apiClient } from "./client";
import type { ChatHistory, ChatResponse } from "@/types/api";

export const chatApi = {
  history: (sessionId: string, signal?: AbortSignal) => apiClient.get<ChatHistory>(`/api/chat/${sessionId}`, signal),
  send: (query: string, sessionId: string, file?: File, signal?: AbortSignal) => {
    const body = new FormData();
    body.append("query", query);
    body.append("session_id", sessionId);
    if (file) body.append("file", file, file.name);
    return apiClient.form<ChatResponse>("/api/chat", body, signal);
  },
};
