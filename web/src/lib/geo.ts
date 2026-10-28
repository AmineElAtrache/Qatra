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

/** Leaflet wants [lat, lon]. */
export const toLatLng = (ring: number[][]) => ring.map(([lon, lat]) => [lat, lon] as [number, number]);

const toRad = (d: number) => (d * Math.PI) / 180;
