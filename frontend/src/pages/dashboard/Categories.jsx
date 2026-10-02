import { useEffect, useState } from "react";
import { FolderTree, Plus, Pencil, Trash2, Loader2 } from "lucide-react";
import { toast } from "sonner";
import api, { apiError } from "../../lib/api";
import { useT } from "../../context/I18nContext";
import { EmptyState } from "../../components/EmptyState";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { Textarea } from "../../components/ui/textarea";
import { Switch } from "../../components/ui/switch";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "../../components/ui/dialog";

const empty = { name: "", description: "", sortOrder: 0, isActive: true };

export default function Categories() {
  const t = useT();
  const [cats, setCats] = useState(null);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(empty);
  const [saving, setSaving] = useState(false);

  const load = () => api.get("/menu/categories").then(({ data }) => setCats(data)).catch(() => setCats([]));
  useEffect(() => { load(); }, []);

  const openNew = () => { setEditing(null); setForm({ ...empty, sortOrder: cats?.length || 0 }); setOpen(true); };
  const openEdit = (c) => { setEditing(c); setForm({ name: c.name, description: c.description || "", sortOrder: c.sortOrder, isActive: c.isActive }); setOpen(true); };

  const save = async () => {
    setSaving(true);
    try {
      if (editing) await api.put(`/menu/categories/${editing.id}`, form);
      else await api.post("/menu/categories", form);
      toast.success(t("Categorie opgeslagen"));
      setOpen(false);
      await load();
    } catch (e) { toast.error(t(apiError(e))); } finally { setSaving(false); }
  };

  const remove = async (c) => {
    if (!window.confirm(t("\"{name}\" verwijderen? Producten in deze categorie worden ook verwijderd.", { name: c.name }))) return;
    try { await api.delete(`/menu/categories/${c.id}`); toast.success(t("Categorie verwijderd")); await load(); }
    catch (e) { toast.error(t(apiError(e))); }
  };

  return (
    <div className="space-y-6" data-testid="categories-page">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h1 className="font-heading text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl">{t("Categorieën")}</h1>
          <p className="mt-1 text-sm text-slate-500">{t("Groepeer je producten in categorieën.")}</p>
        </div>
        <Button onClick={openNew} className="bg-emerald-600 hover:bg-emerald-700" data-testid="category-add-button">
          <Plus className="mr-2 h-4 w-4" /> {t("Nieuwe categorie")}
        </Button>
      </div>

      {cats === null ? (
        <div className="grid place-items-center py-20"><Loader2 className="h-6 w-6 animate-spin text-emerald-600" /></div>
      ) : cats.length === 0 ? (
        <EmptyState icon={FolderTree} title={t("Nog geen categorieën")} description={t("Maak je eerste categorie aan, bijvoorbeeld 'Burgers' of 'Dranken'.")}
          action={<Button onClick={openNew} className="bg-emerald-600 hover:bg-emerald-700" data-testid="category-add-empty">{t("Nieuwe categorie")}</Button>} testid="categories-empty" />
      ) : (
        <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
          {cats.map((c, i) => (
            <div key={c.id} className={`flex items-center justify-between gap-3 px-4 py-3.5 ${i > 0 ? "border-t border-slate-100" : ""}`} data-testid={`category-row-${c.id}`}>
              <div className="min-w-0">
                <p className="flex items-center gap-2 font-semibold text-slate-900">
                  {c.name}
                  {!c.isActive && <span className="rounded bg-slate-100 px-1.5 py-0.5 text-xs font-medium text-slate-500">{t("Inactief")}</span>}
                </p>
                {c.description && <p className="truncate text-sm text-slate-500">{c.description}</p>}
              </div>
              <div className="flex items-center gap-1">
                <Button variant="ghost" size="icon" onClick={() => openEdit(c)} data-testid={`category-edit-${c.id}`}><Pencil className="h-4 w-4 text-slate-500" /></Button>
                <Button variant="ghost" size="icon" onClick={() => remove(c)} data-testid={`category-delete-${c.id}`}><Trash2 className="h-4 w-4 text-rose-500" /></Button>
              </div>
            </div>
          ))}
        </div>
      )}

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="sm:max-w-md" data-testid="category-dialog">
          <DialogHeader><DialogTitle>{editing ? t("Categorie bewerken") : t("Nieuwe categorie")}</DialogTitle></DialogHeader>
          <div className="space-y-4">
            <div>
              <Label htmlFor="c-name">{t("Naam")}</Label>
              <Input id="c-name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="mt-1.5" data-testid="category-name-input" />
            </div>
            <div>
              <Label htmlFor="c-desc">{t("Omschrijving (optioneel)")}</Label>
              <Textarea id="c-desc" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} className="mt-1.5" />
            </div>
            <div className="flex items-center justify-between">
              <div>
                <Label>{t("Sorteervolgorde")}</Label>
                <Input type="number" value={form.sortOrder} onChange={(e) => setForm({ ...form, sortOrder: Number(e.target.value) })} className="mt-1.5 w-24" />
              </div>
              <div className="flex items-center gap-2">
                <Switch checked={form.isActive} onCheckedChange={(v) => setForm({ ...form, isActive: v })} data-testid="category-active-switch" />
                <Label>{t("Actief")}</Label>
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setOpen(false)}>{t("Annuleren")}</Button>
            <Button onClick={save} disabled={saving || !form.name} className="bg-emerald-600 hover:bg-emerald-700" data-testid="category-save-button">
              {saving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />} {t("Opslaan")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
