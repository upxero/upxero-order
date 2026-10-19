import { useState } from "react";

const KEY = "upxero-lang";
const LEGACY_KEY = "upxero-legal-lang";
const norm = (v) => (v === "nl" || v === "en" ? v : null);

// Public-page language: ?lang= (from email links) > saved choice > English.
export function getPublicLang() {
  try {
    const fromUrl = norm(new URLSearchParams(window.location.search).get("lang"));
    if (fromUrl) {
      localStorage.setItem(KEY, fromUrl);
      return fromUrl;
    }
    return norm(localStorage.getItem(KEY)) || norm(localStorage.getItem(LEGACY_KEY)) || "en";
  } catch {
    return "en";
  }
}

export function usePublicLang() {
  const [lang, setLangState] = useState(getPublicLang);
  const setLang = (l) => {
    setLangState(l);
    try { localStorage.setItem(KEY, l); } catch { /* ignore */ }
  };
  return [lang, setLang];
}
