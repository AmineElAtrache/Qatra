"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import dynamic from "next/dynamic";
import {
  CircleAlert,
  CircleCheck,
  CircleDashed,
  Droplets,
  LayoutList,
  LoaderCircle,
  MapPinned,
  RefreshCw,
  Sprout,
} from "lucide-react";
import RequireRole from "@/components/ui/RequireRole";
import StatusBadge from "@/components/ui/StatusBadge";
import { ApiError, advisorPlots } from "@/lib/api";
import { centroid } from "@/lib/geo";
import { daysSince, fmtMm, isSensitive, stageLabel } from "@/lib/labels";
import { useSession } from "@/lib/session";
import type { AdvisorPlot, Session } from "@/lib/types";

const PlotMap = dynamic(() => import("@/components/map/PlotMap"), {
  ssr: false,
  loading: () => (
    <div className="empty" style={{ height: "100%" }}>
      <LoaderCircle className="spin" size={22} />
    </div>
  ),
});

export default function AdvisorPage() {
  return <RequireRole role="advisor">{(s) => <Dashboard session={s} />}</RequireRole>;
}

/** Visit order: sensitive stage first, then the highest need, then plots without data. */
function visitOrder(a: AdvisorPlot, b: AdvisorPlot) {
  const s = Number(isSensitive(b.stage)) - Number(isSensitive(a.stage));
  if (s) return s;
  return (b.gross_irrigation_mm ?? -1) - (a.gross_irrigation_mm ?? -1);
}

