"use client";

import { MapContainer, TileLayer, Polygon } from "react-leaflet";
import "leaflet/dist/leaflet.css";

/** Sample MA-001 ring — Interface seat will wire drawing tools. */
const MA001: [number, number][] = [
  [33.5731, -7.5898],
  [33.5731, -7.5888],
  [33.5740, -7.5888],
  [33.5740, -7.5898],
];

export default function MoroccoMap() {
  return (
    <div className="leaflet-wrap">
      <MapContainer center={[31.8, -7.1]} zoom={6} style={{ height: "100%", width: "100%" }}>
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <Polygon positions={MA001} pathOptions={{ color: "#ff6b00" }} />
      </MapContainer>
    </div>
  );
}
