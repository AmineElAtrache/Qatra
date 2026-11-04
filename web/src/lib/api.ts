import type { AdvisorPlot, AskAnswer, Plot, PlotCreate, Recommendation, Session } from "./types";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export function apiBase(): string {
  return API;
}

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

async function call<T>(path: string, init: RequestInit = {}, token?: string): Promise<T> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) headers.Authorization = `Bearer ${token}`;
  let r: Response;
  try {
    r = await fetch(`${API}/api/v1${path}`, { ...init, headers, cache: "no-store" });
  } catch {
    throw new ApiError(0, "L'API ne répond pas. Vérifiez que le backend tourne sur " + API + ".");
  }
  if (!r.ok) {
    let detail = r.statusText;
    try {
      const body = await r.json();
      if (typeof body?.detail === "string") detail = body.detail;
    } catch {
      /* body not JSON */
    }
    throw new ApiError(r.status, detail);
  }
  return r.json() as Promise<T>;
}

export function apiHealth(): Promise<{ status: string }> {
  return call("/health");
}

type TokenOut = { access_token: string; role: Session["role"] };

export async function login(email: string, password: string): Promise<Session> {
  const t = await call<TokenOut>("/auth/login", { method: "POST", body: JSON.stringify({ email, password }) });
  return { token: t.access_token, role: t.role, email };
}

export async function register(
  email: string,
  password: string,
  full_name: string,
  role: Session["role"],
): Promise<Session> {
  const t = await call<TokenOut>("/auth/register", {
    method: "POST",
    body: JSON.stringify({ email, password, full_name, role }),
  });
  return { token: t.access_token, role: t.role, email };
}

export const listPlots = (token: string) => call<Plot[]>("/plots", {}, token);

export const createPlot = (token: string, body: PlotCreate) =>
  call<Plot>("/plots", { method: "POST", body: JSON.stringify(body) }, token);

export const runRecommendation = (token: string, plotId: string) =>
  call<{ id: number; recommendation: Recommendation }>(
    `/plots/${encodeURIComponent(plotId)}/recommendation`,
    { method: "POST" },
    token,
  );

export const listRecommendations = (token: string, plotId: string) =>
  call<{ id: number; status: string; created_at: string; payload: Recommendation }[]>(
    `/plots/${encodeURIComponent(plotId)}/recommendations`,
    {},
    token,
  );

export const askQatra = (token: string, plotId: string, question: string) =>
  call<AskAnswer>(`/plots/${encodeURIComponent(plotId)}/ask`, {
    method: "POST",
    body: JSON.stringify({ question }),
  }, token);

export const advisorPlots = (token: string) => call<AdvisorPlot[]>("/advisor/plots", {}, token);
