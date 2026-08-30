import type { AuthTokens, GatewayErrorPayload } from "@/types/api";

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? "http://localhost:3001").replace(/\/$/, "");
const ACCESS_TOKEN_KEY = "agrimind.access-token";
const REFRESH_TOKEN_KEY = "agrimind.refresh-token";

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly payload: GatewayErrorPayload | null;

  constructor(message: string, status: number, code = "REQUEST_FAILED", payload: GatewayErrorPayload | null = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.payload = payload;
  }
}

export const tokenStorage = {
  get accessToken() {
    return window.localStorage.getItem(ACCESS_TOKEN_KEY);
  },
  get refreshToken() {
    return window.localStorage.getItem(REFRESH_TOKEN_KEY);
  },
  set(tokens: AuthTokens) {
    window.localStorage.setItem(ACCESS_TOKEN_KEY, tokens.accessToken);
    window.localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refreshToken);
  },
  clear() {
    window.localStorage.removeItem(ACCESS_TOKEN_KEY);
    window.localStorage.removeItem(REFRESH_TOKEN_KEY);
  },
};

const notifyAuthExpired = () => window.dispatchEvent(new CustomEvent("agrimind:auth-expired"));

let refreshPromise: Promise<AuthTokens> | null = null;

async function refreshAccessToken(): Promise<AuthTokens> {
  const refreshToken = tokenStorage.refreshToken;
  if (!refreshToken) throw new ApiError("Your session has expired. Please sign in again.", 401, "AUTHENTICATION_FAILED");

  const response = await fetch(`${API_BASE_URL}/api/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refreshToken }),
  });

  const payload = (await response.json().catch(() => null)) as GatewayErrorPayload | AuthTokens | null;
  if (!response.ok || !payload || !("accessToken" in payload) || !("refreshToken" in payload)) {
    tokenStorage.clear();
    notifyAuthExpired();
    const errorPayload = payload && "error" in payload ? payload : null;
    throw new ApiError(
      getErrorMessage(response.status, errorPayload),
      response.status,
      errorPayload?.error?.code ?? "AUTHENTICATION_FAILED",
      errorPayload,
    );
  }

  tokenStorage.set(payload);
  return payload;
}

function getErrorMessage(status: number, payload: GatewayErrorPayload | null): string {
  if (status === 413) return "That image is too large. The maximum size is 5 MB.";
  if (status === 429) return "You’re sending requests too quickly. Please try again in a moment.";
  if (status === 503) return "The gateway is temporarily unavailable. Please try again shortly.";
  if (status === 504) return "The agriculture assistant took too long to respond. Please try again.";
  if (status === 502) return "The agriculture assistant is temporarily unavailable.";
  if (status === 401) return "Your session has expired. Please sign in again.";
  if (status === 403) return "You don’t have permission to do that.";
  return payload?.error?.message ?? payload?.detail ?? payload?.message ?? "Something went wrong. Please try again.";
}

async function request<T>(path: string, options: RequestInit = {}, retryOnUnauthorized = true): Promise<T> {
  const headers = new Headers(options.headers);
  if (!(options.body instanceof FormData) && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  const accessToken = tokenStorage.accessToken;
  if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`);

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") throw error;
    throw new ApiError("We couldn’t reach the gateway. Check that the backend is running.", 0, "NETWORK_ERROR");
  }

  if (response.status === 401 && retryOnUnauthorized && path !== "/api/auth/refresh") {
    try {
      if (!refreshPromise) refreshPromise = refreshAccessToken().finally(() => { refreshPromise = null; });
      await refreshPromise;
      return request<T>(path, options, false);
    } catch {
      notifyAuthExpired();
    }
  }

  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as GatewayErrorPayload | null;
    throw new ApiError(getErrorMessage(response.status, payload), response.status, payload?.error?.code, payload);
  }
  if (response.status === 204) return null as T;
  const text = await response.text();
  return (text ? JSON.parse(text) : null) as T;
}

export const apiClient = {
  get: <T>(path: string, signal?: AbortSignal) => request<T>(path, { method: "GET", signal }),
  post: <T>(path: string, body: unknown, signal?: AbortSignal) => request<T>(path, { method: "POST", body: JSON.stringify(body), signal }),
  patch: <T>(path: string, body: unknown, signal?: AbortSignal) => request<T>(path, { method: "PATCH", body: JSON.stringify(body), signal }),
  delete: <T>(path: string, signal?: AbortSignal) => request<T>(path, { method: "DELETE", signal }),
  form: <T>(path: string, body: FormData, signal?: AbortSignal) => request<T>(path, { method: "POST", body, signal }),
};

export const authEvents = { notifyExpired: notifyAuthExpired };
