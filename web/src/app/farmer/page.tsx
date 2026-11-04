"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import dynamic from "next/dynamic";
import {
  CircleAlert,
  Check,
  LoaderCircle,
  PenLine,
  RefreshCw,
  Sprout,
  Undo2,
  X,
} from "lucide-react";
import RequireRole from "@/components/ui/RequireRole";
import StatusBadge from "@/components/ui/StatusBadge";
import TodayCard from "@/components/farmer/TodayCard";
import PlotForm from "@/components/farmer/PlotForm";
import { ApiError, createPlot, listPlots, listRecommendations, runRecommendation } from "@/lib/api";
import { closeRing, ringAreaHa } from "@/lib/geo";
import { fmtDate, fmtMm, methodLabel, stageLabel } from "@/lib/labels";
import { loadRings, saveRing, useSession } from "@/lib/session";
import type { Plot, Recommendation, Session } from "@/lib/types";

const PlotMap = dynamic(() => import("@/components/map/PlotMap"), {
  ssr: false,
  loading: () => (
    <div className="empty" style={{ height: "100%" }}>
      <LoaderCircle className="spin" size={22} />
    </div>
  ),
});

type HistoryRow = { id: number; status: string; created_at: string; payload: Recommendation };

export default function FarmerPage() {
  return <RequireRole role="farmer">{(s) => <Workspace session={s} />}</RequireRole>;
}

