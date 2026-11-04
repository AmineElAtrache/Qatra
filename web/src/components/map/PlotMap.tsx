"use client";

import { useEffect, useRef } from "react";
import {
  CircleMarker,
  LayersControl,
  MapContainer,
  Polygon,
  Polyline,
  TileLayer,
  Tooltip,
  useMap,
  useMapEvents,
} from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { LocateFixed } from "lucide-react";
import { toLatLng } from "@/lib/geo";
import type { Status } from "@/lib/types";

export type MapPlot = {
  id: string;
  ring?: number[][] | null; // [lon, lat]
  point?: [number, number] | null; // [lat, lon]
  status?: Status | null;
};

const COLORS: Record<string, string> = { show_dose: "#2e7d4f", needs_check: "#a86a12", none: "#0b1f3a" };
const MOROCCO: [number, number] = [31.8, -7.1];

type Props = {
  plots: MapPlot[];
  selected?: string | null;
  onSelect?: (id: string) => void;
  drawing?: boolean;
  draft?: number[][]; // [lon, lat]
  onAddPoint?: (p: number[]) => void;
};

export default function PlotMap({ plots, selected, onSelect, drawing = false, draft = [], onAddPoint }: Props) {
  return (
    <MapContainer center={MOROCCO} zoom={6} minZoom={5} zoomControl={false} style={{ height: "100%", width: "100%" }}>
      <LayersControl position="topright">
        <LayersControl.BaseLayer checked name="Satellite">
          <TileLayer
            attribution="Imagerie &copy; Esri, Maxar, Earthstar Geographics"
            url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
            maxZoom={19}
          />
        </LayersControl.BaseLayer>
        <LayersControl.BaseLayer name="Plan">
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            maxZoom={19}
          />
        </LayersControl.BaseLayer>
      </LayersControl>

      {plots.map((p) => {
        const color = COLORS[p.status ?? "none"];
        const isSel = p.id === selected;
        const handlers = { click: () => onSelect?.(p.id) };
        if (p.ring && p.ring.length >= 4)
          return (
            <Polygon
              key={p.id}
              positions={toLatLng(p.ring)}
              pathOptions={{
                color: isSel ? "#ff6b00" : color,
                weight: isSel ? 3 : 2,
                fillColor: color,
                fillOpacity: isSel ? 0.35 : 0.22,
              }}
              eventHandlers={drawing ? {} : handlers}
            >
              <Tooltip permanent direction="top" className="plot-label">
                {p.id}
              </Tooltip>
            </Polygon>
          );
        if (p.point)
          return (
            <CircleMarker
              key={p.id}
              center={p.point}
              radius={isSel ? 10 : 8}
              pathOptions={{ color: "#fff", weight: 2, fillColor: color, fillOpacity: 1 }}
              eventHandlers={handlers}
            >
              <Tooltip direction="top">{p.id}</Tooltip>
            </CircleMarker>
          );
        return null;
      })}

      {draft.length > 0 && (
        <>
          <Polyline
            positions={toLatLng(draft.length >= 3 ? [...draft, draft[0]] : draft)}
            pathOptions={{ color: "#ff6b00", weight: 2.5, dashArray: "6 6" }}
          />
          {draft.map(([lon, lat], i) => (
            <CircleMarker
              key={i}
              center={[lat, lon]}
              radius={5}
              pathOptions={{ color: "#fff", weight: 2, fillColor: "#ff6b00", fillOpacity: 1 }}
            />
          ))}
        </>
      )}

      <ClickCapture enabled={drawing} onAddPoint={onAddPoint} />
      <FitSelection plots={plots} selected={selected} />
      <Controls />
    </MapContainer>
  );
}

function ClickCapture({ enabled, onAddPoint }: { enabled: boolean; onAddPoint?: (p: number[]) => void }) {
  const map = useMapEvents({
    click(e) {
      if (enabled) onAddPoint?.([+e.latlng.lng.toFixed(6), +e.latlng.lat.toFixed(6)]);
    },
  });
  useEffect(() => {
    const el = map.getContainer();
    el.style.cursor = enabled ? "crosshair" : "";
    if (enabled) map.doubleClickZoom.disable();
    else map.doubleClickZoom.enable();
  }, [enabled, map]);
  return null;
}

function FitSelection({ plots, selected }: { plots: MapPlot[]; selected?: string | null }) {
  const map = useMap();
  const located = plots.filter((x) => (x.ring && x.ring.length >= 4) || x.point);
  const key = located.map((x) => x.id).join("|");
  useEffect(() => {
    // No selection: frame every located plot once they arrive.
    if (selected || !located.length) return;
    const pts: [number, number][] = located.flatMap((x) => (x.ring && x.ring.length >= 4 ? toLatLng(x.ring) : [x.point!]));
    map.fitBounds(L.latLngBounds(pts), { maxZoom: 16, padding: [50, 50] });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, selected, map]);

  useEffect(() => {
    const p = plots.find((x) => x.id === selected);
    if (!p) return;
    if (p.ring && p.ring.length >= 4) {
      map.flyToBounds(L.latLngBounds(toLatLng(p.ring)), { maxZoom: 17, padding: [40, 40], duration: 0.8 });
    } else if (p.point) {
      map.flyTo(p.point, 15, { duration: 0.8 });
    }
  }, [selected, plots, map]);
  return null;
}

function Controls() {
  const map = useMap();
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (ref.current) {
      L.DomEvent.disableClickPropagation(ref.current);
      L.DomEvent.disableScrollPropagation(ref.current);
    }
  }, []);
  return (
    <div className="leaflet-top leaflet-left" ref={ref}>
      <div className="leaflet-control leaflet-bar" style={{ border: 0 }}>
        <button
          type="button"
          className="btn btn-sm"
          title="Ma position"
          aria-label="Centrer sur ma position"
          style={{ width: 38, padding: 0, boxShadow: "0 2px 8px rgba(11,31,58,.18)" }}
          onClick={() => map.locate({ setView: true, maxZoom: 16 })}
        >
          <LocateFixed size={17} />
        </button>
        <div style={{ display: "grid", marginTop: 6, gap: 4 }}>
          <button
            type="button"
            className="btn btn-sm"
            aria-label="Zoomer"
            style={{ width: 38, padding: 0, boxShadow: "0 2px 8px rgba(11,31,58,.18)" }}
            onClick={() => map.zoomIn()}
          >
            +
          </button>
          <button
            type="button"
            className="btn btn-sm"
            aria-label="Dézoomer"
            style={{ width: 38, padding: 0, boxShadow: "0 2px 8px rgba(11,31,58,.18)" }}
            onClick={() => map.zoomOut()}
          >
            −
          </button>
        </div>
      </div>
    </div>
  );
}
