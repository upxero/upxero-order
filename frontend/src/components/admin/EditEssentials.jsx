import { useState } from "react";
import { Loader2 } from "lucide-react";
import { toast } from "sonner";
import api, { apiError } from "../../lib/api";
import { useT } from "../../context/I18nContext";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { Label } from "../ui/label";
import { Textarea } from "../ui/textarea";
import { Card } from "../ui/card";

const FIELDS = ["name", "description", "phone", "email", "street", "houseNumber", "postalCode", "city", "country", "defaultLanguage"];

export function EditEssentials({ restaurant, disabled, onSaved }) {
  const t = useT();
  const [form, setForm] = useState(() => Object.fromEntries(FIELDS.map((k) => [k, restaurant[k] || ""])));
  const [saving, setSaving] = useState(false);
  const upd = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const save = async () => {
    setSaving(true);
    try {
      await api.put(`/admin/restaurants/${restaurant.id}`, { ...form, country: form.country || "BE", defaultLanguage: form.defaultLanguage || "en" });
      toast.success(t("Restaurantgegevens opgeslagen"));
      onSaved();
    } catch (e) { toast.error(t(apiError(e))); } finally { setSaving(false); }
  };

  const field = (k, label, extra = {}) => (
    <div><Label>{t(label)}</Label><Input value={form[k]} onChange={upd(k)} disabled={disabled} className="mt-1.5" data-testid={`admin-edit-${k}`} {...extra} /></div>
  );

  return (
    <Card className="space-y-4 rounded-xl border-slate-200 p-5 shadow-sm" data-testid="admin-edit-card">
      <h2 className="font-heading text-lg font-semibold text-slate-900">{t("Restaurantgegevens bewerken")}</h2>
      {field("name", "Restaurantnaam")}
      <div><Label>{t("Omschrijving")}</Label><Textarea value={form.description} onChange={upd("description")} disabled={disabled} className="mt-1.5" data-testid="admin-edit-description" /></div>
      <div className="grid gap-4 sm:grid-cols-2">{field("phone", "Telefoon")}{field("email", "E-mail")}</div>
      <div className="grid gap-4 sm:grid-cols-[2fr_1fr]">{field("street", "Straat")}{field("houseNumber", "Huisnummer")}</div>
      <div className="grid gap-4 sm:grid-cols-[1fr_2fr]">{field("postalCode", "Postcode")}{field("city", "Stad")}</div>
      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <Label>{t("Land")}</Label>
          <select value={form.country || "BE"} onChange={upd("country")} disabled={disabled} className="mt-1.5 h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm" data-testid="admin-edit-country">
            <option value="BE">{t("België")}</option><option value="NL">{t("Nederland")}</option>
          </select>
        </div>
        <div>
          <Label>{t("Taal / Language")}</Label>
          <select value={form.defaultLanguage === "nl" ? "nl" : "en"} onChange={upd("defaultLanguage")} disabled={disabled} className="mt-1.5 h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm" data-testid="admin-edit-language">
            <option value="en">English</option><option value="nl">Nederlands</option>
          </select>
        </div>
      </div>
      <div className="flex justify-end">
        <Button onClick={save} disabled={saving || disabled || form.name.trim().length < 2} className="bg-emerald-600 hover:bg-emerald-700" data-testid="admin-edit-save">
          {saving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />} {t("Opslaan")}
        </Button>
      </div>
    </Card>
  );
}
