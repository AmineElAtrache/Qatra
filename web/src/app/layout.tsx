import type { Metadata, Viewport } from "next";
import "./globals.css";
import { SessionProvider } from "@/lib/session";
import TopBar from "@/components/ui/TopBar";

export const metadata: Metadata = {
  title: "Qatra",
  description: "Pilotage de l'irrigation à la parcelle — agrumes, Maroc",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: "#0b1f3a",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        <link
          rel="stylesheet"
          href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Arabic:wght@400;500;600&family=Instrument+Sans:wght@400;500;600;700&display=swap"
        />
      </head>
      <body>
        <SessionProvider>
          <TopBar />
          {children}
        </SessionProvider>
      </body>
    </html>
  );
}
