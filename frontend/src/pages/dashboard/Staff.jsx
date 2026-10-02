import { useEffect, useState } from "react";
import { Users, UserPlus, Loader2, Mail, Clock, Ban, CheckCircle2, X } from "lucide-react";
import { toast } from "sonner";
import api, { apiError } from "../../lib/api";
import { formatDateTime } from "../../lib/format";
import { useT } from "../../context/I18nContext";
import { EmptyState } from "../../components/EmptyState";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { Card } from "../../components/ui/card";

export default function Staff() {
  const t = useT();
  const [data, setData] = useState(null);
  const [email, setEmail] = useState("");
  const [inviting, setInviting] = useState(false);
  const [busy, setBusy] = useState(null);

  const load = () => api.get("/restaurant/staff").then(({ data }) => setData(data)).catch(() => setData({ staff: [], invitations: [] }));
  useEffect(() => { load(); }, []);

  const invite = async (e) => {
    e.preventDefault();
    setInviting(true);
    try {
      await api.post("/restaurant/staff/invite", { email });
      toast.success(t("Uitnodiging verstuurd"));
      setEmail("");
      await load();
    } catch (err) { toast.error(t(apiError(err))); } finally { setInviting(false); }
  };

  const toggleActive = async (u) => {
    setBusy(u.id);
    try {
      await api.patch(`/restaurant/staff/${u.id}/active`, { isActive: !u.isActive });
      toast.success(u.isActive ? t("Toegang gedeactiveerd") : t("Toegang geactiveerd"));
      await load();
    } catch (err) { toast.error(t(apiError(err))); } finally { setBusy(null); }
  };

  const revoke = async (inv) => {
    if (!window.confirm(t("Uitnodiging voor {email} intrekken?", { email: inv.email }))) return;
    setBusy(inv.id);
    try {
      await api.delete(`/restaurant/staff/invitations/${inv.id}`);
      toast.success(t("Uitnodiging ingetrokken"));
      await load();
    } catch (err) { toast.error(t(apiError(err))); } finally { setBusy(null); }
  };

  return (
    <div className="space-y-6" data-testid="staff-page">
      <div>
        <h1 className="font-heading text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl">{t("Personeel")}</h1>
        <p className="mt-1 text-sm text-slate-500">{t("Nodig medewerkers uit en beheer hun toegang.")}</p>
      </div>

      <Card className="rounded-xl border-slate-200 p-5 shadow-sm">
        <h2 className="font-heading text-lg font-semibold text-slate-900">{t("Medewerker uitnodigen")}</h2>
        <p className="mt-1 text-sm text-slate-500">{t("Ze ontvangen een e-mail om hun eigen account aan te maken.")}</p>
        <form onSubmit={invite} className="mt-4 flex flex-col gap-3 sm:flex-row" data-testid="invite-form">
          <div className="flex-1">
            <Label htmlFor="invite-email" className="sr-only">{t("E-mailadres")}</Label>
            <Input id="invite-email" type="email" required value={email} onChange={(e) => setEmail(e.target.value)}
              placeholder="medewerker@email.be" data-testid="invite-email-input" />
          </div>
          <Button type="submit" disabled={inviting} className="bg-emerald-600 hover:bg-emerald-700" data-testid="invite-submit-button">
            {inviting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <UserPlus className="mr-2 h-4 w-4" />} {t("Uitnodigen")}
          </Button>
        </form>
      </Card>

      {data === null ? (
        <div className="grid place-items-center py-16"><Loader2 className="h-6 w-6 animate-spin text-emerald-600" /></div>
      ) : (
        <>
          {data.invitations.length > 0 && (
            <Card className="rounded-xl border-slate-200 p-5 shadow-sm">
              <h2 className="font-heading text-lg font-semibold text-slate-900">{t("Openstaande uitnodigingen")}</h2>
              <div className="mt-4 divide-y divide-slate-100">
                {data.invitations.map((inv) => (
                  <div key={inv.id} className="flex items-center justify-between gap-3 py-3" data-testid={`invitation-row-${inv.id}`}>
                    <div className="flex items-center gap-3">
                      <span className="grid h-9 w-9 place-items-center rounded-lg bg-amber-50 text-amber-600"><Mail className="h-4.5 w-4.5" size={18} /></span>
                      <div>
                        <p className="font-medium text-slate-900">{inv.email}</p>
                        <p className="flex items-center gap-1 text-xs text-slate-400"><Clock className="h-3 w-3" /> {t("Verloopt {date}", { date: formatDateTime(inv.expiresAt) })}</p>
                      </div>
                    </div>
                    <Button variant="outline" size="sm" onClick={() => revoke(inv)} disabled={busy === inv.id}
                      className="border-slate-300 text-rose-600 hover:bg-rose-50" data-testid={`invitation-revoke-${inv.id}`}>
                      <X className="mr-1 h-3.5 w-3.5" /> {t("Intrekken")}
                    </Button>
                  </div>
                ))}
              </div>
            </Card>
          )}

          <Card className="rounded-xl border-slate-200 p-5 shadow-sm">
            <h2 className="font-heading text-lg font-semibold text-slate-900">{t("Medewerkers")}</h2>
            {data.staff.length === 0 ? (
              <EmptyState icon={Users} title={t("Nog geen medewerkers")} description={t("Nodig je eerste medewerker uit via het formulier hierboven.")} testid="staff-empty" />
            ) : (
              <div className="mt-4 divide-y divide-slate-100">
                {data.staff.map((u) => (
                  <div key={u.id} className="flex items-center justify-between gap-3 py-3" data-testid={`staff-row-${u.id}`}>
                    <div className="flex items-center gap-3">
                      <span className={`grid h-9 w-9 place-items-center rounded-lg ${u.isActive ? "bg-emerald-50 text-emerald-600" : "bg-slate-100 text-slate-400"}`}>
                        <Users className="h-4.5 w-4.5" size={18} />
                      </span>
                      <div>
                        <p className="font-medium text-slate-900">{u.name}</p>
                        <p className="text-xs text-slate-500">{u.email}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className={`rounded-md px-2 py-0.5 text-xs font-semibold ${u.isActive ? "bg-emerald-100 text-emerald-700" : "bg-slate-100 text-slate-500"}`} data-testid={`staff-status-${u.id}`}>
                        {u.isActive ? t("Actief") : t("Inactief")}
                      </span>
                      <Button variant="outline" size="sm" onClick={() => toggleActive(u)} disabled={busy === u.id}
                        className={`border-slate-300 ${u.isActive ? "text-rose-600 hover:bg-rose-50" : "text-emerald-600 hover:bg-emerald-50"}`}
                        data-testid={`staff-toggle-${u.id}`}>
                        {busy === u.id ? <Loader2 className="h-4 w-4 animate-spin" /> : u.isActive ? <><Ban className="mr-1 h-3.5 w-3.5" /> {t("Deactiveren")}</> : <><CheckCircle2 className="mr-1 h-3.5 w-3.5" /> {t("Activeren")}</>}
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </>
      )}
    </div>
  );
}
