const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function apiHealth(): Promise<{ status: string }> {
  const r = await fetch(`${API}/api/v1/health`, { cache: "no-store" });
  if (!r.ok) throw new Error("API unreachable");
  return r.json();
}

export function apiBase(): string {
  return API;
}
