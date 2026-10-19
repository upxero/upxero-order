import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import { Loader2 } from "lucide-react";
import api, { apiError } from "../lib/api";
import { makeT } from "../lib/i18n";
import { usePublicLang } from "../lib/publicLang";
import { AuthTopBar, BackHome } from "../components/AuthTopBar";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";

export default function ResetPassword() {
  const [params] = useSearchParams();
  const token = params.get("token") || "";
  const navigate = useNavigate();
  const [lang, setLang] = usePublicLang();
  const t = makeT(lang);
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    if (password !== confirm) { toast.error(t("Wachtwoorden komen niet overeen")); return; }
    setLoading(true);
    try {
      await api.post("/auth/reset-password", { token, password });
      toast.success(t("Je wachtwoord is gewijzigd. Log in met je nieuwe wachtwoord."));
      navigate("/login", { replace: true });
    } catch (err) {
      toast.error(t(apiError(err)));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 px-6 py-12">
      <div className="w-full max-w-sm rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
        <AuthTopBar lang={lang} setLang={setLang} />
        <BackHome lang={lang} />
        <h1 className="mt-6 font-heading text-2xl font-bold tracking-tight text-slate-900">{t("Nieuw wachtwoord")}</h1>
        {!token ? (
          <p className="mt-4 rounded-lg bg-rose-50 p-3 text-sm font-medium text-rose-700" data-testid="reset-no-token">
            {t("Ongeldige of ontbrekende resetlink. Vraag een nieuwe aan.")}
          </p>
        ) : (
          <form onSubmit={submit} className="mt-6 space-y-4" data-testid="reset-form">
            <div>
              <Label htmlFor="password">{t("Nieuw wachtwoord")}</Label>
              <Input id="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required
                minLength={6} placeholder={t("Minimaal 6 tekens")} className="mt-1.5" data-testid="reset-password-input" />
            </div>
            <div>
              <Label htmlFor="confirm">{t("Bevestig wachtwoord")}</Label>
              <Input id="confirm" type="password" value={confirm} onChange={(e) => setConfirm(e.target.value)} required
                minLength={6} placeholder={t("Herhaal wachtwoord")} className="mt-1.5" data-testid="reset-confirm-input" />
            </div>
            <Button type="submit" disabled={loading} className="w-full bg-emerald-600 hover:bg-emerald-700" data-testid="reset-submit-button">
              {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />} {t("Wachtwoord opslaan")}
            </Button>
          </form>
        )}
        <Link to="/login" className="mt-6 inline-block text-sm font-semibold text-emerald-600 hover:underline" data-testid="reset-to-login">{t("Terug naar inloggen")}</Link>
      </div>
    </div>
  );
}
