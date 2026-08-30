import { Menu, ShieldCheck, Sprout } from "lucide-react";
import { useAuiState } from "@assistant-ui/react";
import { AgriThread } from "@/components/assistant-ui/Thread";
import { AgentActivity } from "./AgentActivity";

interface ChatWorkspaceProps { onOpenSidebar: () => void; }

export function ChatWorkspace({ onOpenSidebar }: ChatWorkspaceProps) {
  const activeTitle = useAuiState((state) => state.threads.threadItems.find((item) => item.id === state.threads.mainThreadId)?.title ?? "New conversation");
  return <section className="chat-workspace"><header className="topbar"><button className="mobile-menu" onClick={onOpenSidebar} aria-label="Open sidebar"><Menu size={18} /></button><div className="conversation-title"><span className="title-dot" /><span>{activeTitle}</span></div><div className="topbar-meta"><span><ShieldCheck size={14} /> Gateway secured</span><span className="topbar-separator" /><span>Local workspace</span></div></header><div className="conversation-main"><div className="conversation-kicker"><Sprout size={14} /> Agriculture intelligence desk</div><AgriThread /></div><AgentActivity /></section>;
}
