"use client";

import { useState } from "react";
import Link from "next/link";
import { apiBase } from "@/lib/api";

export default function AskPage() {
  const [q, setQ] = useState("Pourquoi la dose est-elle de 4,7 mm ?");
  const [out, setOut] = useState<string>("");

  async function send() {
    setOut("Connectez-vous et appelez POST /plots/MA-001/ask avec un JWT (siège Interface).");
    setOut((prev) => `${prev}\nAPI: ${apiBase()}`);
  }

  return (
    <main>
      <p className="brand">
        Ask Qa<span>tra</span>
      </p>
      <nav className="nav">
        <Link href="/">Accueil</Link>
      </nav>
      <div className="card">
        <textarea value={q} onChange={(e) => setQ(e.target.value)} rows={3} style={{ width: "100%" }} />
        <button type="button" onClick={send} style={{ marginTop: 8 }}>
          Demander
        </button>
        {out && <pre style={{ whiteSpace: "pre-wrap" }}>{out}</pre>}
      </div>
    </main>
  );
}
