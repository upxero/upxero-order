import { useEffect, useRef, useState } from "react";
import { Loader2, Upload, Trash2, Image as ImageIcon, FileText } from "lucide-react";
import { toast } from "sonner";
import api, { apiError } from "../../lib/api";
import { useAuth } from "../../context/AuthContext";
import { useT } from "../../context/I18nContext";
import { resolveFileUrl, logoUrl, menuFileUrl } from "../../lib/files";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { Textarea } from "../../components/ui/textarea";
import { Card } from "../../components/ui/card";

const IMG_TYPES = ["image/jpeg", "image/png", "image/webp"];
const MENU_TYPES = ["application/pdf", "image/jpeg", "image/png"];

export default function Profile() {
  const { refetch } = useAuth();
  const t = useT();
  const [form, setForm] = useState(null);
  const [saving, setSaving] = useState(false);
  const [slug, setSlug] = useState("");
  const [logoFileId, setLogoFileId] = useState("");
  const [logoBusy, setLogoBusy] = useState(false);
  const [menu, setMenu] = useState({ id: "", name: "", type: "" });
  const [menuBusy, setMenuBusy] = useState(false);
  const logoRef = useRef();
  const menuRef = useRef();

  const hydrate = (data) => {
    setForm({
      name: data.name || "", description: data.description || "", logo: data.logo || "",
      phone: data.phone || "", email: data.email || "", street: data.street || "",
      houseNumber: data.houseNumber || "", postalCode: data.postalCode || "", city: data.city || "",
      country: data.country || "BE", defaultLanguage: data.defaultLanguage || "nl",
    });
    setSlug(data.slug || "");
    setLogoFileId(data.logoFileId || "");
    setMenu({ id: data.menuFileId || "", name: data.menuFileName || "", type: data.menuFileType || "" });
  };

  useEffect(() => { api.get("/restaurant/me").then(({ data }) => hydrate(data)); }, []);

  if (!form) return <div className="grid place-items-center py-20"><Loader2 className="h-6 w-6 animate-spin text-emerald-600" /></div>;

  const upd = (k) => (e) => setForm({ ...form, [k]: e.target.value });
  const logoSrc = logoFileId ? logoUrl(slug, logoFileId) : resolveFileUrl(form.logo);

  const save = async () => {
    setSaving(true);
    try {
      await api.put("/restaurant/profile", form);
      toast.success(t("Profiel opgeslagen. Adres wordt automatisch gelokaliseerd voor bezorging."));
      refetch();
    } catch (e) { toast.error(t(apiError(e))); } finally { setSaving(false); }
  };

  const uploadLogo = async (e) => {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    if (!IMG_TYPES.includes(file.type)) { toast.error(t("Alleen JPG, PNG of WebP.")); return; }
    if (file.size > 5 * 1024 * 1024) { toast.error(t("Logo is te groot (max 5 MB).")); return; }
    setLogoBusy(true);
    try {
      const fd = new FormData(); fd.append("file", file);
      const { data } = await api.post("/restaurant/logo", fd);
      setLogoFileId(data.logoFileId);
      toast.success(t("Logo geüpload."));
      refetch();
    } catch (err) { toast.error(t(apiError(err))); } finally { setLogoBusy(false); }
  };

  const removeLogo = async () => {
    setLogoBusy(true);
    try {
      await api.delete("/restaurant/logo");
      setLogoFileId("");
      toast.success(t("Logo verwijderd."));
      refetch();
    } catch (err) { toast.error(t(apiError(err))); } finally { setLogoBusy(false); }
  };

  const uploadMenu = async (e) => {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    if (!MENU_TYPES.includes(file.type)) { toast.error(t("Alleen PDF, JPG of PNG.")); return; }
    if (file.size > 10 * 1024 * 1024) { toast.error(t("Bestand is te groot (max 10 MB).")); return; }
    setMenuBusy(true);
    try {
      const fd = new FormData(); fd.append("file", file);
      const { data } = await api.post("/restaurant/menu-file", fd);
      setMenu({ id: data.menuFileId, name: data.menuFileName, type: data.menuFileType });
      toast.success(t("Menukaart geüpload."));
    } catch (err) { toast.error(t(apiError(err))); } finally { setMenuBusy(false); }
  };

  const removeMenu = async () => {
    setMenuBusy(true);
    try {
      await api.delete("/restaurant/menu-file");
      setMenu({ id: "", name: "", type: "" });
      toast.success(t("Menukaart verwijderd."));
    } catch (err) { toast.error(t(apiError(err))); } finally { setMenuBusy(false); }
  };

  return (
    <div className="space-y-6" data-testid="profile-page">
      <div>
        <h1 className="font-heading text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl">{t("Profiel")}</h1>
        <p className="mt-1 text-sm text-slate-500">{t("Gegevens van je restaurant.")}</p>
      </div>

      <Card className="space-y-4 rounded-xl border-slate-200 p-5 shadow-sm">
        <div><Label>{t("Restaurantnaam")}</Label><Input value={form.name} onChange={upd("name")} className="mt-1.5" data-testid="profile-name-input" /></div>

        <div>
          <Label>{t("Logo")}</Label>
          <div className="mt-1.5 flex items-center gap-4">
            <div className="grid h-20 w-20 shrink-0 place-items-center overflow-hidden rounded-lg border border-slate-200 bg-slate-50">
              {logoSrc ? <img src={logoSrc} alt="Logo" className="h-full w-full object-contain" data-testid="profile-logo-preview" /> : <ImageIcon className="h-6 w-6 text-slate-300" />}
            </div>
            <div className="flex flex-wrap gap-2">
              <input ref={logoRef} type="file" accept="image/jpeg,image/png,image/webp" className="hidden" onChange={uploadLogo} data-testid="profile-logo-input" />
              <Button type="button" variant="outline" disabled={logoBusy} onClick={() => logoRef.current?.click()} className="border-slate-300" data-testid="profile-logo-upload">
                {logoBusy ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Upload className="mr-2 h-4 w-4" />} {logoFileId ? t("Vervangen") : t("Uploaden")}
              </Button>
              {logoFileId && (
                <Button type="button" variant="outline" disabled={logoBusy} onClick={removeLogo} className="border-slate-300 text-rose-600 hover:bg-rose-50" data-testid="profile-logo-remove">
                  <Trash2 className="mr-2 h-4 w-4" /> {t("Verwijderen")}
                </Button>
              )}
            </div>
          </div>
          <p className="mt-1.5 text-xs text-slate-400">{t("JPG, PNG of WebP · max 5 MB. Wordt getoond op je bestelpagina.")}</p>
        </div>

        <div><Label>{t("Omschrijving")}</Label><Textarea value={form.description} onChange={upd("description")} className="mt-1.5" data-testid="profile-desc-input" /></div>
        <div className="grid gap-4 sm:grid-cols-2">
          <div><Label>{t("Telefoon")}</Label><Input value={form.phone} onChange={upd("phone")} className="mt-1.5" data-testid="profile-phone-input" /></div>
          <div><Label>{t("E-mail")}</Label><Input value={form.email} onChange={upd("email")} className="mt-1.5" /></div>
        </div>
      </Card>

      <Card className="space-y-4 rounded-xl border-slate-200 p-5 shadow-sm">
        <div>
          <h2 className="font-heading text-lg font-semibold text-slate-900">{t("Menukaart")}</h2>
          <p className="-mt-0.5 text-sm text-slate-500">{t("Upload je menukaart als PDF, JPG of PNG (max 10 MB).")}</p>
        </div>
        {menu.id ? (
          <div className="flex flex-wrap items-center gap-3">
            <a href={menuFileUrl(slug, menu.id)} target="_blank" rel="noreferrer"
              className="inline-flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50" data-testid="menu-file-view">
              <FileText className="h-4 w-4 text-emerald-600" /> {menu.name || t("Menukaart bekijken")}
            </a>
            <input ref={menuRef} type="file" accept="application/pdf,image/jpeg,image/png" className="hidden" onChange={uploadMenu} data-testid="menu-file-input" />
            <Button type="button" variant="outline" disabled={menuBusy} onClick={() => menuRef.current?.click()} className="border-slate-300" data-testid="menu-file-replace">
              {menuBusy ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Upload className="mr-2 h-4 w-4" />} {t("Vervangen")}
            </Button>
            <Button type="button" variant="outline" disabled={menuBusy} onClick={removeMenu} className="border-slate-300 text-rose-600 hover:bg-rose-50" data-testid="menu-file-remove">
              <Trash2 className="mr-2 h-4 w-4" /> {t("Verwijderen")}
            </Button>
          </div>
        ) : (
          <div>
            <input ref={menuRef} type="file" accept="application/pdf,image/jpeg,image/png" className="hidden" onChange={uploadMenu} data-testid="menu-file-input" />
            <Button type="button" variant="outline" disabled={menuBusy} onClick={() => menuRef.current?.click()} className="border-slate-300" data-testid="menu-file-upload">
              {menuBusy ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Upload className="mr-2 h-4 w-4" />} {t("Menukaart uploaden")}
            </Button>
          </div>
        )}
      </Card>

      <Card className="space-y-4 rounded-xl border-slate-200 p-5 shadow-sm">
        <h2 className="font-heading text-lg font-semibold text-slate-900">{t("Adres")}</h2>
        <p className="-mt-2 text-sm text-slate-500">{t("Nodig voor het berekenen van bezorgafstanden.")}</p>
        <div className="grid gap-4 sm:grid-cols-[2fr_1fr]">
          <div><Label>{t("Straat")}</Label><Input value={form.street} onChange={upd("street")} className="mt-1.5" data-testid="profile-street-input" /></div>
          <div><Label>{t("Huisnummer")}</Label><Input value={form.houseNumber} onChange={upd("houseNumber")} className="mt-1.5" data-testid="profile-housenr-input" /></div>
        </div>
        <div className="grid gap-4 sm:grid-cols-[1fr_2fr]">
          <div><Label>{t("Postcode")}</Label><Input value={form.postalCode} onChange={upd("postalCode")} className="mt-1.5" data-testid="profile-postal-input" /></div>
          <div><Label>{t("Stad")}</Label><Input value={form.city} onChange={upd("city")} className="mt-1.5" data-testid="profile-city-input" /></div>
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <Label>{t("Land")}</Label>
            <select value={form.country} onChange={upd("country")} className="mt-1.5 h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm">
              <option value="BE">{t("België")}</option>
              <option value="NL">{t("Nederland")}</option>
            </select>
          </div>
          <div>
            <Label>{t("Taal / Language")}</Label>
            <select value={form.defaultLanguage === "nl" ? "nl" : "en"} onChange={upd("defaultLanguage")} className="mt-1.5 h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm" data-testid="profile-language-select">
              <option value="en">English</option>
              <option value="nl">Nederlands</option>
            </select>
          </div>
        </div>
      </Card>

      <div className="flex justify-end">
        <Button onClick={save} disabled={saving} className="bg-emerald-600 hover:bg-emerald-700" data-testid="profile-save-button">
          {saving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />} {t("Opslaan")}
        </Button>
      </div>
    </div>
  );
}
