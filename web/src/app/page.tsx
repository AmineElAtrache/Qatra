import Link from "next/link";

export default function HomePage() {
  return (
    <main>
      <p className="brand">
        Qa<span>tra</span>
      </p>
      <p>Pilotage de l&apos;irrigation à la parcelle — MVP seats ready to merge.</p>
      <nav className="nav">
        <Link href="/farmer">Agriculteur</Link>
        <Link href="/advisor">Conseiller</Link>
        <Link href="/ask">Ask Qatra</Link>
      </nav>
      <div className="card">
        <strong>Interface seat</strong>
        <p>Leaflet + OpenStreetMap. Pas de Mapbox. Notifications site ou Telegram.</p>
      </div>
      <div className="card">
        <strong>Contrat partagé</strong>
        <p>
          Voir <code>docs/contract.json</code> et <code>SEATS.md</code> à la racine du dépôt.
        </p>
      </div>
    </main>
  );
}
