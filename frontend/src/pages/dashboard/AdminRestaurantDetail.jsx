import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, ExternalLink, Loader2, Power } from "lucide-react";
import { toast } from "sonner";
import api, { apiError } from "../../lib/api";
import { useT } from "../../context/I18nContext";
import { formatDateTime } from "../../lib/format";
import { Button } from "../../components/ui/button";
import { Card } from "../../components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "../../components/ui/dialog";
import { EditEssentials } from "../../components/admin/EditEssentials";
import { DeletionRequests } from "../../components/admin/DeletionRequests";
import { PlanCard } from "../../components/admin/PlanCard";

const ACTIONS = {
  "restaurant.created": "Restaurant aangemaakt",
  "restaurant.activated": "Restaurant geactiveerd",
  "restaurant.deactivated": "Restaurant gedeactiveerd",
  "restaurant.updated": "Restaurantgegevens gewijzigd",
  "deletion.requested": "Verwijdering aangevraagd",
  "deletion.cancelled": "Verwijderverzoek ingetrokken",
  "deletion.rejected": "Verwijderverzoek afgewezen",
  "deletion.completed": "Verwijdering uitgevoerd",
  "restaurant.purged": "Restaurant definitief gewist",
  "subscription.legacy_set": "Gratis Pro toegekend",
  "subscription.legacy_removed": "Gratis Pro ingetrokken",
  "subscription.changed": "Abonnement gewijzigd (Whop)",
  "subscription.checkout_started": "Afrekenen gestart",
};
const ROLES = { restaurant_admin: "Beheerder", restaurant_staff: "Medewerker" };

export function StatusBadge({ r, pending }) {
  const t = useT();
  const [label, cls] = r.deletedAt ? ["Verwijderd", "bg-rose-100 text-rose-700"]
    : r.isActive === false ? ["Gedeactiveerd", "bg-slate-200 text-slate-600"] : ["Actief", "bg-emerald-100 text-emerald-700"];
  return (
    <span className="flex flex-wrap gap-1.5">
      <span className={`rounded-md px-2 py-0.5 text-xs font-semibold ${cls}`} data-testid="restaurant-status-badge">{t(label)}</span>
      {pending && <span className="rounded-md bg-amber-100 px-2 py-0.5 text-xs font-semibold text-amber-700" data-testid="pending-deletion-badge">{t("Verwijdering aangevraagd")}</span>}
    </span>
  );
}

function Info({ label, value, testid }) {
  return (
    <div className="min-w-0 rounded-lg border border-slate-200 bg-white p-4">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-400">{label}</p>
      <p className="mt-1 truncate text-sm font-semibold text-slate-900" data-testid={testid}>{value}</p>
    </div>
  );
}

