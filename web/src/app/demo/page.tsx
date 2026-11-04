"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { Info, LoaderCircle } from "lucide-react";
import TodayCard from "@/components/farmer/TodayCard";
import { CONTRACT_SAMPLE, MA001_RING } from "@/lib/sample";

const PlotMap = dynamic(() => import("@/components/map/PlotMap"), {
  ssr: false,
  loading: () => (
    <div className="empty" style={{ height: "100%" }}>
      <LoaderCircle className="spin" size={22} />
    </div>
  ),
});

/** Public preview of the result card, fed by docs/contract.json. Clearly labelled as an example. */
export default function DemoPage() {
  return (
    <main className="page">
      <div className="notice info" style={{ marginBottom: 16 }}>
        <Info size={18} />
        <span>
          Exemple du contrat partagé (MA-001), pas une mesure du jour.{" "}
          <Link href="/login" style={{ fontWeight: 600, textDecoration: "underline" }}>
            Connectez-vous
          </Link>{" "}
          pour calculer vos parcelles.
        </span>
      </div>
      <div className="workspace">
        <div className="workspace-map">
          <div className="mapbox">
            <PlotMap plots={[{ id: "MA-001", ring: MA001_RING, status: "show_dose" }]} selected="MA-001" />
          </div>
        </div>
        <TodayCard rec={CONTRACT_SAMPLE} sample />
      </div>
    </main>
  );
}
