import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";
import { toast } from "sonner";
import api, { apiError } from "../../lib/api";
import { useAuth } from "../../context/AuthContext";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { Textarea } from "../../components/ui/textarea";
import { Card } from "../../components/ui/card";

export default function Profile() {
  const { refetch } = useAuth();
  const [form, setForm] = useState(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api.get("/restaurant/me").then(({ data }) => setForm({
      name: data.name || "", description: data.description || "", logo: data.logo || "",
      phone: data.phone || "", email: data.email || "", street: data.street || "",
      houseNumber: data.houseNumber || "", postalCode: data.postalCode || "", city: data.city || "",
      country: data.country || "BE", defaultLanguage: data.defaultLanguage || "nl",
    }));
  }, []);

  if (!form) return <div className="grid place-items-center py-20"><Loader2 className="h-6 w-6 animate-spin text-emerald-600" /></div>;

  const upd = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const save = async () => {
    setSaving(true);
    try {
      await api.put("/restaurant/profile", form);
      toast.success("Profiel opgeslagen. Adres wordt automatisch gelokaliseerd voor bezorging.");
      refetch();
    } catch (e) { toast.error(apiError(e)); } finally { setSaving(false); }
  };

  return (
    <div className="space-y-6" data-testid="profile-page">
      <div>
        <h1 className="font-heading text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl">Profiel</h1>
        <p className="mt-1 text-sm text-slate-500">Gegevens van je restaurant.</p>
      </div>

      <Card className="space-y-4 rounded-xl border-slate-200 p-5 shadow-sm">
        <div className="grid gap-4 sm:grid-cols-2">
          <div><Label>Restaurantnaam</Label><Input value={form.name} onChange={upd("name")} className="mt-1.5" data-testid="profile-name-input" /></div>
          <div><Label>Logo URL (optioneel)</Label><Input value={form.logo} onChange={upd("logo")} placeholder="https://..." className="mt-1.5" /></div>
        </div>
        <div><Label>Omschrijving</Label><Textarea value={form.description} onChange={upd("description")} className="mt-1.5" data-testid="profile-desc-input" /></div>
        <div className="grid gap-4 sm:grid-cols-2">
          <div><Label>Telefoon</Label><Input value={form.phone} onChange={upd("phone")} className="mt-1.5" data-testid="profile-phone-input" /></div>
          <div><Label>E-mail</Label><Input value={form.email} onChange={upd("email")} className="mt-1.5" /></div>
        </div>
      </Card>

      <Card className="space-y-4 rounded-xl border-slate-200 p-5 shadow-sm">
        <h2 className="font-heading text-lg font-semibold text-slate-900">Adres</h2>
        <p className="-mt-2 text-sm text-slate-500">Nodig voor het berekenen van bezorgafstanden.</p>
        <div className="grid gap-4 sm:grid-cols-[2fr_1fr]">
          <div><Label>Straat</Label><Input value={form.street} onChange={upd("street")} className="mt-1.5" data-testid="profile-street-input" /></div>
          <div><Label>Huisnummer</Label><Input value={form.houseNumber} onChange={upd("houseNumber")} className="mt-1.5" data-testid="profile-housenr-input" /></div>
        </div>
        <div className="grid gap-4 sm:grid-cols-[1fr_2fr]">
          <div><Label>Postcode</Label><Input value={form.postalCode} onChange={upd("postalCode")} className="mt-1.5" data-testid="profile-postal-input" /></div>
          <div><Label>Stad</Label><Input value={form.city} onChange={upd("city")} className="mt-1.5" data-testid="profile-city-input" /></div>
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <Label>Land</Label>
            <select value={form.country} onChange={upd("country")} className="mt-1.5 h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm">
              <option value="BE">België</option>
              <option value="NL">Nederland</option>
            </select>
          </div>
          <div>
            <Label>Standaardtaal</Label>
            <select value={form.defaultLanguage} onChange={upd("defaultLanguage")} className="mt-1.5 h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm" data-testid="profile-language-select">
              <option value="nl">Nederlands</option>
              <option value="fr">Frans</option>
              <option value="en">Engels</option>
            </select>
          </div>
        </div>
      </Card>

      <div className="flex justify-end">
        <Button onClick={save} disabled={saving} className="bg-emerald-600 hover:bg-emerald-700" data-testid="profile-save-button">
          {saving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />} Opslaan
        </Button>
      </div>
    </div>
  );
}
