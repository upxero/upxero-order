import { useEffect, useState } from "react";
import { Truck, Plus, Trash2, Loader2, Info } from "lucide-react";
import { toast } from "sonner";
import api, { apiError } from "../../lib/api";
import { useAuth } from "../../context/AuthContext";
import { useT } from "../../context/I18nContext";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { Switch } from "../../components/ui/switch";
import { Card } from "../../components/ui/card";

export default function Delivery() {
  const { restaurant, refetch } = useAuth();
  const t = useT();
  const [form, setForm] = useState(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api.get("/restaurant/me").then(({ data }) => {
      setForm({
        deliveryEnabled: data.deliveryEnabled,
        freeDeliveryEnabled: data.freeDeliveryEnabled,
        freeDeliveryThreshold: data.freeDeliveryThreshold || 0,
        zones: (data.deliveryZones || []).map((z) => ({ ...z })),
        hasLocation: data.latitude != null,
      });
    });
  }, []);

  if (!form) return <div className="grid place-items-center py-20"><Loader2 className="h-6 w-6 animate-spin text-emerald-600" /></div>;

  const addZone = () => setForm((f) => ({ ...f, zones: [...f.zones, { minDistance: 0, maxDistance: 3, deliveryFee: 2.5, minimumOrderAmount: 15, enabled: true }] }));
  const updZone = (i, patch) => setForm((f) => { const z = [...f.zones]; z[i] = { ...z[i], ...patch }; return { ...f, zones: z }; });
  const removeZone = (i) => setForm((f) => ({ ...f, zones: f.zones.filter((_, idx) => idx !== i) }));

  const save = async () => {
    setSaving(true);
    try {
      await api.put("/restaurant/delivery", {
        deliveryEnabled: form.deliveryEnabled,
        freeDeliveryEnabled: form.freeDeliveryEnabled,
        freeDeliveryThreshold: parseFloat(form.freeDeliveryThreshold) || 0,
        zones: form.zones.map((z) => ({
          id: z.id, enabled: z.enabled,
          minDistance: parseFloat(z.minDistance) || 0,
          maxDistance: parseFloat(z.maxDistance) || 0,
          deliveryFee: parseFloat(z.deliveryFee) || 0,
          minimumOrderAmount: parseFloat(z.minimumOrderAmount) || 0,
        })),
      });
      toast.success(t("Bezorginstellingen opgeslagen"));
      refetch();
    } catch (e) { toast.error(t(apiError(e))); } finally { setSaving(false); }
  };

  return (
    <div className="space-y-6" data-testid="delivery-page">
      <div>
        <h1 className="font-heading text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl">{t("Bezorging")}</h1>
        <p className="mt-1 text-sm text-slate-500">{t("Stel bezorgzones in op basis van afstand.")}</p>
      </div>

      {!form.hasLocation && (
        <div className="flex items-start gap-2 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800" data-testid="delivery-location-warning">
          <Info className="mt-0.5 h-4 w-4 shrink-0" />
          <span>{t("Stel eerst je restaurantadres in bij")} <b>{t("Profiel")}</b> {t("zodat afstanden berekend kunnen worden.")}</span>
        </div>
      )}

      <Card className="rounded-xl border-slate-200 p-5 shadow-sm">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="grid h-10 w-10 place-items-center rounded-lg bg-emerald-50 text-emerald-600"><Truck className="h-5 w-5" /></span>
            <div>
              <p className="font-semibold text-slate-900">{t("Bezorgen inschakelen")}</p>
              <p className="text-sm text-slate-500">{t("Klanten kunnen kiezen voor bezorging.")}</p>
            </div>
          </div>
          <Switch checked={form.deliveryEnabled} onCheckedChange={(v) => setForm({ ...form, deliveryEnabled: v })} data-testid="delivery-enabled-switch" />
        </div>
      </Card>

      <Card className="rounded-xl border-slate-200 p-5 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <Switch checked={form.freeDeliveryEnabled} onCheckedChange={(v) => setForm({ ...form, freeDeliveryEnabled: v })} data-testid="free-delivery-switch" />
            <Label className="font-semibold">{t("Gratis bezorgd vanaf")}</Label>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-slate-500">€</span>
            <Input type="number" step="0.5" min="0" value={form.freeDeliveryThreshold} disabled={!form.freeDeliveryEnabled}
              onChange={(e) => setForm({ ...form, freeDeliveryThreshold: e.target.value })} className="w-28" data-testid="free-delivery-threshold" />
          </div>
        </div>
      </Card>

      <Card className="rounded-xl border-slate-200 p-5 shadow-sm">
        <div className="flex items-center justify-between">
          <h2 className="font-heading text-lg font-semibold text-slate-900">{t("Bezorgzones")}</h2>
          <Button variant="outline" onClick={addZone} className="border-slate-300" data-testid="zone-add-button"><Plus className="mr-2 h-4 w-4" /> {t("Zone")}</Button>
        </div>

        {form.zones.length === 0 ? (
          <p className="mt-6 rounded-lg border border-dashed border-slate-300 py-8 text-center text-sm text-slate-500" data-testid="zones-empty">
            {t("Nog geen bezorgzones ingesteld.")}
          </p>
        ) : (
          <div className="mt-4 space-y-3">
            <div className="hidden gap-3 px-1 text-xs font-medium text-slate-400 sm:grid sm:grid-cols-[1fr_1fr_1fr_1fr_auto_auto]">
              <span>{t("Van (km)")}</span><span>{t("Tot (km)")}</span><span>{t("Bezorgkosten €")}</span><span>{t("Min. bestelling €")}</span><span>{t("Aan")}</span><span></span>
            </div>
            {form.zones.map((z, i) => (
              <div key={i} className="grid grid-cols-2 items-center gap-3 rounded-lg bg-slate-50 p-3 sm:grid-cols-[1fr_1fr_1fr_1fr_auto_auto]" data-testid={`zone-row-${i}`}>
                <Input type="number" step="0.5" value={z.minDistance} onChange={(e) => updZone(i, { minDistance: e.target.value })} className="bg-white" data-testid={`zone-min-dist-${i}`} />
                <Input type="number" step="0.5" value={z.maxDistance} onChange={(e) => updZone(i, { maxDistance: e.target.value })} className="bg-white" data-testid={`zone-max-dist-${i}`} />
                <Input type="number" step="0.5" value={z.deliveryFee} onChange={(e) => updZone(i, { deliveryFee: e.target.value })} className="bg-white" data-testid={`zone-fee-${i}`} />
                <Input type="number" step="0.5" value={z.minimumOrderAmount} onChange={(e) => updZone(i, { minimumOrderAmount: e.target.value })} className="bg-white" data-testid={`zone-min-order-${i}`} />
                <div className="flex justify-center"><Switch checked={z.enabled} onCheckedChange={(v) => updZone(i, { enabled: v })} /></div>
                <Button variant="ghost" size="icon" onClick={() => removeZone(i)} data-testid={`zone-delete-${i}`}><Trash2 className="h-4 w-4 text-rose-500" /></Button>
              </div>
            ))}
          </div>
        )}
      </Card>

      <div className="flex justify-end">
        <Button onClick={save} disabled={saving} className="bg-emerald-600 hover:bg-emerald-700" data-testid="delivery-save-button">
          {saving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />} {t("Opslaan")}
        </Button>
      </div>
    </div>
  );
}
