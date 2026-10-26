import Link from "next/link";

export default function AdvisorPage() {
  return (
    <main>
      <p className="brand">
        Qa<span>tra</span> · Conseiller
      </p>
      <nav className="nav">
        <Link href="/">Accueil</Link>
        <Link href="/farmer">Agriculteur</Link>
      </nav>
      <div className="card">
        <p>
          Liste des parcelles : <code>GET /api/v1/advisor/plots</code> (rôle advisor).
        </p>
        <p>Carte colorée par statut + liste de visites — à brancher par le siège Interface.</p>
      </div>
    </main>
  );
}
