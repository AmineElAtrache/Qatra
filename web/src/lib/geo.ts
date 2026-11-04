/** Small geometry helpers. Coordinates follow GeoJSON order: [lon, lat]. */

const R = 6_378_137; // WGS84 equatorial radius, metres

/** Geodesic area of a closed ring in hectares (same formula as turf/area). */
export function ringAreaHa(ring: number[][]): number {
  if (ring.length < 4) return 0;
  let total = 0;
  for (let i = 0; i < ring.length - 1; i++) {
    const [lon1, lat1] = ring[i];
    const [lon2, lat2] = ring[i + 1];
    total += toRad(lon2 - lon1) * (2 + Math.sin(toRad(lat1)) + Math.sin(toRad(lat2)));
  }
  return Math.abs((total * R * R) / 2) / 10_000;
}

export function closeRing(points: number[][]): number[][] {
  if (points.length === 0) return points;
  const [f, l] = [points[0], points[points.length - 1]];
  return f[0] === l[0] && f[1] === l[1] ? points : [...points, f];
}

export function centroid(ring: number[][]): [number, number] {
  const pts = ring.slice(0, -1).length ? ring.slice(0, -1) : ring;
  const lon = pts.reduce((s, p) => s + p[0], 0) / pts.length;
  const lat = pts.reduce((s, p) => s + p[1], 0) / pts.length;
  return [lat, lon];
}

/** Outer ring of the API's GeoJSON (first polygon of a MultiPolygon). */
export function ringFromFeature(
  feature?: { geometry?: { type: string; coordinates: unknown } } | null,
): number[][] | null {
  const g = feature?.geometry;
  if (!g) return null;
  if (g.type === "Polygon") return (g.coordinates as number[][][])[0] ?? null;
  if (g.type === "MultiPolygon") return (g.coordinates as number[][][][])[0]?.[0] ?? null;
  return null;
}

/** Above this the drawing is a region, not an orchard. */
export const MAX_PLOT_HA = 200;
export const MIN_PLOT_HA = 0.01;

/** Leaflet wants [lat, lon]. */
export const toLatLng = (ring: number[][]) => ring.map(([lon, lat]) => [lat, lon] as [number, number]);

const toRad = (d: number) => (d * Math.PI) / 180;
