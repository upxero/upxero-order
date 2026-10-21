import { Link } from "react-router-dom";
import { Sparkles } from "lucide-react";
import { useT } from "../context/I18nContext";

export function UpgradeNotice({ title, text, testid = "upgrade-notice" }) {
  const t = useT();
  return (
    <div className="flex flex-col gap-3 rounded-xl border border-emerald-200 bg-emerald-50 p-4 sm:flex-row sm:items-center sm:justify-between" data-testid={testid}>
      <div className="flex items-start gap-3">
        <Sparkles className="mt-0.5 h-5 w-5 shrink-0 text-emerald-600" />
        <div>
          <p className="text-sm font-semibold text-emerald-900">{t(title)}</p>
          {text && <p className="text-sm text-emerald-800">{text}</p>}
        </div>
      </div>
      <Link to="/dashboard/abonnement" data-testid={`${testid}-button`}
        className="inline-flex shrink-0 items-center justify-center rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-emerald-700">
        {t("Upgrade naar Pro")}
      </Link>
    </div>
  );
}

export function UsageMeter({ used, limit, label, testid }) {
  const pct = Math.min(100, Math.round((used / limit) * 100));
  return (
    <div data-testid={testid}>
      <div className="flex items-baseline justify-between text-sm">
        <span className="font-medium text-slate-700">{label}</span>
        <span className="font-semibold text-slate-900">{used} / {limit}</span>
      </div>
      <div className="mt-1.5 h-2 overflow-hidden rounded-full bg-slate-100">
        <div className={`h-full rounded-full ${pct >= 100 ? "bg-rose-500" : pct >= 80 ? "bg-amber-500" : "bg-emerald-500"}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}
