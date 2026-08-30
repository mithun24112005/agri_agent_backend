import { useSyncExternalStore } from "react";
import type { AgentName } from "@/types/api";

export interface AgentActivityState {
  status: "idle" | "processing" | "complete" | "error";
  agents: AgentName[];
  selectedCount: number;
}

const empty: AgentActivityState = { status: "idle", agents: [], selectedCount: 0 };
let state = empty;
const listeners = new Set<() => void>();

export const activityStore = {
  getSnapshot: () => state,
  subscribe: (listener: () => void) => {
    listeners.add(listener);
    return () => listeners.delete(listener);
  },
  set(next: AgentActivityState) {
    state = next;
    listeners.forEach((listener) => listener());
  },
  reset() { state = empty; listeners.forEach((listener) => listener()); },
};

export function useAgentActivity() {
  return useSyncExternalStore(activityStore.subscribe, activityStore.getSnapshot, activityStore.getSnapshot);
}
