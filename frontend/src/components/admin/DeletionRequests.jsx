import { useState } from "react";
import { Loader2 } from "lucide-react";
import { toast } from "sonner";
import api, { apiError } from "../../lib/api";
import { useT } from "../../context/I18nContext";
import { formatDateTime } from "../../lib/format";
import { DeletionInfo } from "../DeletionInfo";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { Label } from "../ui/label";
import { Card } from "../ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "../ui/dialog";

const TYPE = { account: "Eigenaarsaccount verwijderen", restaurant: "Restaurant sluiten en gegevens verwijderen" };
const STATUS = { pending: "In behandeling", completed: "Uitgevoerd", rejected: "Afgewezen", cancelled: "Ingetrokken" };

function ApproveDialog({ req, restaurantName, onClose, onDone }) {
  const t = useT();
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const approve = async () => {
    setBusy(true);
    try {
      await api.post(`/admin/deletion-requests/${req.id}/approve`, { confirmText: text });
      toast.success(t("Verwijdering uitgevoerd"));
      onDone();
    } catch (e) { toast.error(t(apiError(e))); } finally { setBusy(false); }
  };
  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-lg" data-testid="approve-deletion-dialog">
        <DialogHeader><DialogTitle>{t(TYPE[req.type])}</DialogTitle></DialogHeader>
        <p className="text-sm font-medium text-rose-700">{t("Dit is permanent en kan niet ongedaan worden gemaakt.")}</p>
        <DeletionInfo type={req.type} email={req.requestedByEmail} />
        <div>
          <Label>{t("Typ \"{text}\" ter bevestiging", { text: restaurantName })}</Label>
          <Input value={text} onChange={(e) => setText(e.target.value)} className="mt-1.5" data-testid="approve-confirm-input" />
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>{t("Annuleren")}</Button>
          <Button onClick={approve} disabled={busy || text.trim().toLowerCase() !== restaurantName.trim().toLowerCase()}
            className="bg-rose-600 hover:bg-rose-700" data-testid="approve-submit-button">
            {busy && <Loader2 className="mr-2 h-4 w-4 animate-spin" />} {t("Definitief verwijderen")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export function DeletionRequests({ requests, restaurantName, onChange }) {
  const t = useT();
  const [approving, setApproving] = useState(null);
  const [busy, setBusy] = useState(null);

  const reject = async (req) => {
    setBusy(req.id);
    try {
      await api.post(`/admin/deletion-requests/${req.id}/reject`, { reason: "" });
      toast.success(t("Verwijderverzoek afgewezen"));
      onChange();
    } catch (e) { toast.error(t(apiError(e))); } finally { setBusy(null); }
  };

  return (
    <Card className="rounded-xl border-slate-200 p-5 shadow-sm" data-testid="admin-deletion-requests">
      <h2 className="font-heading text-lg font-semibold text-slate-900">{t("Verwijderverzoeken")}</h2>
      {requests.length === 0 ? (
        <p className="mt-2 text-sm text-slate-500">{t("Geen verwijderverzoeken.")}</p>
      ) : (
        <ul className="mt-3 divide-y divide-slate-100">
          {requests.map((r) => (
            <li key={r.id} className="flex flex-col gap-2 py-3 sm:flex-row sm:items-center sm:justify-between" data-testid={`deletion-request-${r.id}`}>
              <div className="text-sm">
                <p className="font-semibold text-slate-900">{t(TYPE[r.type])} · <span className="text-slate-500">{t(STATUS[r.status])}</span></p>
                <p className="text-slate-500">{r.requestedByEmail} · {formatDateTime(r.createdAt)}</p>
                {r.reason && <p className="mt-1 text-slate-600">“{r.reason}”</p>}
              </div>
              {r.status === "pending" && (
                <div className="flex gap-2">
                  <Button variant="outline" disabled={busy === r.id} onClick={() => reject(r)} data-testid={`reject-deletion-${r.id}`}>
                    {busy === r.id && <Loader2 className="mr-2 h-4 w-4 animate-spin" />} {t("Afwijzen")}
                  </Button>
                  <Button className="bg-rose-600 hover:bg-rose-700" onClick={() => setApproving(r)} data-testid={`approve-deletion-${r.id}`}>
                    {t("Goedkeuren en verwijderen")}
                  </Button>
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
      {approving && (
        <ApproveDialog req={approving} restaurantName={restaurantName} onClose={() => setApproving(null)}
          onDone={() => { setApproving(null); onChange(); }} />
      )}
    </Card>
  );
}
