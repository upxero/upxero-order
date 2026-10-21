import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Check, ExternalLink, Gift, Loader2, Minus, Sparkles } from "lucide-react";
import { toast } from "sonner";
import api, { apiError } from "../../lib/api";
import { useBilling } from "../../lib/useBilling";
import { useI18n } from "../../context/I18nContext";
import { UsageMeter } from "../../components/UpgradeNotice";
import { Button } from "../../components/ui/button";
import { Card } from "../../components/ui/card";

const ROWS = [
  ["Actieve menuproducten", "Max. 20", "Onbeperkt*"],
  ["Nieuwe bestellingen per maand", "Max. 30", "Onbeperkt*"],
  ["Afhalen", true, true],
  ["Bezorging en bezorgzones", false, true],
  ["Personeelsaccounts", false, true],
  ["Automatische e-mailmeldingen", false, true],
];
const PLAN_LABEL = { free: "Free", pro: "Pro", legacy: "Gratis Pro" };
const STATUS_LABEL = { active: "Actief", trialing: "Proefperiode", past_due: "Betaling achterstallig", canceling: "Wordt opgezegd", canceled: "Opgezegd", expired: "Verlopen" };

function Cell({ v }) {
  const { t } = useI18n();
  if (v === true) return <Check className="mx-auto h-4 w-4 text-emerald-600" />;
  if (v === false) return <Minus className="mx-auto h-4 w-4 text-slate-300" />;
  return <span>{t(v)}</span>;
}

function Comparison() {
  const { t } = useI18n();
  return (
    <Card className="overflow-x-auto rounded-xl border-slate-200 p-5 shadow-sm" data-testid="plan-comparison">
      <h2 className="font-heading text-lg font-semibold text-slate-900">{t("Free vs. Pro")}</h2>
      <table className="mt-3 w-full text-sm">
        <thead><tr className="text-left text-slate-500"><th className="py-2 font-medium" /><th className="whitespace-nowrap py-2 text-center font-medium">Free · $0</th><th className="whitespace-nowrap py-2 text-center font-medium">Pro · $9.99</th></tr></thead>
        <tbody className="divide-y divide-slate-100">
          {ROWS.map(([label, f, p]) => (
            <tr key={label}><td className="py-2.5 pr-3 text-slate-700">{t(label)}</td><td className="py-2.5 text-center text-slate-600"><Cell v={f} /></td><td className="py-2.5 text-center font-medium text-slate-900"><Cell v={p} /></td></tr>
          ))}
        </tbody>
      </table>
      <p className="mt-3 text-xs text-slate-400">{t("* Binnen redelijk gebruik.")}</p>
    </Card>
  );
}

function PlanActions({ billing }) {
  const { t, lang } = useI18n();
  const [busy, setBusy] = useState(false);
  const fmt = (iso) => new Date(iso).toLocaleDateString(lang === "nl" ? "nl-BE" : "en-GB", { day: "numeric", month: "long", year: "numeric" });
  const upgrade = async () => {
    setBusy(true);
    try {
      const { data } = await api.post("/billing/checkout");
      window.location.assign(data.purchaseUrl);
    } catch (e) { toast.error(t(apiError(e))); setBusy(false); }
  };
  if (billing.plan === "legacy") {
    return (
      <div className="flex items-start gap-3 rounded-lg bg-emerald-50 p-4 text-sm text-emerald-900" data-testid="complimentary-info">
        <Gift className="mt-0.5 h-5 w-5 shrink-0 text-emerald-600" />
        <div><p className="font-semibold">{t("Volledige Pro-functionaliteit")}</p><p>{t("Geen maandelijkse kosten. Toegang aangeboden door Upxero.")}</p></div>
      </div>
    );
  }
  if (billing.plan === "pro") {
    return (
      <div className="space-y-3" data-testid="pro-info">
        <p className="text-sm text-slate-600">
          {t("Status")}: <span className="font-semibold text-slate-900" data-testid="subscription-status">{t(STATUS_LABEL[billing.status] || billing.status)}</span>
          {billing.renewalPeriodEnd && <> · {t(billing.cancelAtPeriodEnd ? "Toegang tot" : "Volgende betaling")}: <span className="font-semibold text-slate-900" data-testid="subscription-renewal">{fmt(billing.renewalPeriodEnd)}</span></>}
        </p>
        {billing.manageUrl && (
          <a href={billing.manageUrl} target="_blank" rel="noreferrer" data-testid="manage-subscription-button"
            className="inline-flex items-center gap-2 rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50">
            {t("Abonnement beheren")} <ExternalLink className="h-4 w-4" />
          </a>
        )}
      </div>
    );
  }
  if (!billing.checkoutAvailable) {
    return <p className="rounded-lg bg-slate-50 p-3 text-sm text-slate-600" data-testid="checkout-unavailable">{t("Upgraden is momenteel nog niet beschikbaar. Probeer het later opnieuw.")}</p>;
  }
  return (
    <Button onClick={upgrade} disabled={busy} className="bg-emerald-600 hover:bg-emerald-700" data-testid="upgrade-button">
      {busy ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Sparkles className="mr-2 h-4 w-4" />} {t("Upgrade naar Pro — $9.99/maand")}
    </Button>
  );
}

export default function Subscription() {
  const { t } = useI18n();
  const { billing, reload } = useBilling();
  const [params, setParams] = useSearchParams();
  const synced = useRef(false);

  useEffect(() => {
    if (params.get("checkout") !== "done" || synced.current) { return; }
    synced.current = true;
    toast.info(t("We controleren je betaling bij Whop…"));
    api.post("/billing/sync").catch(() => {}).finally(() => { reload(); setParams({}, { replace: true }); });
  }, [params, setParams, reload, t]);

  if (!billing) return <div className="grid place-items-center py-20"><Loader2 className="h-6 w-6 animate-spin text-emerald-600" /></div>;
  const u = billing.usage;
  return (
    <div className="space-y-6" data-testid="subscription-page">
      <div>
        <h1 className="font-heading text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl">{t("Abonnement")}</h1>
        <p className="mt-1 text-sm text-slate-500">{t("Je huidige plan, gebruik en upgrade-opties.")}</p>
      </div>
      <Card className="space-y-5 rounded-xl border-slate-200 p-5 shadow-sm" data-testid="current-plan-card">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <p className="font-heading text-xl font-bold text-slate-900" data-testid="current-plan">{t(PLAN_LABEL[billing.plan])}</p>
          <p className="text-sm text-slate-500" data-testid="current-price">{billing.plan === "pro" ? "$9.99 / " + t("maand") : billing.plan === "legacy" ? t("Gratis") : "$0 / " + t("maand")}</p>
        </div>
        <PlanActions billing={billing} />
        <div className="grid gap-4 sm:grid-cols-2">
          {u.monthlyOrderLimit ? <UsageMeter used={u.ordersThisMonth} limit={u.monthlyOrderLimit} label={t("Bestellingen deze maand")} testid="usage-orders" />
            : <p className="text-sm text-slate-600" data-testid="usage-orders">{t("Bestellingen deze maand")}: <b>{u.ordersThisMonth}</b></p>}
          {u.activeProductLimit ? <UsageMeter used={u.activeProducts} limit={u.activeProductLimit} label={t("Actieve menuproducten")} testid="usage-products" />
            : <p className="text-sm text-slate-600" data-testid="usage-products">{t("Actieve menuproducten")}: <b>{u.activeProducts}</b></p>}
        </div>
      </Card>
      {billing.plan !== "legacy" && <Comparison />}
    </div>
  );
}