function ActiveToggle({ r, onDone }) {
  const t = useT();
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const next = r.isActive === false;
  const submit = async () => {
    setBusy(true);
    try {
      await api.patch(`/admin/restaurants/${r.id}/active`, { isActive: next });
      toast.success(t(next ? "Restaurant geactiveerd" : "Restaurant gedeactiveerd"));
      setOpen(false); onDone();
    } catch (e) { toast.error(t(apiError(e))); } finally { setBusy(false); }
  };
  if (r.deletedAt) return null;
  return (
    <>
      <Button variant="outline" onClick={() => setOpen(true)} data-testid="toggle-active-button"
        className={next ? "border-emerald-300 text-emerald-700" : "border-rose-200 text-rose-700"}>
        <Power className="mr-2 h-4 w-4" /> {t(next ? "Activeren" : "Deactiveren")}
      </Button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="sm:max-w-md" data-testid="toggle-active-dialog">
          <DialogHeader><DialogTitle>{t(next ? "Restaurant activeren?" : "Restaurant deactiveren?")}</DialogTitle></DialogHeader>
          <p className="text-sm text-slate-600">
            {t(next ? "De openbare bestelpagina wordt weer bereikbaar." : "De openbare bestelpagina gaat offline en er kunnen geen bestellingen meer worden geplaatst. Er worden geen gegevens verwijderd; je kunt het restaurant later weer activeren.")}
          </p>
          <DialogFooter>
            <Button variant="outline" onClick={() => setOpen(false)}>{t("Annuleren")}</Button>
            <Button onClick={submit} disabled={busy} className={next ? "bg-emerald-600 hover:bg-emerald-700" : "bg-rose-600 hover:bg-rose-700"} data-testid="toggle-active-confirm">
              {busy && <Loader2 className="mr-2 h-4 w-4 animate-spin" />} {t(next ? "Activeren" : "Deactiveren")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}

export default function AdminRestaurantDetail() {
  const t = useT();
  const { id } = useParams();
  const [data, setData] = useState(undefined);
  const load = useCallback(() => api.get(`/admin/restaurants/${id}`).then(({ data: d }) => setData(d))
    .catch((e) => { toast.error(t(apiError(e))); setData(null); }), [id, t]);
  useEffect(() => { load(); }, [load]);

  if (data === undefined) return <div className="grid place-items-center py-20"><Loader2 className="h-6 w-6 animate-spin text-emerald-600" /></div>;
  const back = <Link to="/dashboard/platform" className="inline-flex items-center gap-1 text-sm font-medium text-emerald-600 hover:underline" data-testid="admin-back-link"><ArrowLeft className="h-4 w-4" /> {t("Platform")}</Link>;
  if (data === null) return <div className="space-y-4">{back}<p className="text-sm text-slate-500" data-testid="admin-detail-error">{t("Restaurant niet gevonden")}</p></div>;

  const r = data.restaurant;
  const pending = data.deletionRequests.some((x) => x.status === "pending");
  return (
    <div className="space-y-6" data-testid="admin-restaurant-detail">
      {back}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="break-words font-heading text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl" data-testid="admin-detail-name">{r.name}</h1>
          <div className="mt-2"><StatusBadge r={r} pending={pending} /></div>
        </div>
        <div className="flex flex-wrap gap-2">
          {!r.deletedAt && (
            <a href={`/order/${r.slug}`} target="_blank" rel="noreferrer" data-testid="admin-detail-order-link"
              className="inline-flex h-10 items-center gap-1 rounded-md border border-slate-300 px-4 text-sm font-medium text-slate-700 hover:bg-slate-50">
              {t("Bestelpagina")} <ExternalLink className="h-3.5 w-3.5" />
            </a>
          )}
          <ActiveToggle r={r} onDone={load} />
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Info label={t("Eigenaar")} value={data.owner?.email || "—"} testid="admin-detail-owner" />
        <Info label={t("Aangemaakt")} value={r.createdAt ? formatDateTime(r.createdAt) : "—"} testid="admin-detail-created" />
        <Info label={t("Bestellingen")} value={data.orderCount} testid="admin-detail-orders" />
        <Info label={t("Online bestellen")} value={t(r.orderingEnabled ? "Aan" : "Uit")} testid="admin-detail-ordering" />
      </div>

      <PlanCard restaurant={r} plan={data.plan} onChanged={load} />

      <EditEssentials key={r.updatedAt} restaurant={r} disabled={!!r.deletedAt} onSaved={load} />

      <Card className="rounded-xl border-slate-200 p-5 shadow-sm" data-testid="admin-users-card">
        <h2 className="font-heading text-lg font-semibold text-slate-900">{t("Gebruikers")}</h2>
        <ul className="mt-3 divide-y divide-slate-100">
          {data.users.map((u) => (
            <li key={u.id} className="flex flex-wrap items-center justify-between gap-2 py-2.5 text-sm" data-testid={`admin-user-${u.id}`}>
              <span className="break-all"><span className="font-medium text-slate-900">{u.name}</span> · <span className="text-slate-500">{u.email}</span></span>
              <span className="flex gap-2 text-xs text-slate-500">
                <span>{t(ROLES[u.role] || u.role)}</span>
                <span>· {u.deletedAt ? t("Verwijderd") : u.isActive ? t("Actief") : t("Gedeactiveerd")}</span>
                {!u.deletedAt && <span>· {u.emailVerified ? t("E-mail bevestigd") : t("E-mail niet bevestigd")}</span>}
              </span>
            </li>
          ))}
        </ul>
      </Card>

      <DeletionRequests requests={data.deletionRequests} restaurantName={r.name} onChange={load} />

      <Card className="rounded-xl border-slate-200 p-5 shadow-sm" data-testid="admin-audit-log">
        <h2 className="font-heading text-lg font-semibold text-slate-900">{t("Auditlog")}</h2>
        {data.auditLog.length === 0 ? <p className="mt-2 text-sm text-slate-500">{t("Nog geen acties geregistreerd.")}</p> : (
          <ul className="mt-3 divide-y divide-slate-100 text-sm">
            {data.auditLog.map((a) => (
              <li key={a.id} className="flex flex-col gap-0.5 py-2.5 sm:flex-row sm:justify-between" data-testid="audit-entry">
                <span className="font-medium text-slate-900">{t(ACTIONS[a.action] || a.action)}
                  {a.details?.fields && <span className="font-normal text-slate-500"> · {a.details.fields.join(", ")}</span>}
                </span>
                <span className="break-all text-slate-500">{a.actorEmail} · {formatDateTime(a.createdAt)}</span>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
