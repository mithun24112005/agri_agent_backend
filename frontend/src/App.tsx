import { useState } from "react";
import {
  AssistantRuntimeProvider,
  useLocalRuntime,
  useRemoteThreadListRuntime,
} from "@assistant-ui/react";
import { AuthPage } from "@/components/auth/AuthPage";
import { Sidebar } from "@/components/sidebar/Sidebar";
import { ChatWorkspace } from "@/components/chat/ChatWorkspace";
import { useAuth } from "@/lib/auth/AuthContext";
import { gatewayAttachmentAdapter } from "@/lib/runtime/attachments";
import { gatewayModelAdapter } from "@/lib/runtime/gateway";
import { gatewayThreadListAdapter } from "@/lib/runtime/thread-adapter";
import { useTheme } from "@/hooks/useTheme";

function AuthenticatedApp() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const runtime = useRemoteThreadListRuntime({
    runtimeHook: useGatewayRuntime,
    adapter: gatewayThreadListAdapter,
  });
  return <AssistantRuntimeProvider runtime={runtime}><div className="app-shell"><div className="mobile-scrim" onClick={() => setSidebarOpen(false)} aria-hidden={!sidebarOpen} /><Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} /><ChatWorkspace onOpenSidebar={() => setSidebarOpen(true)} /></div></AssistantRuntimeProvider>;
}

function useGatewayRuntime() {
  return useLocalRuntime(gatewayModelAdapter, { adapters: { attachments: gatewayAttachmentAdapter } });
}

export default function App() {
  useTheme();
  const { user, isLoading } = useAuth();
  if (isLoading) return <div className="app-loading"><div className="loading-glyph">✦</div><span>Preparing your field desk…</span></div>;
  return user ? <AuthenticatedApp /> : <AuthPage />;
}
