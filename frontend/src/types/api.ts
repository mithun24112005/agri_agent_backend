export type AgentName = "disease_agent" | "crop_agent" | "general_agent";

export interface User {
  id: string;
  email: string;
  createdAt: string;
  isActive: boolean;
}

export interface AuthTokens {
  accessToken: string;
  refreshToken: string;
}

export interface Session {
  id: string;
  title: string;
  userId: string;
  createdAt: string;
  updatedAt: string;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface ChatHistory {
  session_id: string;
  messages: ChatMessage[];
}

export interface ChatResponse {
  status: "success";
  query: string;
  response: string;
  session_id: string;
  selected_agents: AgentName[];
  agent_responses: Record<string, string>;
}

export interface GatewayErrorPayload {
  error?: {
    code?: string;
    message?: string;
    details?: unknown;
  };
  detail?: string;
  message?: string;
}
