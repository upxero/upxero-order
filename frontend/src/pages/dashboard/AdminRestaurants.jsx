import { useEffect, useState } from "react";
import { Store, Plus, Loader2, ExternalLink } from "lucide-react";
import { toast } from "sonner";
import api, { apiError } from "../../lib/api";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { Card } from "../../components/ui/card";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "../../components/ui/dialog";

const empty = { restaurantName: "", ownerName: "", email: "", password: "" };

export default function AdminRestaurants() {
  const [restaurants, setRestaurants] = useState(null);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState(empty);
  const [saving, setSaving] = useState(false);

  const load = () => api.get("/admin/restaurants").then(({ data }) => setRestaurants(data)).catch(() => setRestaurants([]));
  useEffect(() => { load(); }, []);

  const save = async () => {
    setSaving(true);
    try {
      await api.post("/admin/restaurants", form);
      toast.success("Restaurant aangemaakt");
      setOpen(false); setForm(empty); await load();
    } catch (e) { toast.error(apiError(e)); } finally { setSaving(false); }
  };

  return (
    <div className="space-y-6" data-testid="admin-page">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h1 className="font-heading text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl">Platform</h1>
          <p className="mt-1 text-sm text-slate-500">Beheer restaurants op het Upxero-platform.</p>
        </div>
        <Button onClick={() => { setForm(empty); setOpen(true); }} className="bg-emerald-600 hover:bg-emerald-700" data-testid="admin-add-button">
          <Plus className="mr-2 h-4 w-4" /> Nieuw restaurant
        </Button>
      </div>

      {restaurants === null ? (
        <div className="grid place-items-center py-20"><Loader2 className="h-6 w-6 animate-spin text-emerald-600" /></div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {restaurants.map((r) => (
            <Card key={r.id} className="rounded-xl border-slate-200 p-5 shadow-sm" data-testid={`admin-restaurant-${r.id}`}>
              <div className="flex items-start justify-between">
                <span className="grid h-10 w-10 place-items-center rounded-lg bg-slate-100 text-slate-500"><Store className="h-5 w-5" /></span>
                <span className={`rounded-md px-2 py-0.5 text-xs font-semibold ${r.orderingEnabled ? "bg-emerald-100 text-emerald-700" : "bg-slate-100 text-slate-500"}`}>
                  {r.orderingEnabled ? "Actief" : "Uit"}
                </span>
              </div>
              <p className="mt-3 font-semibold text-slate-900">{r.name}</p>
              <p className="text-sm text-slate-500">{r.city || "—"}</p>
              <div className="mt-3 flex gap-4 text-sm text-slate-500">
                <span>{r.orderCount} bestellingen</span>
                <span>{r.userCount} gebruikers</span>
              </div>
              <a href={`/order/${r.slug}`} target="_blank" rel="noreferrer" className="mt-3 inline-flex items-center gap-1 text-sm font-semibold text-emerald-600 hover:underline">
                Bestelpagina <ExternalLink className="h-3.5 w-3.5" />
              </a>
            </Card>
          ))}
        </div>
      )}

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="sm:max-w-md" data-testid="admin-dialog">
          <DialogHeader><DialogTitle>Nieuw restaurant</DialogTitle></DialogHeader>
          <div className="space-y-4">
            <div><Label>Restaurantnaam</Label><Input value={form.restaurantName} onChange={(e) => setForm({ ...form, restaurantName: e.target.value })} className="mt-1.5" data-testid="admin-restaurant-input" /></div>
            <div><Label>Naam eigenaar</Label><Input value={form.ownerName} onChange={(e) => setForm({ ...form, ownerName: e.target.value })} className="mt-1.5" data-testid="admin-owner-input" /></div>
            <div><Label>E-mail</Label><Input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} className="mt-1.5" data-testid="admin-email-input" /></div>
            <div><Label>Wachtwoord</Label><Input type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} className="mt-1.5" data-testid="admin-password-input" /></div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setOpen(false)}>Annuleren</Button>
            <Button onClick={save} disabled={saving} className="bg-emerald-600 hover:bg-emerald-700" data-testid="admin-save-button">
              {saving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />} Aanmaken
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
