import {
  AssistantRuntimeProvider,
  useLocalRuntime,
  useRemoteThreadListRuntime,
} from "@assistant-ui/react";
import { AuthPage } from "@/components/auth/AuthPage";
import { AppShell } from "@/components/layout/AppShell";
import { ChatWorkspace } from "@/components/chat/ChatWorkspace";
import { DashboardView } from "@/components/dashboard/DashboardView";
import { CropRecommendationView } from "@/components/crop/CropRecommendationView";
import { DiseaseDetectionView } from "@/components/disease/DiseaseDetectionView";
import { SettingsView } from "@/components/settings/SettingsView";
import { useAuth } from "@/lib/auth/AuthContext";
import { gatewayAttachmentAdapter } from "@/lib/runtime/attachments";
import { gatewayModelAdapter } from "@/lib/runtime/gateway";
import { gatewayThreadListAdapter } from "@/lib/runtime/thread-adapter";
import { useTheme } from "@/hooks/useTheme";
import type { AppRoute } from "@/hooks/useHashRoute";

function AuthenticatedApp() {
  const runtime = useRemoteThreadListRuntime({
    runtimeHook: useGatewayRuntime,
    adapter: gatewayThreadListAdapter,
  });

  const renderView = (route: AppRoute, navigate: (path: string) => void) => {
    switch (route) {
      case "home":
        return <DashboardView onNavigate={navigate} />;
      case "crop":
        return <CropRecommendationView onNavigate={navigate} />;
      case "disease":
        return <DiseaseDetectionView onNavigate={navigate} />;
      case "settings":
        return <SettingsView onNavigate={navigate} />;
      case "chat":
      default:
        return <ChatWorkspace />;
    }
  };

  return (
    <AssistantRuntimeProvider runtime={runtime}>
      <AppShell renderView={renderView} />
    </AssistantRuntimeProvider>
  );
}

function useGatewayRuntime() {
  return useLocalRuntime(gatewayModelAdapter, { adapters: { attachments: gatewayAttachmentAdapter } });
}

export default function App() {
  useTheme();
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="app-loading">
        <div className="loading-glyph">✦</div>
        <span>Preparing your field desk…</span>
      </div>
    );
  }

  return user ? <AuthenticatedApp /> : <AuthPage />;
}