function Workspace({ session }: { session: Session }) {
  const { signOut } = useSession();
  const [plots, setPlots] = useState<Plot[]>([]);
  const [rings, setRings] = useState<Record<string, number[][]>>({});
  const [history, setHistory] = useState<Record<string, HistoryRow[]>>({});
  const [selected, setSelected] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);

  const [drawing, setDrawing] = useState(false);
  const [draft, setDraft] = useState<number[][]>([]);
  const [formRing, setFormRing] = useState<number[][] | null>(null);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const handleError = useCallback(
    (e: unknown, set: (m: string) => void) => {
      if (e instanceof ApiError && e.status === 401) {
        signOut();
        return;
      }
      set(e instanceof Error ? e.message : "Erreur inattendue.");
    },
    [signOut],
  );

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const list = await listPlots(session.token);
      setPlots(list);
      setRings(loadRings());
      const entries = await Promise.all(
        list.map(async (p) => [p.public_id, await listRecommendations(session.token, p.public_id).catch(() => [])] as const),
      );
      setHistory(Object.fromEntries(entries));
      setSelected((cur) => cur ?? list[0]?.public_id ?? null);
    } catch (e) {
      handleError(e, setError);
    } finally {
      setLoading(false);
    }
  }, [session.token, handleError]);

  useEffect(() => {
    load();
  }, [load]);

  const mapPlots = useMemo(
    () =>
      plots.map((p) => ({
        id: p.public_id,
        ring: p.coordinates?.[0] ?? rings[p.public_id] ?? null,
        status: (history[p.public_id]?.[0]?.payload.status ?? null) as Recommendation["status"] | null,
      })),
    [plots, rings, history],
  );

  const current = plots.find((p) => p.public_id === selected) ?? null;
  const rows = selected ? history[selected] ?? [] : [];
  const latest = rows[0]?.payload ?? null;

  async function run() {
    if (!current) return;
    setRunning(true);
    setError(null);
    try {
      const out = await runRecommendation(session.token, current.public_id);
      const row: HistoryRow = {
        id: out.id,
        status: out.recommendation.status,
        created_at: new Date().toISOString(),
        payload: out.recommendation,
      };
      setHistory((h) => ({ ...h, [current.public_id]: [row, ...(h[current.public_id] ?? [])] }));
    } catch (e) {
      handleError(e, setError);
    } finally {
      setRunning(false);
    }
  }

  function finishDrawing() {
    if (draft.length < 3) return;
    setFormRing(closeRing(draft));
    setDrawing(false);
    setFormError(null);
  }

  function cancelDrawing() {
    setDrawing(false);
    setDraft([]);
    setFormRing(null);
  }

  async function save(body: Parameters<typeof createPlot>[1]) {
    if (!formRing) return;
    setSaving(true);
    setFormError(null);
    try {
      const plot = await createPlot(session.token, { ...body, coordinates: [formRing] });
      saveRing(plot.public_id, formRing);
      setRings((r) => ({ ...r, [plot.public_id]: formRing }));
      setPlots((p) => [...p, plot]);
      setSelected(plot.public_id);
      setDraft([]);
      setFormRing(null);
    } catch (e) {
      handleError(e, setFormError);
    } finally {
      setSaving(false);
    }
  }

  const suggestedId = `MA-${String(plots.length + 1).padStart(3, "0")}`;

  return (
    <main className="page">
      <div className="workspace">
        <div className="workspace-map">
          <div className="mapbox">
            <PlotMap
              plots={mapPlots}
              selected={selected}
              onSelect={(id) => !drawing && setSelected(id)}
              drawing={drawing}
              draft={formRing ? formRing.slice(0, -1) : draft}
              onAddPoint={(p) => setDraft((d) => [...d, p])}
            />
            <div className="map-toolbar">
              {drawing ? (
                <>
                  <span className="hint">
                    {draft.length < 3
                      ? `Touchez chaque coin de la parcelle (${draft.length} sur 3 minimum)`
                      : `${draft.length} coins, ${fmtMm(ringAreaHa(closeRing(draft)))} ha`}
                  </span>
                  <button className="btn btn-sm" onClick={() => setDraft((d) => d.slice(0, -1))} disabled={!draft.length}>
                    <Undo2 size={15} /> Annuler
                  </button>
                  <button className="btn btn-ghost btn-sm" onClick={cancelDrawing} aria-label="Abandonner le dessin">
                    <X size={15} />
                  </button>
                  <button className="btn btn-drop btn-sm" onClick={finishDrawing} disabled={draft.length < 3}>
                    <Check size={15} /> Terminer
                  </button>
                </>
              ) : (
                <>
                  <span className="hint">
                    {formRing ? "Complétez le formulaire pour enregistrer." : "Zoomez sur votre verger puis dessinez son contour."}
                  </span>
                  {!formRing && (
                    <button className="btn btn-primary btn-sm" onClick={() => setDrawing(true)}>
                      <PenLine size={15} /> Dessiner une parcelle
                    </button>
                  )}
                </>
              )}
            </div>
          </div>
        </div>

        <div>
          {formRing ? (
            <PlotForm
              areaHa={ringAreaHa(formRing)}
              suggestedId={suggestedId}
              busy={saving}
              error={formError}
              onCancel={cancelDrawing}
              onSubmit={save}
            />
          ) : (
            <>
              {error && (
                <div className="notice error" role="alert" style={{ marginBottom: 14 }}>
                  <CircleAlert size={18} />
                  <span>{error}</span>
                </div>
              )}

              <section className="panel">
                <h2 className="panel-title">
                  <Sprout size={18} /> Mes parcelles
                </h2>
                {loading ? (
                  <div className="empty">
                    <LoaderCircle className="spin" size={22} />
                  </div>
                ) : plots.length === 0 ? (
                  <div className="empty">
                    <PenLine size={26} />
                    <strong>Aucune parcelle pour l&apos;instant</strong>
                    <span className="small">Dessinez le contour de votre verger sur la carte pour commencer.</span>
                  </div>
                ) : (
                  <div className="plot-list">
                    {plots.map((p) => (
                      <button
                        key={p.public_id}
                        className="plot-row"
                        aria-pressed={p.public_id === selected}
                        onClick={() => setSelected(p.public_id)}
                      >
                        <span className="plot-icon">
                          <Sprout size={17} />
                        </span>
                        <span>
                          <span className="id">{p.public_id}</span>
                          <span className="small muted" style={{ display: "block" }}>
                            {stageLabel(p.stage)}, {methodLabel(p.irrigation_method).toLowerCase()},{" "}
                            <span className="num">{fmtMm(p.area_ha)} ha</span>
                          </span>
                        </span>
                        <StatusBadge status={(history[p.public_id]?.[0]?.payload.status ?? null) as never} />
                      </button>
                    ))}
                  </div>
                )}
              </section>

              {current && (
                <>
                  <div className="panel" style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
                    <span style={{ flex: 1, minWidth: 180 }}>
                      <strong>{current.public_id}</strong>
                      <span className="small muted" style={{ display: "block" }}>
                        {rows[0] ? `Dernier calcul ${fmtDate(rows[0].created_at)}` : "Jamais calculée"}
                      </span>
                    </span>
                    <button className="btn btn-drop" onClick={run} disabled={running}>
                      {running ? <LoaderCircle className="spin" size={17} /> : <RefreshCw size={17} />}
                      Calculer aujourd&apos;hui
                    </button>
                  </div>

                  {latest ? (
                    <div style={{ marginTop: 14 }}>
                      <TodayCard rec={latest} />
                    </div>
                  ) : (
                    <div className="panel empty">
                      <RefreshCw size={24} />
                      <span className="small">Lancez le calcul pour obtenir la recommandation du jour.</span>
                    </div>
                  )}

                  {rows.length > 1 && <History rows={rows} />}
                </>
              )}
            </>
          )}
        </div>
      </div>
    </main>
  );
}

function History({ rows }: { rows: HistoryRow[] }) {
  const last = rows.slice(0, 14).reverse();
  const max = Math.max(...last.map((r) => r.payload.display_dose ?? r.payload.gross_irrigation_mm ?? 0), 1);
  return (
    <section className="panel" style={{ marginTop: 14 }}>
      <h2 className="panel-title">Historique des doses</h2>
      <div className="history" role="img" aria-label="Doses des derniers calculs">
        {last.map((r) => {
          const dose = r.payload.status === "show_dose" ? r.payload.display_dose ?? r.payload.gross_irrigation_mm : null;
          return (
            <span
              key={r.id}
              className={dose == null ? "check" : ""}
              style={{ height: dose == null ? "100%" : `${Math.max((dose / max) * 100, 6)}%` }}
              title={`${fmtDate(r.created_at)} : ${dose == null ? "à vérifier" : `${fmtMm(dose)} mm`}`}
            />
          );
        })}
      </div>
      <div className="legend">
        <span>
          <span className="dot" style={{ background: "var(--drop)" }} /> Dose affichée
        </span>
        <span>
          <span className="dot" style={{ background: "#e6c27a" }} /> À vérifier
        </span>
      </div>
    </section>
  );
}
