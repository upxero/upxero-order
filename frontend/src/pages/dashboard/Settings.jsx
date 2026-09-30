import { useEffect, useState } from "react";
import { Power, ShoppingBag, Loader2 } from "lucide-react";
import { toast } from "sonner";
import api, { apiError } from "../../lib/api";
import { useAuth } from "../../context/AuthContext";
import { Switch } from "../../components/ui/switch";
import { Card } from "../../components/ui/card";

export default function Settings() {
  const { refetch } = useAuth();
  const [state, setState] = useState(null);

  useEffect(() => {
    api.get("/restaurant/me").then(({ data }) =>
      setState({ orderingEnabled: data.orderingEnabled, pickupEnabled: data.pickupEnabled })
    );
  }, []);

  if (!state) return <div className="grid place-items-center py-20"><Loader2 className="h-6 w-6 animate-spin text-emerald-600" /></div>;

  const update = async (patch) => {
    const next = { ...state, ...patch };
    setState(next);
    try {
      await api.put("/restaurant/settings", next);
      toast.success("Instelling opgeslagen");
      refetch();
    } catch (e) {
      toast.error(apiError(e));
      setState(state);
    }
  };

  return (
    <div className="space-y-6" data-testid="settings-page">
      <div>
        <h1 className="font-heading text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl">Instellingen</h1>
        <p className="mt-1 text-sm text-slate-500">Schakel online bestellen en afhalen aan of uit.</p>
      </div>

      <Card className="rounded-xl border-slate-200 p-5 shadow-sm">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="grid h-10 w-10 place-items-center rounded-lg bg-emerald-50 text-emerald-600"><Power className="h-5 w-5" /></span>
            <div>
              <p className="font-semibold text-slate-900">Online bestellen</p>
              <p className="text-sm text-slate-500">Zet uit om tijdelijk geen bestellingen te ontvangen.</p>
            </div>
          </div>
          <Switch checked={state.orderingEnabled} onCheckedChange={(v) => update({ orderingEnabled: v })} data-testid="settings-ordering-switch" />
        </div>
      </Card>

      <Card className="rounded-xl border-slate-200 p-5 shadow-sm">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="grid h-10 w-10 place-items-center rounded-lg bg-emerald-50 text-emerald-600"><ShoppingBag className="h-5 w-5" /></span>
            <div>
              <p className="font-semibold text-slate-900">Afhalen</p>
              <p className="text-sm text-slate-500">Klanten kunnen hun bestelling komen afhalen.</p>
            </div>
          </div>
          <Switch checked={state.pickupEnabled} onCheckedChange={(v) => update({ pickupEnabled: v })} data-testid="settings-pickup-switch" />
        </div>
      </Card>
    </div>
  );
}
