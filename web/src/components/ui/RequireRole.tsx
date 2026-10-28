"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { LoaderCircle } from "lucide-react";
import { useSession } from "@/lib/session";
import type { Session } from "@/lib/types";

/** Sends visitors to /login, and the wrong role to its own home. */
export default function RequireRole({
  role,
  children,
}: {
  role: Session["role"];
  children: (s: Session) => React.ReactNode;
}) {
  const { session, ready } = useSession();
  const router = useRouter();

  useEffect(() => {
    if (!ready) return;
    if (!session) router.replace("/login");
    else if (session.role !== role) router.replace(session.role === "advisor" ? "/advisor" : "/farmer");
  }, [ready, session, role, router]);

  if (!ready || !session || session.role !== role)
    return (
      <div className="empty" style={{ minHeight: "50vh" }}>
        <LoaderCircle className="spin" size={22} />
      </div>
    );
  return <>{children(session)}</>;
}
