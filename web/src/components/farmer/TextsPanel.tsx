"use client";

import { useEffect, useState } from "react";
import { Check, Copy, Square, Volume2 } from "lucide-react";
import type { Recommendation } from "@/lib/types";

type Lang = "darija" | "fr" | "ar";

const TABS: { key: Lang; label: string; speech: string }[] = [
  { key: "darija", label: "Darija", speech: "ar-MA" },
  { key: "fr", label: "Français", speech: "fr-FR" },
  { key: "ar", label: "العربية", speech: "ar-SA" },
];

export function textsOf(rec: Recommendation): Record<Lang, string | undefined> {
  return {
    fr: rec.texts?.fr ?? rec.text_fr,
    darija: rec.texts?.darija ?? rec.text_ary,
    ar: rec.texts?.ar ?? rec.text_ar,
  };
}

/** Three languages from the Explanation seat. The text is always shown; voice is an extra. */
export default function TextsPanel({ rec }: { rec: Recommendation }) {
  const texts = textsOf(rec);
  const [lang, setLang] = useState<Lang>("darija");
  const [speaking, setSpeaking] = useState(false);
  const [copied, setCopied] = useState(false);
  const [canSpeak, setCanSpeak] = useState(false);

  useEffect(() => {
    setCanSpeak(typeof window !== "undefined" && "speechSynthesis" in window);
    return () => {
      if (typeof window !== "undefined" && "speechSynthesis" in window) window.speechSynthesis.cancel();
    };
  }, []);

  const text = texts[lang];
  const tab = TABS.find((t) => t.key === lang)!;

  function speak() {
    if (!text || !canSpeak) return;
    const synth = window.speechSynthesis;
    if (speaking) {
      synth.cancel();
      setSpeaking(false);
      return;
    }
    const u = new SpeechSynthesisUtterance(text);
    u.lang = tab.speech;
    const voice = synth.getVoices().find((v) => v.lang.startsWith(tab.speech.slice(0, 2)));
    if (voice) u.voice = voice;
    u.onend = () => setSpeaking(false);
    u.onerror = () => setSpeaking(false);
    synth.speak(u);
    setSpeaking(true);
  }

  async function copy() {
    if (!text) return;
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      /* clipboard blocked */
    }
  }

  return (
    <div style={{ marginTop: 18 }}>
      <div className="segmented" role="tablist" aria-label="Langue de l'explication">
        {TABS.map((t) => (
          <button
            key={t.key}
            role="tab"
            aria-selected={lang === t.key}
            aria-pressed={lang === t.key}
            onClick={() => {
              if (speaking) window.speechSynthesis.cancel();
              setSpeaking(false);
              setLang(t.key);
            }}
            className={t.key === "ar" ? "ar" : undefined}
          >
            {t.label}
          </button>
        ))}
      </div>
      <p className={`texts-body ${lang === "ar" ? "ar" : ""}`} lang={lang === "fr" ? "fr" : "ar"} dir={lang === "ar" ? "rtl" : "ltr"}>
        {text || <span className="muted">Pas encore de texte dans cette langue.</span>}
      </p>
      <div className="texts-actions">
        <button className="btn btn-sm" onClick={speak} disabled={!text || !canSpeak}>
          {speaking ? <Square size={15} /> : <Volume2 size={16} />}
          {speaking ? "Arrêter" : "Écouter"}
        </button>
        <button className="btn btn-ghost btn-sm" onClick={copy} disabled={!text}>
          {copied ? <Check size={15} /> : <Copy size={15} />}
          {copied ? "Copié" : "Copier"}
        </button>
      </div>
    </div>
  );
}
