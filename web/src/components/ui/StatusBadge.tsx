import { CircleAlert, CircleCheck, CircleDashed } from "lucide-react";
import type { Status } from "@/lib/types";

export default function StatusBadge({ status }: { status: Status | null | undefined }) {
  if (status === "show_dose")
    return (
      <span className="badge ok">
        <CircleCheck size={15} strokeWidth={2} /> Dose disponible
      </span>
    );
  if (status === "needs_check")
    return (
      <span className="badge check">
        <CircleAlert size={15} strokeWidth={2} /> À vérifier
      </span>
    );
  return (
    <span className="badge none">
      <CircleDashed size={15} strokeWidth={2} /> Pas encore calculé
    </span>
  );
}
