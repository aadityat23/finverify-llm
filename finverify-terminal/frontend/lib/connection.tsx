"use client";

import React, { createContext, useContext, useEffect, useState, useCallback } from "react";
import { checkHealth } from "@/lib/api";

/**
 * ConnectionProvider — Manages backend health state across the app.
 * Checks /health on mount and periodically, exposing connection status
 * so components can fall back to client-side DVL when backend is down.
 */

export type ConnectionStatus = "checking" | "online" | "degraded";

interface ConnectionContextValue {
  status: ConnectionStatus;
  backendOnline: boolean;
  modelName: string;
  refresh: () => void;
}

const ConnectionContext = createContext<ConnectionContextValue>({
  status: "checking",
  backendOnline: false,
  modelName: "finverify-lora",
  refresh: () => {},
});

export function useConnection() {
  return useContext(ConnectionContext);
}

export function ConnectionProvider({ children }: { children: React.ReactNode }) {
  const [status, setStatus] = useState<ConnectionStatus>("checking");
  const [modelName, setModelName] = useState("finverify-lora");

  const checkConnection = useCallback(async () => {
    try {
      const health = await checkHealth();
      if (health.status === "ok" || health.status === "healthy") {
        setStatus("online");
        if (health.model) setModelName(health.model);
      } else {
        setStatus("degraded");
      }
    } catch {
      setStatus("degraded");
    }
  }, []);

  useEffect(() => {
    checkConnection();
    // Re-check every 30 seconds
    const interval = setInterval(checkConnection, 30000);
    return () => clearInterval(interval);
  }, [checkConnection]);

  return (
    <ConnectionContext.Provider
      value={{
        status,
        backendOnline: status === "online",
        modelName,
        refresh: checkConnection,
      }}
    >
      {children}
    </ConnectionContext.Provider>
  );
}
