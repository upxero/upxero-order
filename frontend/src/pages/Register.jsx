import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Loader2 } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { apiError } from "../lib/api";
import { makeT } from "../lib/i18n";
import { usePublicLang } from "../lib/publicLang";
import { AuthTopBar, BackHome } from "../components/AuthTopBar";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";

export default function Register() {
  const { register, user } = useAuth();
  const navigate = useNavigate();
  const [lang, setLang] = usePublicLang();
  const t = makeT(lang);
  const [form, setForm] = useState({ restaurantName: "", name: "", email: "", password: "" });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (user) navigate("/dashboard", { replace: true });
  }, [user, navigate]);

  const upd = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await register({ ...form, language: lang });
      toast.success(t("Restaurant aangemaakt! Check je inbox om je e-mailadres te bevestigen."));
      navigate("/dashboard", { replace: true });
    } catch (err) {
      toast.error(t(apiError(err, "Registratie mislukt")));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 px-6 py-12">
      <div className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
        <AuthTopBar lang={lang} setLang={setLang} />
        <BackHome lang={lang} />
        <h1 className="mt-6 font-heading text-2xl font-bold tracking-tight text-slate-900">{t("Registreer je restaurant")}</h1>
        <p className="mt-2 text-sm text-slate-500">{t("Maak een account aan en je restaurant staat meteen klaar.")}</p>

        <form onSubmit={submit} className="mt-6 space-y-4" data-testid="register-form">
          <div>
            <Label htmlFor="restaurantName">{t("Naam restaurant")}</Label>
            <Input id="restaurantName" value={form.restaurantName} onChange={upd("restaurantName")} required
              placeholder="Bistro De Hoek" className="mt-1.5" data-testid="register-restaurant-input" />
          </div>
          <div>
            <Label htmlFor="name">{t("Je naam")}</Label>
            <Input id="name" value={form.name} onChange={upd("name")} required
              placeholder={t("Jan Jansen")} className="mt-1.5" data-testid="register-name-input" />
          </div>
          <div>
            <Label htmlFor="email">{t("E-mailadres")}</Label>
            <Input id="email" type="email" value={form.email} onChange={upd("email")} required
              placeholder={t("jij@restaurant.nl")} className="mt-1.5" data-testid="register-email-input" />
          </div>
          <div>
            <Label htmlFor="password">{t("Wachtwoord")}</Label>
            <Input id="password" type="password" value={form.password} onChange={upd("password")} required
              minLength={6} placeholder={t("Minimaal 6 tekens")} className="mt-1.5" data-testid="register-password-input" />
          </div>
          <p className="text-xs text-slate-500">{t("We sturen je een e-mail om je adres te bevestigen.")}</p>
          <Button type="submit" disabled={loading} className="w-full bg-emerald-600 hover:bg-emerald-700" data-testid="register-submit-button">
            {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            {t("Account aanmaken")}
          </Button>
        </form>

        <p className="mt-6 text-sm text-slate-500">
          {t("Heb je al een account?")}{" "}
          <Link to="/login" className="font-semibold text-emerald-600 hover:underline" data-testid="register-to-login">{t("Inloggen")}</Link>
        </p>
      </div>
    </div>
  );
}
