"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { CircleAlert, LoaderCircle, Sprout, Users } from "lucide-react";
import Logo from "./Logo";
import { login, register } from "@/lib/api";
import { useSession } from "@/lib/session";
import type { Session } from "@/lib/types";

export default function AuthScreen() {
  const { session, ready, signIn } = useSession();
  const router = useRouter();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [role, setRole] = useState<Session["role"]>("farmer");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (ready && session) router.replace(session.role === "advisor" ? "/advisor" : "/farmer");
  }, [ready, session, router]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const s = mode === "login" ? await login(email, password) : await register(email, password, name, role);
      signIn(s);
      router.replace(s.role === "advisor" ? "/advisor" : "/farmer");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Connexion impossible.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth">
      <section className="auth-art">
        <div className="logo" style={{ position: "absolute", top: 24, left: 24, color: "#fff" }}>
          <Logo size={26} />
          Qatra
        </div>
        <div className="auth-sample num" aria-hidden="true">
          <p style={{ margin: 0 }}>Besoin d&apos;un oranger, jour d&apos;exemple</p>
          <div className="big">
            3,15<small>mm</small>
          </div>
          <p style={{ margin: 0 }}>ETc = Kc 0,75 × ET0 4,2 mm</p>
        </div>
        <h1>L&apos;eau juste, parcelle par parcelle.</h1>
        <p>
          Chaque jour, le besoin en eau de vos agrumes, calculé avec la méthode FAO-56 et expliqué en darija, en
          français et en arabe.
        </p>
      </section>

      <section className="auth-form">
        <div>
          <h2>{mode === "login" ? "Se connecter" : "Créer un compte"}</h2>
          <p className="muted small" style={{ margin: "0 0 20px" }}>
            {mode === "login" ? "Pas encore de compte ? " : "Déjà inscrit ? "}
            <button
              type="button"
              className="btn-link"
              onClick={() => {
                setMode(mode === "login" ? "register" : "login");
                setError(null);
              }}
              style={{ border: 0, background: "none", padding: 0, color: "var(--water)", fontWeight: 600, cursor: "pointer" }}
            >
              {mode === "login" ? "Créer un compte" : "Se connecter"}
            </button>
          </p>

          <form onSubmit={submit}>
            {mode === "register" && (
              <>
                <div className="field">
                  <span className="field-label">Je suis</span>
                  <div className="segmented" role="group" aria-label="Rôle">
                    <button type="button" aria-pressed={role === "farmer"} onClick={() => setRole("farmer")}>
                      <Sprout size={16} /> Agriculteur
                    </button>
                    <button type="button" aria-pressed={role === "advisor"} onClick={() => setRole("advisor")}>
                      <Users size={16} /> Conseiller
                    </button>
                  </div>
                </div>
                <div className="field">
                  <label htmlFor="name">Nom complet</label>
                  <input id="name" className="input" value={name} onChange={(e) => setName(e.target.value)} autoComplete="name" />
                </div>
              </>
            )}
            <div className="field">
              <label htmlFor="email">E-mail</label>
              <input
                id="email"
                className="input"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoComplete="email"
              />
            </div>
            <div className="field">
              <label htmlFor="password">Mot de passe</label>
              <input
                id="password"
                className="input"
                type="password"
                required
                minLength={mode === "register" ? 6 : undefined}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete={mode === "login" ? "current-password" : "new-password"}
              />
            </div>

            {error && (
              <div className="notice error" role="alert" style={{ marginBottom: 14 }}>
                <CircleAlert size={18} />
                <span>{error}</span>
              </div>
            )}

            <button className="btn btn-primary" type="submit" disabled={busy} style={{ width: "100%" }}>
              {busy && <LoaderCircle className="spin" size={18} />}
              {mode === "login" ? "Se connecter" : "Créer mon compte"}
            </button>
          </form>

          <p className="muted small" style={{ marginTop: 24 }}>
            Compte de démonstration : <strong>demo@qatra.local</strong> / <strong>demo-demo</strong>.{" "}
            <Link href="/demo" style={{ color: "var(--water)", fontWeight: 600 }}>
              Voir l&apos;exemple MA-001 sans compte
            </Link>
          </p>
        </div>
      </section>
    </div>
  );
}
