import { useState } from "react";
import { Link } from "react-router-dom";
import { Logo } from "../../components/Logo";
import { PublicFooter } from "../../components/PublicFooter";
import { makeT } from "../../lib/i18n";
import { LEGAL, COMPANY } from "../../lib/legalContent";

const STORE_KEY = "upxero-legal-lang";

function Section({ s }) {
  return (
    <section className="mt-8">
      <h2 className="font-heading text-lg font-semibold text-slate-900">{s.h}</h2>
      {s.p?.map((para, i) => (
        <p key={i} className="mt-2 text-sm leading-relaxed text-slate-600">{para}</p>
      ))}
      {s.ul && (
        <ul className="mt-3 list-disc space-y-1 pl-5 text-sm leading-relaxed text-slate-600">
          {s.ul.map((li, i) => <li key={i}>{li}</li>)}
        </ul>
      )}
      {s.sub?.map((sub, i) => (
        <div key={i} className="mt-4">
          <h3 className="text-sm font-semibold text-slate-800">{sub.h}</h3>
          {sub.p?.map((para, j) => <p key={j} className="mt-1.5 text-sm leading-relaxed text-slate-600">{para}</p>)}
          {sub.ul && (
            <ul className="mt-2 list-disc space-y-1 pl-5 text-sm leading-relaxed text-slate-600">
              {sub.ul.map((li, j) => <li key={j}>{li}</li>)}
            </ul>
          )}
        </div>
      ))}
    </section>
  );
}

function CompanyBlock() {
  const row = (label, value, href) => (
    <div className="flex flex-col gap-0.5 border-b border-slate-100 py-3 sm:flex-row sm:items-center sm:justify-between">
      <span className="text-sm font-medium text-slate-500">{label}</span>
      {href ? (
        <a href={href} className="text-sm font-semibold text-emerald-600 hover:underline">{value}</a>
      ) : (
        <span className="text-sm font-semibold text-slate-900">{value}</span>
      )}
    </div>
  );
  return (
    <div className="mt-8 rounded-xl border border-slate-200 bg-slate-50 p-5" data-testid="company-info-block">
      <p className="font-heading text-base font-bold text-slate-900">{COMPANY.name}</p>
      <p className="mt-1 text-sm text-slate-600">
        {COMPANY.addressLines.join(", ")} · {COMPANY.country}
      </p>
      <div className="mt-4">
        {row("Commercial Registry code", COMPANY.registry)}
        {row("VAT number", COMPANY.vat)}
        {row("Email", COMPANY.email, `mailto:${COMPANY.email}`)}
        {row("Website", COMPANY.website, COMPANY.website)}
        {row("Ordering", COMPANY.ordering, COMPANY.ordering)}
      </div>
    </div>
  );
}

export default function LegalPage({ page }) {
  const [lang, setLang] = useState(() => {
    try { return localStorage.getItem(STORE_KEY) === "nl" ? "nl" : "en"; } catch { return "en"; }
  });
  const t = makeT(lang);
  const setLanguage = (l) => {
    setLang(l);
    try { localStorage.setItem(STORE_KEY, l); } catch { /* ignore */ }
  };

  const content = LEGAL[page][lang] || LEGAL[page].en;

  return (
    <div className="flex min-h-screen flex-col bg-white" data-testid={`legal-page-${page}`}>
      <header className="border-b border-slate-200">
        <div className="mx-auto flex max-w-3xl items-center justify-between px-6 py-4">
          <Link to="/" data-testid="legal-home-link"><Logo /></Link>
          <div className="flex items-center gap-1 rounded-lg border border-slate-200 p-0.5 text-xs font-semibold" data-testid="legal-lang-toggle">
            {["en", "nl"].map((l) => (
              <button key={l} onClick={() => setLanguage(l)}
                data-testid={`legal-lang-${l}`}
                className={`rounded-md px-2.5 py-1 transition-colors ${lang === l ? "bg-emerald-600 text-white" : "text-slate-500 hover:text-slate-800"}`}>
                {l.toUpperCase()}
              </button>
            ))}
          </div>
        </div>
      </header>

      <main className="mx-auto w-full max-w-3xl flex-1 px-6 py-10 sm:py-14">
        <Link to="/" className="text-sm font-medium text-emerald-600 hover:underline" data-testid="legal-back-home">
          ← {t("Terug naar home")}
        </Link>
        <h1 className="mt-4 font-heading text-3xl font-bold tracking-tight text-slate-900 sm:text-4xl" data-testid="legal-title">
          {content.title}
        </h1>
        {content.updated && <p className="mt-2 text-sm text-slate-400">{content.updated}</p>}

        {content.sections.map((s, i) => <Section key={i} s={s} />)}

        {page === "legal" && <CompanyBlock />}

        {page === "contact" && (
          <div className="mt-6" data-testid="contact-email-block">
            <a href={`mailto:${COMPANY.email}`}
              className="inline-flex items-center rounded-lg bg-emerald-600 px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-emerald-700"
              data-testid="contact-mailto">
              {COMPANY.email}
            </a>
          </div>
        )}
      </main>

      <PublicFooter lang={lang} />
    </div>
  );
}
