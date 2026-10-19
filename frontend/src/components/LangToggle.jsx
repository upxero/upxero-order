export function LangToggle({ lang, setLang, prefix = "lang" }) {
  return (
    <div className="flex items-center gap-1 rounded-lg border border-slate-200 bg-white p-0.5 text-xs font-semibold" data-testid={`${prefix}-toggle`}>
      {["en", "nl"].map((l) => (
        <button key={l} type="button" onClick={() => setLang(l)} aria-pressed={lang === l}
          data-testid={`${prefix}-${l}`}
          className={`rounded-md px-2.5 py-1 transition-colors ${lang === l ? "bg-emerald-600 text-white" : "text-slate-500 hover:text-slate-800"}`}>
          {l.toUpperCase()}
        </button>
      ))}
    </div>
  );
}
