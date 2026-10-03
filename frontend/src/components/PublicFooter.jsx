import { Link } from "react-router-dom";
import { makeT } from "../lib/i18n";

const LINKS = [
  { to: "/privacy", label: "Privacybeleid" },
  { to: "/terms", label: "Algemene voorwaarden" },
  { to: "/cookies", label: "Cookiebeleid" },
  { to: "/legal", label: "Juridisch & bedrijfsinformatie" },
  { to: "/contact", label: "Contact" },
];

export function PublicFooter({ lang = "en" }) {
  const t = makeT(lang);
  return (
    <footer className="border-t border-slate-200 bg-white" data-testid="public-footer">
      <div className="mx-auto max-w-6xl px-6 py-8">
        <nav className="flex flex-wrap items-center justify-center gap-x-6 gap-y-2 text-sm">
          {LINKS.map((l) => (
            <Link key={l.to} to={l.to} className="text-slate-500 transition-colors hover:text-emerald-600"
              data-testid={`footer-link-${l.to.slice(1)}`}>
              {t(l.label)}
            </Link>
          ))}
        </nav>
        <p className="mt-5 text-center text-sm text-slate-400">
          © {new Date().getFullYear()} Upxero Ordering
        </p>
      </div>
    </footer>
  );
}
