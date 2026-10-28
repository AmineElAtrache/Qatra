"use client";

import { useEffect, useRef, useState } from "react";
import { CircleAlert, LoaderCircle, MessageCircleQuestion, SendHorizontal } from "lucide-react";
import RequireRole from "@/components/ui/RequireRole";
import { ApiError, askQatra, listPlots } from "@/lib/api";
import { useSession } from "@/lib/session";
import type { AskAnswer, Plot, Session } from "@/lib/types";

const SUGGESTIONS = ["Pourquoi cette dose aujourd'hui ?", "Est-ce que je peux traiter ?", "Pourquoi faut-il vérifier ?"];

type Msg = { id: number; from: "me" | "bot"; text?: string; answer?: AskAnswer["answer"] };

export default function AskPage() {
  return <RequireRole role="farmer">{(s) => <Chat session={s} />}</RequireRole>;
}

function Chat({ session }: { session: Session }) {
  const { signOut } = useSession();
  const [plots, setPlots] = useState<Plot[]>([]);
  const [plotId, setPlotId] = useState("");
  const [q, setQ] = useState("");
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const end = useRef<HTMLDivElement>(null);

  useEffect(() => {
    listPlots(session.token)
      .then((list) => {
        setPlots(list);
        setPlotId(list[0]?.public_id ?? "");
      })
      .catch((e) => (e instanceof ApiError && e.status === 401 ? signOut() : setError(e.message)));
  }, [session.token, signOut]);

  useEffect(() => {
    end.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [msgs]);

  async function send(question: string) {
    const text = question.trim();
    if (!text || !plotId || busy) return;
    setQ("");
    setError(null);
    setMsgs((m) => [...m, { id: Date.now(), from: "me", text }]);
    setBusy(true);
    try {
      const out = await askQatra(session.token, plotId, text);
      setMsgs((m) => [...m, { id: Date.now() + 1, from: "bot", answer: out.answer }]);
    } catch (e) {
      if (e instanceof ApiError && e.status === 400) setError("Lancez d'abord le calcul du jour pour cette parcelle.");
      else if (e instanceof ApiError && e.status === 401) signOut();
      else setError(e instanceof Error ? e.message : "Erreur inattendue.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="page" style={{ maxWidth: 760 }}>
      <section className="panel">
        <div className="today-head">
          <h2 style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <MessageCircleQuestion size={20} color="var(--drop)" /> Ask Qatra
          </h2>
          <select
            className="select"
            style={{ width: "auto", minHeight: 36 }}
            value={plotId}
            onChange={(e) => setPlotId(e.target.value)}
            aria-label="Parcelle"
          >
            {plots.length === 0 && <option value="">Aucune parcelle</option>}
            {plots.map((p) => (
              <option key={p.public_id} value={p.public_id}>
                {p.public_id}
              </option>
            ))}
          </select>
        </div>
        <p className="small muted" style={{ marginTop: -6 }}>
          Les réponses partent du dernier calcul de la parcelle. Aucun chiffre n&apos;est ajouté.
        </p>

        <div className="chat" aria-live="polite">
          {msgs.length === 0 && (
            <div className="empty">
              <MessageCircleQuestion size={26} />
              <span className="small">Posez une question sur la recommandation du jour.</span>
            </div>
          )}
          {msgs.map((m) =>
            m.from === "me" ? (
              <div key={m.id} className="bubble me">
                {m.text}
              </div>
            ) : (
              <div key={m.id} className="bubble bot">
                {m.answer?.darija && <p>{m.answer.darija}</p>}
                {m.answer?.fr && <p>{m.answer.fr}</p>}
                {m.answer?.ar && (
                  <p className="ar" dir="rtl" lang="ar">
                    {m.answer.ar}
                  </p>
                )}
              </div>
            ),
          )}
          {busy && (
            <div className="bubble bot">
              <LoaderCircle className="spin" size={16} />
            </div>
          )}
          <div ref={end} />
        </div>

        {error && (
          <div className="notice error" role="alert" style={{ marginTop: 12 }}>
            <CircleAlert size={18} />
            <span>{error}</span>
          </div>
        )}

        <div className="suggestions">
          {SUGGESTIONS.map((s) => (
            <button key={s} className="chip" onClick={() => send(s)} disabled={busy || !plotId}>
              {s}
            </button>
          ))}
        </div>

        <form
          className="composer"
          onSubmit={(e) => {
            e.preventDefault();
            send(q);
          }}
        >
          <input
            className="input"
            placeholder="Votre question, en darija ou en français"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            aria-label="Votre question"
          />
          <button className="btn btn-primary" type="submit" disabled={busy || !q.trim() || !plotId} aria-label="Envoyer">
            <SendHorizontal size={17} />
          </button>
        </form>
      </section>
    </main>
  );
}
