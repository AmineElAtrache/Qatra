"use client";

import dynamic from "next/dynamic";
import Link from "next/link";

const MoroccoMap = dynamic(() => import("@/components/map/MoroccoMap"), { ssr: false });

export default function FarmerPage() {
  return (
    <main>
      <p className="brand">
        Qa<span>tra</span> · Agriculteur
      </p>
      <nav className="nav">
        <Link href="/">Accueil</Link>
        <Link href="/advisor">Conseiller</Link>
      </nav>
      <div className="card">
        <p>Carte Leaflet (OSM). Dessin de polygone : prochaine tâche Interface.</p>
        <MoroccoMap />
      </div>
      <div className="card">
        <p>
          Formulaire (culture, stade, irrigation, dernière irrigation) →{" "}
          <code>POST /api/v1/plots</code>
        </p>
        <p>
          Carte du jour → <code>POST /api/v1/plots/MA-001/recommendation</code>
        </p>
      </div>
    </main>
  );
}
