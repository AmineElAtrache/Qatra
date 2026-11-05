"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Bell, BellRing, LoaderCircle, Send, Smartphone, X } from "lucide-react";
import { ApiError, NOTIFY_EVENT, listNotifications, sendTestNotification } from "@/lib/api";
import { fmtDateTime } from "@/lib/labels";
import { useSession } from "@/lib/session";
import type { AppNotification } from "@/lib/types";

const SEEN_KEY = "qatra.notifications.seen";
const POLL_MS = 30_000;

function readSeen(): number {
  try {
    return Number(localStorage.getItem(SEEN_KEY) || 0);
  } catch {
    return 0;
  }
}

function writeSeen(id: number) {
  try {
    localStorage.setItem(SEEN_KEY, String(id));
  } catch {
    /* storage blocked: badge just stays */
  }
}

/** In-app notifications: the messages the system sent to this account. */
export default function NotificationBell() {
  const { session, signOut } = useSession();
  const [items, setItems] = useState<AppNotification[]>([]);
  const [open, setOpen] = useState(false);
  const [seen, setSeen] = useState(0);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const box = useRef<HTMLDivElement>(null);

  const load = useCallback(async () => {
    if (!session) return;
    try {
      setItems(await listNotifications(session.token));
      setError(null);
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) signOut();
      else setError(e instanceof Error ? e.message : "Notifications indisponibles.");
    }
  }, [session, signOut]);

  useEffect(() => {
    setSeen(readSeen());
    load();
    const timer = setInterval(load, POLL_MS);
    window.addEventListener(NOTIFY_EVENT, load);
    return () => {
      clearInterval(timer);
      window.removeEventListener(NOTIFY_EVENT, load);
    };
  }, [load]);

  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      if (box.current && !box.current.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  if (!session) return null;
  const unread = items.filter((n) => n.id > seen).length;

  function toggle() {
    const next = !open;
    setOpen(next);
    if (next && items[0]) {
      writeSeen(items[0].id);
      setSeen(items[0].id);
    }
  }

  async function test() {
    if (!session) return;
    setSending(true);
    setError(null);
    try {
      const n = await sendTestNotification(session.token);
      setItems((cur) => [n, ...cur.filter((x) => x.id !== n.id)]);
      writeSeen(n.id);
      setSeen(n.id);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Envoi impossible.");
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="bell" ref={box}>
      <button
        className="btn btn-ghost btn-sm bell-btn"
        onClick={toggle}
        aria-expanded={open}
        aria-label={unread ? `Notifications, ${unread} non lue(s)` : "Notifications"}
      >
        {unread ? <BellRing size={18} /> : <Bell size={18} />}
        {unread > 0 && <span className="bell-badge num">{unread > 9 ? "9+" : unread}</span>}
      </button>

      {open && (
        <div className="bell-panel" role="dialog" aria-label="Notifications">
          <div className="bell-head">
            <strong>Notifications</strong>
            <button className="btn btn-ghost btn-sm" onClick={() => setOpen(false)} aria-label="Fermer">
              <X size={15} />
            </button>
          </div>

          {items.length === 0 ? (
            <div className="empty small">
              <Bell size={22} />
              Aucune notification. Vous en recevrez une quand la recommandation d&apos;une parcelle change.
            </div>
          ) : (
            <ul className="bell-list">
              {items.map((n) => (
                <li key={n.id} className={n.id > seen ? "unread" : undefined}>
                  <span className="bell-meta small">
                    <Smartphone size={13} />
                    {n.plot_id ?? "Qatra"} · {n.channel === "telegram" ? "Telegram" : "Application"} ·{" "}
                    {fmtDateTime(n.created_at)}
                  </span>
                  <span>{n.body}</span>
                </li>
              ))}
            </ul>
          )}

          {error && <p className="small" style={{ color: "var(--clay)", margin: "8px 0 0" }}>{error}</p>}

          <button className="btn btn-sm" onClick={test} disabled={sending} style={{ width: "100%", marginTop: 10 }}>
            {sending ? <LoaderCircle className="spin" size={15} /> : <Send size={15} />}
            Envoyer une notification de test
          </button>
        </div>
      )}
    </div>
  );
}
