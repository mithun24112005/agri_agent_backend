import { Leaf, LogOut, Moon, Settings2, Sun, X, MonitorCog, Wifi } from "lucide-react";
import { useAuth } from "@/lib/auth/AuthContext";
import { useTheme, type ThemeMode } from "@/hooks/useTheme";
import { NewChatButton, ThreadList } from "./ThreadList";

interface SidebarProps { open: boolean; onClose: () => void; }

export function Sidebar({ open, onClose }: SidebarProps) {
  const { user, signOut } = useAuth();
  const { theme, setTheme } = useTheme();
  return <aside className={`app-sidebar ${open ? "open" : ""}`}><div className="sidebar-brand"><span className="brand-mark"><Leaf size={17} /></span><span>AgriMind</span><button className="mobile-close" onClick={onClose} aria-label="Close sidebar"><X size={17} /></button></div><div className="sidebar-action"><NewChatButton /></div><ThreadList /><div className="sidebar-bottom"><div className="gateway-status"><span><Wifi size={14} /> Gateway</span><strong><i /> Ready</strong></div><div className="theme-strip" aria-label="Theme"><button className={theme === "light" ? "selected" : ""} onClick={() => setTheme("light")} aria-label="Light theme"><Sun size={14} /></button><button className={theme === "system" ? "selected" : ""} onClick={() => setTheme("system")} aria-label="System theme"><MonitorCog size={14} /></button><button className={theme === "dark" ? "selected" : ""} onClick={() => setTheme("dark")} aria-label="Dark theme"><Moon size={14} /></button></div><div className="sidebar-user"><div className="user-avatar">{user?.email.slice(0, 1).toUpperCase()}</div><div className="user-details"><strong>{user?.email.split("@")[0]}</strong><span>{user?.email}</span></div><button className="logout-button" onClick={() => void signOut()} aria-label="Log out"><LogOut size={16} /></button></div><button className="settings-button"><Settings2 size={15} /> Preferences <span>⌘ ,</span></button></div></aside>;
}

export function ThemeLabel({ mode }: { mode: ThemeMode }) { return <span>{mode === "light" ? "Light" : mode === "dark" ? "Dark" : "System"}</span>; }
