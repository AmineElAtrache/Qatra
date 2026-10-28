"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import type { Session } from "./types";

const KEY = "qatra.session";

type Ctx = {
  session: Session | null;
  ready: boolean;
  signIn: (s: Session) => void;
  signOut: () => void;
};

const SessionContext = createContext<Ctx>({ session: null, ready: false, signIn: () => {}, signOut: () => {} });

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const [session, setSession] = useState<Session | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    try {
      const raw = localStorage.getItem(KEY);
      if (raw) setSession(JSON.parse(raw));
    } catch {
      /* storage blocked: stay signed out */
    }
    setReady(true);
  }, []);

  const signIn = useCallback((s: Session) => {
    setSession(s);
    try {
      localStorage.setItem(KEY, JSON.stringify(s));
    } catch {
      /* ignore */
    }
  }, []);

  const signOut = useCallback(() => {
    setSession(null);
    try {
      localStorage.removeItem(KEY);
    } catch {
      /* ignore */
    }
  }, []);

  return <SessionContext.Provider value={{ session, ready, signIn, signOut }}>{children}</SessionContext.Provider>;
}

export const useSession = () => useContext(SessionContext);

/** Rings drawn on this device, keyed by plot id, until the API returns geometry. */
const RINGS = "qatra.rings";

export function saveRing(plotId: string, ring: number[][]) {
  try {
    const all = JSON.parse(localStorage.getItem(RINGS) || "{}");
    all[plotId] = ring;
    localStorage.setItem(RINGS, JSON.stringify(all));
  } catch {
    /* ignore */
  }
}

export function loadRings(): Record<string, number[][]> {
  try {
    return JSON.parse(localStorage.getItem(RINGS) || "{}");
  } catch {
    return {};
  }
}
