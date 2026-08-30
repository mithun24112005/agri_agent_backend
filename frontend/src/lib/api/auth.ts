import { apiClient, tokenStorage } from "./client";
import type { AuthTokens, User } from "@/types/api";

export const authApi = {
  register: (email: string, password: string) => apiClient.post<{ status: string; message: string }>("/api/auth/register", { email, password }),
  login: async (email: string, password: string) => {
    const tokens = await apiClient.post<AuthTokens>("/api/auth/login", { email, password });
    tokenStorage.set(tokens);
    return tokens;
  },
  me: () => apiClient.get<User>("/api/auth/me"),
  logout: async () => {
    try {
      await apiClient.post<{ status: string; message: string }>("/api/auth/logout", { refreshToken: tokenStorage.refreshToken });
    } finally {
      tokenStorage.clear();
    }
  },
};
