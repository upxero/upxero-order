import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";
import { toast } from "sonner";
import api, { apiError } from "../../lib/api";
import { DAYS } from "../../lib/constants";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Switch } from "../../components/ui/switch";
import { Card } from "../../components/ui/card";

export default function OpeningHours() {
  const [hours, setHours] = useState(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api.get("/restaurant/me").then(({ data }) => setHours(data.openingHours || {}));
  }, []);

  if (!hours) return <div className="grid place-items-center py-20"><Loader2 className="h-6 w-6 animate-spin text-emerald-600" /></div>;

  const upd = (day, patch) => setHours((h) => ({ ...h, [day]: { ...h[day], ...patch } }));

  const save = async () => {
    setSaving(true);
    try {
      await api.put("/restaurant/opening-hours", hours);
      toast.success("Openingstijden opgeslagen");
    } catch (e) { toast.error(apiError(e)); } finally { setSaving(false); }
  };

  return (
    <div className="space-y-6" data-testid="hours-page">
      <div>
        <h1 className="font-heading text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl">Openingstijden</h1>
        <p className="mt-1 text-sm text-slate-500">Bepaal wanneer klanten online kunnen bestellen.</p>
      </div>

      <Card className="divide-y divide-slate-100 rounded-xl border-slate-200 p-0 shadow-sm">
        {DAYS.map(([key, label]) => {
          const d = hours[key] || { closed: true, open: "11:30", close: "21:30" };
          return (
            <div key={key} className="flex flex-wrap items-center gap-4 px-5 py-4" data-testid={`hours-row-${key}`}>
              <div className="w-28 font-medium text-slate-900">{label}</div>
              <div className="flex items-center gap-2">
                <Switch checked={!d.closed} onCheckedChange={(v) => upd(key, { closed: !v })} data-testid={`hours-open-switch-${key}`} />
                <span className={`text-sm font-medium ${d.closed ? "text-slate-400" : "text-emerald-600"}`}>{d.closed ? "Gesloten" : "Open"}</span>
              </div>
              {!d.closed && (
                <div className="flex items-center gap-2">
                  <Input type="time" value={d.open} onChange={(e) => upd(key, { open: e.target.value })} className="w-32" data-testid={`hours-open-${key}`} />
                  <span className="text-slate-400">–</span>
                  <Input type="time" value={d.close} onChange={(e) => upd(key, { close: e.target.value })} className="w-32" data-testid={`hours-close-${key}`} />
                </div>
              )}
            </div>
          );
        })}
      </Card>

      <div className="flex justify-end">
        <Button onClick={save} disabled={saving} className="bg-emerald-600 hover:bg-emerald-700" data-testid="hours-save-button">
          {saving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />} Opslaan
        </Button>
      </div>
    </div>
  );
}
