/* eslint-disable react-refresh/only-export-components -- context hook and provider intentionally share one module. */
import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { authApi } from "@/lib/api/auth";
import { tokenStorage } from "@/lib/api/client";
import type { User } from "@/types/api";

interface AuthContextValue {
  user: User | null;
  isLoading: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const refreshUser = async () => {
    if (!tokenStorage.accessToken && !tokenStorage.refreshToken) {
      setUser(null);
      return;
    }
    try {
      setUser(await authApi.me());
    } catch {
      tokenStorage.clear();
      setUser(null);
    }
  };

  useEffect(() => {
    // Initial auth hydration is intentionally stateful: it resolves the existing bearer session.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void refreshUser().finally(() => setIsLoading(false));
    const handleExpired = () => setUser(null);
    window.addEventListener("agrimind:auth-expired", handleExpired);
    return () => window.removeEventListener("agrimind:auth-expired", handleExpired);
  }, []);

  const value = useMemo<AuthContextValue>(() => ({
    user,
    isLoading,
    signIn: async (email, password) => {
      await authApi.login(email, password);
      await refreshUser();
    },
    signOut: async () => {
      await authApi.logout();
      setUser(null);
    },
    refreshUser,
  }), [isLoading, user]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AuthProvider");
  return context;
}
