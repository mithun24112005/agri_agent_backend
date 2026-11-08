import { useState, useEffect, useCallback } from "react";

export type AppRoute = "home" | "chat" | "crop" | "disease" | "settings";

export interface ParsedRoute {
  route: AppRoute;
  param?: string;
  hash: string;
}

export function parseHash(hash: string): ParsedRoute {
  const clean = hash.replace(/^#\/?/, "").trim();
  const parts = clean.split("/").filter(Boolean);
  const root = parts[0]?.toLowerCase() ?? "home";

  if (root === "chat") {
    return {
      route: "chat",
      param: parts[1], // session_id if present
      hash,
    };
  }
  if (root === "crop") {
    return { route: "crop", hash };
  }
  if (root === "disease") {
    return { route: "disease", hash };
  }
  if (root === "settings") {
    return { route: "settings", hash };
  }

  // Default to home
  return { route: "home", hash };
}

export function useHashRoute() {
  const [currentRoute, setCurrentRoute] = useState<ParsedRoute>(() =>
    parseHash(window.location.hash || "#/home")
  );

  useEffect(() => {
    // If no hash at startup, set to #/home
    if (!window.location.hash || window.location.hash === "#") {
      window.location.hash = "#/home";
    }

    const handleHashChange = () => {
      setCurrentRoute(parseHash(window.location.hash));
    };

    window.addEventListener("hashchange", handleHashChange);
    return () => window.removeEventListener("hashchange", handleHashChange);
  }, []);

  const navigate = useCallback((path: string) => {
    const targetHash = path.startsWith("#") ? path : `#${path.startsWith("/") ? "" : "/"}${path}`;
    if (window.location.hash !== targetHash) {
      window.location.hash = targetHash;
    } else {
      setCurrentRoute(parseHash(targetHash));
    }
  }, []);

  return {
    ...currentRoute,
    navigate,
  };
}

