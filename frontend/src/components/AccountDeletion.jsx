import { useEffect, useState } from "react";
import { Loader2, Trash2, UserX } from "lucide-react";
import { toast } from "sonner";
import api, { apiError } from "../lib/api";
import { useAuth } from "../context/AuthContext";
import { useT } from "../context/I18nContext";
import { formatDateTime } from "../lib/format";
import { DeletionInfo } from "./DeletionInfo";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Label } from "./ui/label";
import { Textarea } from "./ui/textarea";
import { Card } from "./ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "./ui/dialog";

const TITLES = { account: "Mijn eigenaarsaccount verwijderen", restaurant: "Restaurant sluiten en gegevens verwijderen" };

function RequestDialog({ type, onClose, onDone }) {
  const t = useT();
  const { user, restaurant } = useAuth();
  const [form, setForm] = useState({ password: "", confirmText: "", reason: "" });
  const [busy, setBusy] = useState(false);
  const expected = type === "restaurant" ? restaurant?.name : user?.email;

  const submit = async () => {
    setBusy(true);
    try {
      const { data } = await api.post("/restaurant/deletion-request", { type, ...form });
      toast.success(t("Verwijderverzoek verstuurd"));
      onDone(data.request);
    } catch (e) { toast.error(t(apiError(e))); } finally { setBusy(false); }
  };

  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-lg" data-testid="deletion-request-dialog">
        <DialogHeader><DialogTitle>{t(TITLES[type])}</DialogTitle></DialogHeader>
        <p className="text-sm text-slate-500">{t("Je verzoek wordt beoordeeld door het Upxero-platformteam. Er wordt niets verwijderd tot het verzoek is verwerkt, en tot die tijd kun je het intrekken.")}</p>
        <DeletionInfo type={type} email={user?.email} />
        <div className="space-y-3">
          <div><Label>{t("Reden (optioneel)")}</Label><Textarea value={form.reason} onChange={(e) => setForm({ ...form, reason: e.target.value })} className="mt-1.5" data-testid="deletion-reason-input" /></div>
          <div><Label>{t("Typ \"{text}\" ter bevestiging", { text: expected })}</Label><Input value={form.confirmText} onChange={(e) => setForm({ ...form, confirmText: e.target.value })} className="mt-1.5" data-testid="deletion-confirm-input" /></div>
          <div><Label>{t("Wachtwoord")}</Label><Input type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} className="mt-1.5" data-testid="deletion-password-input" /></div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>{t("Annuleren")}</Button>
          <Button onClick={submit} disabled={busy || !form.password || form.confirmText.trim().toLowerCase() !== (expected || "").trim().toLowerCase()}
            className="bg-rose-600 hover:bg-rose-700" data-testid="deletion-submit-button">
            {busy && <Loader2 className="mr-2 h-4 w-4 animate-spin" />} {t("Verwijderverzoek versturen")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export function AccountDeletion() {
  const t = useT();
  const [req, setReq] = useState(undefined);
  const [dialog, setDialog] = useState(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.get("/restaurant/deletion-request").then(({ data }) => setReq(data.request)).catch(() => setReq(null));
  }, []);

  const cancel = async () => {
    setBusy(true);
    try {
      await api.delete("/restaurant/deletion-request");
      toast.success(t("Verwijderverzoek ingetrokken"));
      setReq(null);
    } catch (e) { toast.error(t(apiError(e))); } finally { setBusy(false); }
  };

  return (
    <Card className="space-y-4 rounded-xl border-rose-200 p-5 shadow-sm" data-testid="account-deletion-card">
      <div>
        <h2 className="font-heading text-lg font-semibold text-rose-700">{t("Account verwijderen")}</h2>
        <p className="mt-0.5 text-sm text-slate-500">{t("Vraag verwijdering aan van je eigenaarsaccount, of sluit je restaurant en laat de gegevens verwijderen.")}</p>
      </div>
      {req === undefined ? (
        <Loader2 className="h-5 w-5 animate-spin text-slate-400" />
      ) : req ? (
        <div className="flex flex-col gap-3 rounded-lg border border-amber-200 bg-amber-50 p-3 sm:flex-row sm:items-center sm:justify-between" data-testid="deletion-pending">
          <p className="text-sm text-amber-900">
            <span className="font-semibold">{t("Verwijderverzoek in behandeling")}</span> · {t(TITLES[req.type])} · {formatDateTime(req.createdAt)}
          </p>
          <Button variant="outline" onClick={cancel} disabled={busy} className="border-amber-300" data-testid="deletion-cancel-button">
            {busy && <Loader2 className="mr-2 h-4 w-4 animate-spin" />} {t("Verzoek intrekken")}
          </Button>
        </div>
      ) : (
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" onClick={() => setDialog("account")} className="border-rose-200 text-rose-700 hover:bg-rose-50" data-testid="delete-account-button">
            <UserX className="mr-2 h-4 w-4" /> {t(TITLES.account)}
          </Button>
          <Button variant="outline" onClick={() => setDialog("restaurant")} className="border-rose-200 text-rose-700 hover:bg-rose-50" data-testid="delete-restaurant-button">
            <Trash2 className="mr-2 h-4 w-4" /> {t(TITLES.restaurant)}
          </Button>
        </div>
      )}
      {dialog && <RequestDialog type={dialog} onClose={() => setDialog(null)} onDone={(r) => { setReq(r); setDialog(null); }} />}
    </Card>
  );
}
