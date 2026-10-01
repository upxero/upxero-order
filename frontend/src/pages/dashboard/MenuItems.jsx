import { useEffect, useRef, useState } from "react";
import { UtensilsCrossed, Plus, Pencil, Trash2, Loader2, X, Upload, Image as ImageIcon } from "lucide-react";
import { toast } from "sonner";
import api, { apiError } from "../../lib/api";
import { euro } from "../../lib/format";
import { useAuth } from "../../context/AuthContext";
import { resolveFileUrl, menuItemImageUrl } from "../../lib/files";
import { EmptyState } from "../../components/EmptyState";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { Textarea } from "../../components/ui/textarea";
import { Switch } from "../../components/ui/switch";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "../../components/ui/dialog";

const emptyItem = {
  categoryId: "", name: "", description: "", price: "", image: "",
  sortOrder: 0, isAvailable: true, optionGroups: [],
  imageFile: null, imageFileId: "",
};
const IMG_TYPES = ["image/jpeg", "image/png", "image/webp"];

export default function MenuItems() {
  const { restaurant } = useAuth();
  const slug = restaurant?.slug;
  const [items, setItems] = useState(null);
  const [cats, setCats] = useState([]);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(emptyItem);
  const [saving, setSaving] = useState(false);
  const imgRef = useRef();

  const load = async () => {
    const [i, c] = await Promise.all([api.get("/menu/items"), api.get("/menu/categories")]);
    setItems(i.data); setCats(c.data);
  };
  useEffect(() => { load().catch(() => setItems([])); }, []);

  const catName = (id) => cats.find((c) => c.id === id)?.name || "—";
  const listImg = (it) => it.imageFileId ? menuItemImageUrl(slug, it.id, it.imageFileId) : resolveFileUrl(it.image);

  const openNew = () => {
    if (cats.length === 0) { toast.error("Maak eerst een categorie aan."); return; }
    setEditing(null);
    setForm({ ...emptyItem, categoryId: cats[0].id, sortOrder: items?.length || 0 });
    setOpen(true);
  };
  const openEdit = (it) => {
    setEditing(it);
    setForm({ categoryId: it.categoryId, name: it.name, description: it.description || "", price: it.price,
      image: it.image || "", sortOrder: it.sortOrder, isAvailable: it.isAvailable,
      imageFile: null, imageFileId: it.imageFileId || "",
      optionGroups: JSON.parse(JSON.stringify(it.optionGroups || [])) });
    setOpen(true);
  };

  const onPickImage = (e) => {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    if (!IMG_TYPES.includes(file.type)) { toast.error("Alleen JPG, PNG of WebP."); return; }
    if (file.size > 5 * 1024 * 1024) { toast.error("Afbeelding is te groot (max 5 MB)."); return; }
    setForm((f) => ({ ...f, imageFile: file }));
  };

  const removeImage = async () => {
    if (editing && form.imageFileId) {
      try { await api.delete(`/menu/items/${editing.id}/image`); } catch (e) { toast.error(apiError(e)); return; }
    }
    setForm((f) => ({ ...f, imageFile: null, imageFileId: "" }));
  };

  const previewSrc = form.imageFile ? URL.createObjectURL(form.imageFile)
    : (form.imageFileId && editing ? menuItemImageUrl(slug, editing.id, form.imageFileId) : resolveFileUrl(form.image));

  const save = async () => {
    setSaving(true);
    try {
      const payload = {
        categoryId: form.categoryId, name: form.name, description: form.description,
        price: parseFloat(form.price) || 0, image: form.image,
        sortOrder: form.sortOrder, isAvailable: form.isAvailable,
        optionGroups: form.optionGroups.map((g) => ({ ...g, options: g.options.map((o) => ({ ...o, price: parseFloat(o.price) || 0 })) })),
      };
      let itemId = editing?.id;
      if (editing) await api.put(`/menu/items/${editing.id}`, payload);
      else { const { data } = await api.post("/menu/items", payload); itemId = data.id; }
      if (form.imageFile && itemId) {
        const fd = new FormData(); fd.append("file", form.imageFile);
        await api.post(`/menu/items/${itemId}/image`, fd);
      }
      toast.success("Product opgeslagen");
      setOpen(false);
      await load();
    } catch (e) { toast.error(apiError(e)); } finally { setSaving(false); }
  };

  const toggleAvail = async (it) => {
    try {
      await api.patch(`/menu/items/${it.id}/availability`, { isAvailable: !it.isAvailable });
      await load();
    } catch (e) { toast.error(apiError(e)); }
  };

  const remove = async (it) => {
    if (!window.confirm(`"${it.name}" verwijderen?`)) return;
    try { await api.delete(`/menu/items/${it.id}`); toast.success("Product verwijderd"); await load(); }
    catch (e) { toast.error(apiError(e)); }
  };

  const addGroup = () => setForm((f) => ({ ...f, optionGroups: [...f.optionGroups, { name: "", required: false, multiple: false, options: [{ name: "", price: "" }] }] }));
  const updGroup = (gi, patch) => setForm((f) => { const g = [...f.optionGroups]; g[gi] = { ...g[gi], ...patch }; return { ...f, optionGroups: g }; });
  const removeGroup = (gi) => setForm((f) => ({ ...f, optionGroups: f.optionGroups.filter((_, i) => i !== gi) }));
  const addOption = (gi) => setForm((f) => { const g = [...f.optionGroups]; g[gi].options = [...g[gi].options, { name: "", price: "" }]; return { ...f, optionGroups: g }; });
  const updOption = (gi, oi, patch) => setForm((f) => { const g = [...f.optionGroups]; g[gi].options[oi] = { ...g[gi].options[oi], ...patch }; return { ...f, optionGroups: g }; });
  const removeOption = (gi, oi) => setForm((f) => { const g = [...f.optionGroups]; g[gi].options = g[gi].options.filter((_, i) => i !== oi); return { ...f, optionGroups: g }; });

  return (
    <div className="space-y-6" data-testid="menu-page">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h1 className="font-heading text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl">Menu</h1>
          <p className="mt-1 text-sm text-slate-500">Beheer je producten, prijzen en opties.</p>
        </div>
        <Button onClick={openNew} className="bg-emerald-600 hover:bg-emerald-700" data-testid="menu-add-button">
          <Plus className="mr-2 h-4 w-4" /> Nieuw product
        </Button>
      </div>

      {items === null ? (
        <div className="grid place-items-center py-20"><Loader2 className="h-6 w-6 animate-spin text-emerald-600" /></div>
      ) : items.length === 0 ? (
        <EmptyState icon={UtensilsCrossed} title="Je menu is nog leeg" description="Voeg je eerste product toe."
          action={<Button onClick={openNew} className="bg-emerald-600 hover:bg-emerald-700" data-testid="menu-add-empty">Nieuw product</Button>} testid="menu-empty" />
      ) : (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          {items.map((it) => {
            const img = listImg(it);
            return (
            <div key={it.id} className="flex gap-4 rounded-xl border border-slate-200 bg-white p-4 shadow-sm" data-testid={`menu-item-${it.id}`}>
              {img ? (
                <img src={img} alt={it.name} className="h-20 w-20 shrink-0 rounded-lg object-cover" data-testid={`menu-item-img-${it.id}`} />
              ) : (
                <div className="grid h-20 w-20 shrink-0 place-items-center rounded-lg bg-slate-100 text-slate-300"><UtensilsCrossed className="h-6 w-6" /></div>
              )}
              <div className="min-w-0 flex-1">
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <p className="truncate font-semibold text-slate-900">{it.name}</p>
                    <p className="text-xs font-medium text-emerald-600">{catName(it.categoryId)}</p>
                  </div>
                  <span className="tabular font-semibold text-slate-900">{euro(it.price)}</span>
                </div>
                {it.description && <p className="mt-1 line-clamp-2 text-sm text-slate-500">{it.description}</p>}
                <div className="mt-2 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Switch checked={it.isAvailable} onCheckedChange={() => toggleAvail(it)} data-testid={`menu-avail-${it.id}`} />
                    <span className={`text-xs font-medium ${it.isAvailable ? "text-emerald-600" : "text-slate-400"}`}>{it.isAvailable ? "Beschikbaar" : "Niet beschikbaar"}</span>
                  </div>
                  <div className="flex gap-1">
                    <Button variant="ghost" size="icon" onClick={() => openEdit(it)} data-testid={`menu-edit-${it.id}`}><Pencil className="h-4 w-4 text-slate-500" /></Button>
                    <Button variant="ghost" size="icon" onClick={() => remove(it)} data-testid={`menu-delete-${it.id}`}><Trash2 className="h-4 w-4 text-rose-500" /></Button>
                  </div>
                </div>
              </div>
            </div>
          );})}
        </div>
      )}

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-h-[90vh] overflow-y-auto scroll-thin sm:max-w-2xl" data-testid="menu-dialog">
          <DialogHeader><DialogTitle>{editing ? "Product bewerken" : "Nieuw product"}</DialogTitle></DialogHeader>
          <div className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <Label>Naam</Label>
                <Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="mt-1.5" data-testid="menu-name-input" />
              </div>
              <div>
                <Label>Categorie</Label>
                <select value={form.categoryId} onChange={(e) => setForm({ ...form, categoryId: e.target.value })}
                  className="mt-1.5 h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm" data-testid="menu-category-select">
                  {cats.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
                </select>
              </div>
            </div>
            <div>
              <Label>Omschrijving</Label>
              <Textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} className="mt-1.5" />
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <Label>Prijs (€)</Label>
                <Input type="number" step="0.01" min="0" value={form.price} onChange={(e) => setForm({ ...form, price: e.target.value })} className="mt-1.5" data-testid="menu-price-input" />
              </div>
              <div>
                <Label>Afbeelding URL (optioneel)</Label>
                <Input value={form.image} onChange={(e) => setForm({ ...form, image: e.target.value })} placeholder="https://..." className="mt-1.5" />
              </div>
            </div>

            <div>
              <Label>Afbeelding uploaden</Label>
              <div className="mt-1.5 flex items-center gap-4">
                <div className="grid h-20 w-20 shrink-0 place-items-center overflow-hidden rounded-lg border border-slate-200 bg-slate-50">
                  {previewSrc ? <img src={previewSrc} alt="Voorbeeld" className="h-full w-full object-cover" data-testid="menu-image-preview" /> : <ImageIcon className="h-6 w-6 text-slate-300" />}
                </div>
                <div className="flex flex-wrap gap-2">
                  <input ref={imgRef} type="file" accept="image/jpeg,image/png,image/webp" className="hidden" onChange={onPickImage} data-testid="menu-image-input" />
                  <Button type="button" variant="outline" size="sm" onClick={() => imgRef.current?.click()} className="border-slate-300" data-testid="menu-image-upload">
                    <Upload className="mr-2 h-4 w-4" /> {(form.imageFile || form.imageFileId) ? "Vervangen" : "Uploaden"}
                  </Button>
                  {(form.imageFile || form.imageFileId) && (
                    <Button type="button" variant="outline" size="sm" onClick={removeImage} className="border-slate-300 text-rose-600 hover:bg-rose-50" data-testid="menu-image-remove">
                      <Trash2 className="mr-2 h-4 w-4" /> Verwijderen
                    </Button>
                  )}
                </div>
              </div>
              <p className="mt-1.5 text-xs text-slate-400">JPG, PNG of WebP · max 5 MB.</p>
            </div>

            <div className="flex items-center gap-2">
              <Switch checked={form.isAvailable} onCheckedChange={(v) => setForm({ ...form, isAvailable: v })} />
              <Label>Beschikbaar</Label>
            </div>

            <div className="rounded-lg border border-slate-200 p-3">
              <div className="flex items-center justify-between">
                <Label className="text-sm font-semibold">Optiegroepen</Label>
                <Button type="button" variant="outline" size="sm" onClick={addGroup} className="border-slate-300" data-testid="menu-add-group"><Plus className="mr-1 h-3.5 w-3.5" /> Groep</Button>
              </div>
              {form.optionGroups.length === 0 && <p className="mt-2 text-xs text-slate-400">Bijv. "Saus" of "Extra's". Optioneel.</p>}
              <div className="mt-3 space-y-3">
                {form.optionGroups.map((g, gi) => (
                  <div key={gi} className="rounded-lg bg-slate-50 p-3">
                    <div className="flex items-center gap-2">
                      <Input value={g.name} onChange={(e) => updGroup(gi, { name: e.target.value })} placeholder="Groepnaam" className="h-9 bg-white" />
                      <Button type="button" variant="ghost" size="icon" onClick={() => removeGroup(gi)}><X className="h-4 w-4 text-rose-500" /></Button>
                    </div>
                    <div className="mt-2 flex gap-4 text-xs">
                      <label className="flex items-center gap-1.5"><Switch checked={g.required} onCheckedChange={(v) => updGroup(gi, { required: v })} /> Verplicht</label>
                      <label className="flex items-center gap-1.5"><Switch checked={g.multiple} onCheckedChange={(v) => updGroup(gi, { multiple: v })} /> Meerdere keuzes</label>
                    </div>
                    <div className="mt-2 space-y-2">
                      {g.options.map((o, oi) => (
                        <div key={oi} className="flex items-center gap-2">
                          <Input value={o.name} onChange={(e) => updOption(gi, oi, { name: e.target.value })} placeholder="Optie" className="h-8 bg-white" />
                          <Input type="number" step="0.01" value={o.price} onChange={(e) => updOption(gi, oi, { price: e.target.value })} placeholder="€" className="h-8 w-20 bg-white" />
                          <Button type="button" variant="ghost" size="icon" onClick={() => removeOption(gi, oi)}><X className="h-3.5 w-3.5 text-slate-400" /></Button>
                        </div>
                      ))}
                      <Button type="button" variant="ghost" size="sm" onClick={() => addOption(gi)} className="text-emerald-600"><Plus className="mr-1 h-3.5 w-3.5" /> Optie toevoegen</Button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setOpen(false)}>Annuleren</Button>
            <Button onClick={save} disabled={saving || !form.name || form.price === ""} className="bg-emerald-600 hover:bg-emerald-700" data-testid="menu-save-button">
              {saving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />} Opslaan
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
