import { useState } from "react";
import { Gift, Loader2 } from "lucide-react";
import { toast } from "sonner";
import api, { apiError } from "../../lib/api";
import { useT } from "../../context/I18nContext";
import { Button } from "../ui/button";
import { Card } from "../ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "../ui/dialog";

export const PLAN_LABELS = { free: "Free", pro: "Pro", legacy: "Gratis Pro" };

export function PlanBadge({ plan }) {
  const t = useT();
  const cls = plan === "free" ? "bg-slate-100 text-slate-600" : plan === "legacy" ? "bg-violet-100 text-violet-700" : "bg-emerald-100 text-emerald-700";
  return <span className={`rounded-md px-2 py-0.5 text-xs font-semibold ${cls}`} data-testid="plan-badge">{t(PLAN_LABELS[plan] || plan)}</span>;
}

export function PlanCard({ restaurant, plan, onChanged }) {
  const t = useT();
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const sub = restaurant.subscription || {};
  const grant = !sub.legacy;
  const paid = plan === "pro" || (sub.whopStatus && ["trialing", "active", "past_due", "canceling"].includes(sub.whopStatus));

  const submit = async () => {
    setBusy(true);
    try {
      await api.patch(`/admin/restaurants/${restaurant.id}/legacy`, { legacy: grant });
      toast.success(t(grant ? "Gratis Pro toegekend" : "Gratis Pro ingetrokken"));
      setOpen(false); onChanged();
    } catch (e) { toast.error(t(apiError(e))); } finally { setBusy(false); }
  };

  return (
    <Card className="rounded-xl border-slate-200 p-5 shadow-sm" data-testid="admin-plan-card">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="font-heading text-lg font-semibold text-slate-900">{t("Abonnement")}</h2>
          <div className="mt-1 flex flex-wrap items-center gap-2 text-sm text-slate-500">
            <PlanBadge plan={plan} />
            {sub.whopStatus && <span>Whop: {sub.whopStatus}</span>}
          </div>
        </div>
        {!restaurant.deletedAt && (
          <Button variant="outline" onClick={() => setOpen(true)} disabled={grant && paid} data-testid="toggle-complimentary-button"
            title={grant && paid ? t("Dit restaurant heeft een actief betaald abonnement.") : ""}
            className={grant ? "border-violet-300 text-violet-700" : "border-rose-200 text-rose-700"}>
            <Gift className="mr-2 h-4 w-4" /> {t(grant ? "Gratis Pro toekennen" : "Gratis Pro intrekken")}
          </Button>
        )}
      </div>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="sm:max-w-md" data-testid="complimentary-dialog">
          <DialogHeader><DialogTitle>{t(grant ? "Gratis Pro toekennen?" : "Gratis Pro intrekken?")}</DialogTitle></DialogHeader>
          <p className="text-sm text-slate-600">
            {t(grant ? "Het restaurant krijgt alle Pro-functies zonder betaling via Whop."
              : "Het restaurant valt terug op Free (of op een eventueel betaald Whop-abonnement). Er worden geen gegevens verwijderd; Free-beperkingen gelden voor nieuwe acties.")}
          </p>
          <DialogFooter>
            <Button variant="outline" onClick={() => setOpen(false)}>{t("Annuleren")}</Button>
            <Button onClick={submit} disabled={busy} className={grant ? "bg-violet-600 hover:bg-violet-700" : "bg-rose-600 hover:bg-rose-700"} data-testid="complimentary-confirm">
              {busy && <Loader2 className="mr-2 h-4 w-4 animate-spin" />} {t("Bevestigen")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Card>
  );
}