function Dashboard({ session }: { session: Session }) {
  const { signOut } = useSession();
  const [plots, setPlots] = useState<AdvisorPlot[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setPlots(await advisorPlots(session.token));
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) signOut();
      else setError(e instanceof Error ? e.message : "Erreur inattendue.");
    } finally {
      setLoading(false);
    }
  }, [session.token, signOut]);

  useEffect(() => {
    load();
  }, [load]);

  const ordered = useMemo(() => [...plots].sort(visitOrder), [plots]);
  const counts = {
    ok: plots.filter((p) => p.status === "show_dose").length,
    check: plots.filter((p) => p.status === "needs_check").length,
    none: plots.filter((p) => !p.status).length,
  };
  const mapPlots = plots.map((p) => {
    const ring = p.coordinates?.[0] ?? null;
    const point: [number, number] | null =
      p.lat != null && p.lon != null ? [p.lat, p.lon] : ring ? centroid(ring) : null;
    return { id: p.public_id, ring, point: ring ? null : point, status: p.status };
  });
  const located = mapPlots.filter((p) => p.ring || p.point).length;
  const season = plots.map((p) => p.season_water_mm).filter((v): v is number => v != null);

  return (
    <main className="page">
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 16, flexWrap: "wrap" }}>
        <h1 style={{ margin: 0, fontSize: "1.5rem", letterSpacing: "-0.02em", flex: 1 }}>Parcelles suivies</h1>
        <button className="btn btn-sm" onClick={load} disabled={loading}>
          {loading ? <LoaderCircle className="spin" size={15} /> : <RefreshCw size={15} />}
          Actualiser
        </button>
      </div>

      {error && (
        <div className="notice error" role="alert" style={{ marginBottom: 14 }}>
          <CircleAlert size={18} />
          <span>{error}</span>
        </div>
      )}

      <div className="kpis">
        <Kpi icon={<Sprout size={18} />} bg="var(--drop-soft)" fg="var(--drop-ink)" value={plots.length} label="Parcelles" />
        <Kpi icon={<CircleCheck size={18} />} bg="var(--leaf-soft)" fg="var(--leaf)" value={counts.ok} label="Dose disponible" />
        <Kpi icon={<CircleAlert size={18} />} bg="var(--amber-soft)" fg="var(--amber)" value={counts.check} label="À vérifier" />
        <Kpi icon={<CircleDashed size={18} />} bg="var(--sunken)" fg="var(--ink-3)" value={counts.none} label="Sans calcul" />
      </div>

      <div className="workspace">
        <div className="workspace-map">
          <div className="mapbox">
            <PlotMap plots={mapPlots} selected={selected} onSelect={setSelected} />
          </div>
          <div className="legend">
            <span>
              <span className="dot" style={{ background: "#2e7d4f" }} /> Dose disponible
            </span>
            <span>
              <span className="dot" style={{ background: "#a86a12" }} /> À vérifier
            </span>
            <span>
              <span className="dot" style={{ background: "#0b1f3a" }} /> Sans calcul
            </span>
          </div>
          {!loading && plots.length > 0 && located < plots.length && (
            <div className="notice info small" style={{ marginTop: 10 }}>
              <MapPinned size={17} />
              <span>
                {plots.length - located} parcelle(s) sans position : l&apos;API conseiller ne renvoie pas encore leur
                contour.
              </span>
            </div>
          )}
        </div>

        <div>
          <section className="panel">
            <h2 className="panel-title">
              <LayoutList size={18} /> Liste de visites
            </h2>
            <p className="small muted" style={{ marginTop: -6 }}>
              Stade sensible d&apos;abord, puis le besoin le plus haut.
            </p>
            {loading ? (
              <div className="empty">
                <LoaderCircle className="spin" size={22} />
              </div>
            ) : ordered.length === 0 ? (
              <div className="empty">
                <Sprout size={24} />
                <span className="small">Aucune parcelle liée à votre compte pour l&apos;instant.</span>
              </div>
            ) : (
              <div>
                {ordered.map((p, i) => {
                  const age = daysSince(p.ndvi_observed_at);
                  return (
                    <button
                      key={p.public_id}
                      className="visit"
                      onClick={() => setSelected(p.public_id)}
                      style={{
                        width: "100%",
                        border: 0,
                        borderBottom: "1px solid var(--line)",
                        background: p.public_id === selected ? "var(--sunken)" : "transparent",
                        textAlign: "left",
                        cursor: "pointer",
                      }}
                    >
                      <span className="rank num">{i + 1}</span>
                      <span>
                        <span className="title">{p.public_id}</span>
                        <span className="meta">
                          <span>
                            {stageLabel(p.stage)}
                            {isSensitive(p.stage) ? ", sensible" : ""}
                          </span>
                          {p.etc_mm != null && <span className="num">ETc {fmtMm(p.etc_mm)} mm</span>}
                          {p.status === "show_dose" && p.gross_irrigation_mm != null && (
                            <span className="num">Dose {fmtMm(p.gross_irrigation_mm)} mm</span>
                          )}
                          {age !== null && <span className="num">Image {age} j</span>}
                        </span>
                      </span>
                      <StatusBadge status={p.status} />
                    </button>
                  );
                })}
              </div>
            )}
          </section>

          <section className="panel" style={{ marginTop: 14 }}>
            <h2 className="panel-title">
              <Droplets size={18} /> Bilan de saison
            </h2>
            {season.length ? (
              <p className="num" style={{ margin: 0, fontSize: "1.6rem", fontWeight: 700 }}>
                {fmtMm(season.reduce((a, b) => a + b, 0), 0)} mm
                <span className="small muted" style={{ fontWeight: 400, marginLeft: 8 }}>
                  d&apos;eau conseillée sur {season.length} parcelle(s)
                </span>
              </p>
            ) : (
              <p className="small muted" style={{ margin: 0 }}>
                Le total de saison s&apos;affichera quand l&apos;API conseiller renverra le cumul par parcelle.
              </p>
            )}
          </section>
        </div>
      </div>
    </main>
  );
}

function Kpi({ icon, bg, fg, value, label }: { icon: React.ReactNode; bg: string; fg: string; value: number; label: string }) {
  return (
    <div className="kpi">
      <span className="ico" style={{ background: bg, color: fg }}>
        {icon}
      </span>
      <span>
        <strong className="num">{value}</strong>
        <span>{label}</span>
      </span>
    </div>
  );
}
