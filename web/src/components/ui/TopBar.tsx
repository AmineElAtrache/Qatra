"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { LogOut, MessageCircleQuestion, Map as MapIcon, Users } from "lucide-react";
import Logo from "./Logo";
import { useSession } from "@/lib/session";

const LINKS = [
  { href: "/farmer", label: "Mes parcelles", icon: MapIcon, role: "farmer" },
  { href: "/ask", label: "Ask Qatra", icon: MessageCircleQuestion, role: "farmer" },
  { href: "/advisor", label: "Conseiller", icon: Users, role: "advisor" },
] as const;

export default function TopBar() {
  const path = usePathname();
  const router = useRouter();
  const { session, signOut } = useSession();
  if (path === "/" || path === "/login") return null;

  const links = LINKS.filter((l) => !session || l.role === session.role);

  return (
    <header className="topbar">
      <div className="topbar-inner">
        <Link href="/" className="logo" aria-label="Qatra, accueil">
          <Logo />
          Qatra
        </Link>
        <nav className="tabs" aria-label="Navigation principale">
          {links.map(({ href, label, icon: Icon }) => (
            <Link key={href} href={href} className="tab" aria-current={path.startsWith(href) ? "page" : undefined}>
              <Icon size={17} strokeWidth={1.8} />
              {label}
            </Link>
          ))}
        </nav>
        <div className="account">
          {session ? (
            <>
              <span className="email">{session.email}</span>
              <button
                className="btn btn-ghost btn-sm"
                onClick={() => {
                  signOut();
                  router.push("/login");
                }}
              >
                <LogOut size={16} strokeWidth={1.8} />
                Se déconnecter
              </button>
            </>
          ) : (
            <Link href="/login" className="btn btn-sm">
              Se connecter
            </Link>
          )}
        </div>
      </div>
    </header>
  );
}
