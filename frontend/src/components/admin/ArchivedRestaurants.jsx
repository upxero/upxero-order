import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Archive, Loader2 } from "lucide-react";
import { toast } from "sonner";
import api, { apiError } from "../../lib/api";
import { useI18n } from "../../context/I18nContext";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { Label } from "../ui/label";
import { Card } from "../ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "../ui/dialog";

const REMOVED = [
  "Geanonimiseerde gebruikersaccounts van dit restaurant",
  "Eventuele resterende menu-items, categorieën, bestanden en uitnodigingen",
  "Openingstijden, instellingen en de bestelnummerteller",
];
const KEPT = [
  "Geanonimiseerde bestellingen met bestelnummers, producten en totalen (boekhoudkundige bewaarplicht)",
  "Minimaal restaurantrecord: naam, link, land, aanmaak-, verwijder- en wisdatum",
  "Verwijderverzoeken en auditlog",
];

function PurgeDialog({ r, onClose, onDone }) {
  const { t } = useI18n();
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const purge = async () => {
    setBusy(true);
    try {
      await api.post(`/admin/restaurants/${r.id}/purge`, { confirmText: text });
      toast.success(t("Restaurant definitief gewist"));
      onDone();
    } catch (e) { toast.error(t(apiError(e))); } finally { setBusy(false); }
  };
  const list = (title, items, tone) => (
    <div>
      <p className={`text-sm font-semibold ${tone}`}>{t(title)}</p>
      <ul className="mt-1 list-disc space-y-0.5 pl-5 text-sm text-slate-600">{items.map((i) => <li key={i}>{t(i)}</li>)}</ul>
    </div>
  );
  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-lg" data-testid="purge-dialog">
        <DialogHeader><DialogTitle>{t("Definitief wissen")}: {r.name}</DialogTitle></DialogHeader>
        <p className="text-sm font-medium text-rose-700">{t("Dit is permanent en kan niet ongedaan worden gemaakt.")}</p>
        <div className="space-y-3 rounded-lg bg-slate-50 p-3">
          {list("Wordt permanent verwijderd", REMOVED, "text-rose-700")}
          {list("Blijft bewaard", KEPT, "text-slate-800")}
        </div>
        <div>
          <Label>{t("Typ \"{text}\" ter bevestiging", { text: r.name })}</Label>
          <Input value={text} onChange={(e) => setText(e.target.value)} className="mt-1.5" data-testid="purge-confirm-input" />
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>{t("Annuleren")}</Button>
          <Button onClick={purge} disabled={busy || text.trim().toLowerCase() !== r.name.trim().toLowerCase()}
            className="bg-rose-600 hover:bg-rose-700" data-testid="purge-submit-button">
            {busy && <Loader2 className="mr-2 h-4 w-4 animate-spin" />} {t("Definitief wissen")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export function ArchivedRestaurants() {
  const { t, lang } = useI18n();
  const [data, setData] = useState(null);
  const [purging, setPurging] = useState(null);
  const fmt = (iso) => new Date(iso).toLocaleDateString(lang === "nl" ? "nl-BE" : "en-GB", { day: "2-digit", month: "short", year: "numeric" });
  const load = useCallback(() => api.get("/admin/restaurants/archived").then(({ data: d }) => setData(d))
    .catch((e) => toast.error(t(apiError(e)))), [t]);
  useEffect(() => { load(); }, [load]);

  return (
    <Card className="rounded-xl border-slate-200 p-5 shadow-sm" data-testid="archived-restaurants">
      <div className="flex items-center gap-2">
        <Archive className="h-5 w-5 text-slate-500" />
        <h2 className="font-heading text-lg font-semibold text-slate-900">{t("Gearchiveerde / verwijderde restaurants")}</h2>
      </div>
      {data && (
        <p className="mt-1 text-sm text-slate-500" data-testid="retention-note">
          {t("Bewaartermijn: {days} dagen na verwijdering. Er wordt nooit automatisch gewist; definitief wissen is daarna een handmatige actie.", { days: data.retentionDays })}
        </p>
      )}
      {!data ? <Loader2 className="mt-4 h-5 w-5 animate-spin text-slate-400" /> : data.restaurants.length === 0 ? (
        <p className="mt-3 text-sm text-slate-500" data-testid="archived-empty">{t("Geen gearchiveerde restaurants.")}</p>
      ) : (
        <ul className="mt-3 divide-y divide-slate-100">
          {data.restaurants.map((r) => (
            <li key={r.id} className="flex flex-col gap-2 py-3 sm:flex-row sm:items-center sm:justify-between" data-testid={`archived-${r.id}`}>
              <div className="min-w-0 text-sm">
                <p className="break-words font-semibold text-slate-900">{r.name}
                  <span className={`ml-2 rounded-md px-2 py-0.5 text-xs font-semibold ${r.purgedAt ? "bg-slate-200 text-slate-600" : "bg-rose-100 text-rose-700"}`}>
                    {t(r.purgedAt ? "Definitief gewist" : "Verwijderd")}
                  </span>
                </p>
                <p className="text-slate-500">
                  {t("Verwijderd op")} {fmt(r.deletedAt)} · {r.purgedAt ? `${t("Gewist op")} ${fmt(r.purgedAt)}` : `${t("Wissen mogelijk vanaf")} ${fmt(r.purgeEligibleAt)}`} · {r.orderCount} {t("bestellingen bewaard")}
                </p>
              </div>
              <div className="flex shrink-0 gap-2">
                <Link to={`/dashboard/platform/${r.id}`} className="inline-flex h-9 items-center rounded-md border border-slate-300 px-3 text-sm font-medium text-slate-700 hover:bg-slate-50" data-testid={`archived-view-${r.id}`}>{t("Bekijken")}</Link>
                {!r.purgedAt && (
                  <Button size="sm" disabled={!r.canPurge} onClick={() => setPurging(r)} className="h-9 bg-rose-600 hover:bg-rose-700" data-testid={`purge-button-${r.id}`}
                    title={r.canPurge ? "" : `${t("Wissen mogelijk vanaf")} ${fmt(r.purgeEligibleAt)}`}>
                    {t("Definitief wissen")}
                  </Button>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
      {purging && <PurgeDialog r={purging} onClose={() => setPurging(null)} onDone={() => { setPurging(null); load(); }} />}
    </Card>
  );
}
