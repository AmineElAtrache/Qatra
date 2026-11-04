"use client";

import { useEffect, useState } from "react";
import { Check, Copy, Square, Volume2 } from "lucide-react";
import type { Recommendation } from "@/lib/types";

type Lang = "darija" | "fr" | "ar";

const TABS: { key: Lang; label: string }[] = [
  { key: "darija", label: "Darija" },
  { key: "fr", label: "Français" },
  { key: "ar", label: "العربية" },
];

const ARABIC_SCRIPT = /[\u0600-\u06FF]/;

/**
 * Pick a voice by the script of the text, not only by the tab:
 * Darija is often written in Latin letters ("Khass n2aked"), which an Arabic
 * voice cannot read, so Latin text goes to a French voice.
 */
function pickVoice(voices: SpeechSynthesisVoice[], text: string): SpeechSynthesisVoice | null {
  const wanted = ARABIC_SCRIPT.test(text) ? ["ar-MA", "ar"] : ["fr-MA", "fr"];
  for (const tag of wanted) {
    const v = voices.find((x) => x.lang.toLowerCase().startsWith(tag.toLowerCase()));
    if (v) return v;
  }
  return null;
}

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
  const [voices, setVoices] = useState<SpeechSynthesisVoice[]>([]);

  useEffect(() => {
    if (typeof window === "undefined" || !("speechSynthesis" in window)) return;
    setCanSpeak(true);
    const synth = window.speechSynthesis;
    const refresh = () => setVoices(synth.getVoices());
    refresh();
    synth.addEventListener("voiceschanged", refresh);
    return () => {
      synth.removeEventListener("voiceschanged", refresh);
      synth.cancel();
    };
  }, []);

  const text = texts[lang];
  const voice = text ? pickVoice(voices, text) : null;
  // Voices load late on some browsers: only call it missing once the list is known.
  const noVoice = canSpeak && voices.length > 0 && !!text && !voice;

  function speak() {
    if (!text || !canSpeak) return;
    const synth = window.speechSynthesis;
    if (speaking) {
      synth.cancel();
      setSpeaking(false);
      return;
    }
    const u = new SpeechSynthesisUtterance(text);
    if (voice) {
      u.voice = voice;
      u.lang = voice.lang;
    }
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
        <button className="btn btn-sm" onClick={speak} disabled={!text || !canSpeak || noVoice}>
          {speaking ? <Square size={15} /> : <Volume2 size={16} />}
          {speaking ? "Arrêter" : "Écouter"}
        </button>
        <button className="btn btn-ghost btn-sm" onClick={copy} disabled={!text}>
          {copied ? <Check size={15} /> : <Copy size={15} />}
          {copied ? "Copié" : "Copier"}
        </button>
      </div>
      {(noVoice || (!canSpeak && text)) && (
        <p className="small muted" style={{ margin: "6px 0 0" }}>
          Pas de voix pour cette langue sur cet appareil. Le texte reste affiché.
        </p>
      )}
    </div>
  );
}
