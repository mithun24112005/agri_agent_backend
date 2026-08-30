import { apiClient } from "./client";
import type { Session } from "@/types/api";

export const sessionsApi = {
  list: (signal?: AbortSignal) => apiClient.get<Session[]>("/api/sessions", signal),
  create: (title: string) => apiClient.post<Session>("/api/sessions", { title }),
  get: (id: string, signal?: AbortSignal) => apiClient.get<Session>(`/api/sessions/${id}`, signal),
  rename: (id: string, title: string) => apiClient.patch<Session>(`/api/sessions/${id}`, { title }),
  remove: (id: string) => apiClient.delete<{ status: string; message: string }>(`/api/sessions/${id}`),
};
