import { Link } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { Logo } from "./Logo";
import { LangToggle } from "./LangToggle";
import { makeT } from "../lib/i18n";

export function HomeLogo(props) {
  return (
    <Link to="/" aria-label="Upxero Ordering — home" data-testid="home-logo-link" className="inline-flex">
      <Logo {...props} />
    </Link>
  );
}

export function AuthTopBar({ lang, setLang }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <HomeLogo />
      <LangToggle lang={lang} setLang={setLang} />
    </div>
  );
}

export function BackHome({ lang }) {
  return (
    <Link to="/" className="mt-3 inline-flex items-center gap-1 text-sm font-medium text-slate-500 hover:text-emerald-600" data-testid="back-home-link">
      <ArrowLeft className="h-3.5 w-3.5" /> {makeT(lang)("Terug naar home")}
    </Link>
  );
}
