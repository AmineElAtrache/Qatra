"use client";

import { useState } from "react";
import { CircleAlert, Droplets, LoaderCircle, Waves, X } from "lucide-react";
import { METHODS, STAGES } from "@/lib/labels";
import { MAX_PLOT_HA, MIN_PLOT_HA } from "@/lib/geo";
import type { PlotCreate } from "@/lib/types";

type Props = {
  areaHa: number;
  suggestedId: string;
  busy: boolean;
  error: string | null;
  onCancel: () => void;
  onSubmit: (body: Omit<PlotCreate, "coordinates">) => void;
};

export default function PlotForm({ areaHa, suggestedId, busy, error, onCancel, onSubmit }: Props) {
  const [publicId, setPublicId] = useState(suggestedId);
  const [stage, setStage] = useState("");
  const [method, setMethod] = useState("drip");
  const [last, setLast] = useState("");
  const tooBig = areaHa > MAX_PLOT_HA;
  const tooSmall = areaHa < MIN_PLOT_HA;

  return (
    <section className="panel" aria-labelledby="form-title">
      <div className="today-head">
        <h2 id="form-title">Nouvelle parcelle</h2>
        <button className="btn btn-ghost btn-sm" onClick={onCancel} aria-label="Fermer le formulaire">
          <X size={16} />
        </button>
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          onSubmit({
            public_id: publicId.trim(),
            crop: "citrus",
            stage,
            irrigation_method: method,
            area_ha: +areaHa.toFixed(2),
            last_irrigation_on: last || null,
          });
        }}
      >
        <div className="field">
          <label htmlFor="pid">Nom de la parcelle</label>
          <input
            id="pid"
            className="input"
            required
            maxLength={64}
            value={publicId}
            onChange={(e) => setPublicId(e.target.value)}
          />
        </div>

        <div className="field">
          <span className="field-label">Surface dessinée</span>
          <p className="num" style={{ margin: 0, fontWeight: 600 }}>
            {areaHa.toLocaleString("fr-FR", { maximumFractionDigits: 2 })} ha, agrumes
          </p>
        </div>

        <div className="field">
          <label htmlFor="stage">Stade de la culture</label>
          <select id="stage" className="select" required value={stage} onChange={(e) => setStage(e.target.value)}>
            <option value="" disabled>
              Choisir le stade
            </option>
            {STAGES.map((s) => (
              <option key={s.value} value={s.value}>
                {s.label}
              </option>
            ))}
          </select>
        </div>

        <div className="field">
          <span className="field-label">Irrigation</span>
          <div className="segmented" role="group" aria-label="Système d'irrigation">
            {METHODS.map((m) => (
              <button key={m.value} type="button" aria-pressed={method === m.value} onClick={() => setMethod(m.value)}>
                {m.value === "drip" ? <Droplets size={16} /> : <Waves size={16} />}
                {m.label}
              </button>
            ))}
          </div>
        </div>

        <div className="field">
          <label htmlFor="last">Dernière irrigation</label>
          <input
            id="last"
            className="input"
            type="date"
            value={last}
            max={new Date().toISOString().slice(0, 10)}
            onChange={(e) => setLast(e.target.value)}
          />
        </div>

        {(tooBig || tooSmall) && (
          <div className="notice" role="alert" style={{ marginBottom: 14 }}>
            <CircleAlert size={18} />
            <span>
              {tooBig
                ? `Surface de ${Math.round(areaHa).toLocaleString("fr-FR")} ha : c'est une région, pas un verger. Fermez, zoomez jusqu'à voir les arbres et redessinez.`
                : "Surface trop petite : redessinez en plaçant les coins plus loin."}
            </span>
          </div>
        )}

        {error && (
          <div className="notice error" role="alert" style={{ marginBottom: 14 }}>
            <CircleAlert size={18} />
            <span>{error}</span>
          </div>
        )}

        <button className="btn btn-drop" type="submit" disabled={busy || !stage || !publicId.trim() || tooBig || tooSmall} style={{ width: "100%" }}>
          {busy && <LoaderCircle className="spin" size={18} />}
          Enregistrer la parcelle
        </button>
      </form>
    </section>
  );
}
