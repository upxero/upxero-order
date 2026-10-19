import { useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { Loader2, MailCheck } from "lucide-react";
import api, { apiError } from "../lib/api";
import { makeT } from "../lib/i18n";
import { usePublicLang } from "../lib/publicLang";
import { AuthTopBar, BackHome } from "../components/AuthTopBar";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";

export default function ForgotPassword() {
  const [lang, setLang] = usePublicLang();
  const t = makeT(lang);
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await api.post("/auth/forgot-password", { email, language: lang });
      setSent(true);
    } catch (err) {
      toast.error(t(apiError(err)));
    } finally {
      setLoading(false);
    }
  };

  const backLogin = (id) => (
    <Link to="/login" className="mt-6 inline-block text-sm font-semibold text-emerald-600 hover:underline" data-testid={id}>
      {t("Terug naar inloggen")}
    </Link>
  );

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 px-6 py-12">
      <div className="w-full max-w-sm rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
        <AuthTopBar lang={lang} setLang={setLang} />
        <BackHome lang={lang} />
        {sent ? (
          <div className="mt-8 text-center" data-testid="forgot-sent">
            <span className="mx-auto grid h-12 w-12 place-items-center rounded-full bg-emerald-100 text-emerald-600"><MailCheck className="h-6 w-6" /></span>
            <h1 className="mt-4 font-heading text-xl font-bold text-slate-900">{t("Check je e-mail")}</h1>
            <p className="mt-2 text-sm text-slate-500">{t("Als dit e-mailadres bij ons bekend is, hebben we een resetlink verstuurd. De link verloopt binnen 1 uur.")}</p>
            {backLogin("forgot-back-login")}
          </div>
        ) : (
          <>
            <h1 className="mt-6 font-heading text-2xl font-bold tracking-tight text-slate-900">{t("Wachtwoord vergeten?")}</h1>
            <p className="mt-2 text-sm text-slate-500">{t("Vul je e-mailadres in en we sturen je een link om je wachtwoord opnieuw in te stellen.")}</p>
            <form onSubmit={submit} className="mt-6 space-y-4" data-testid="forgot-form">
              <div>
                <Label htmlFor="email">{t("E-mailadres")}</Label>
                <Input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required
                  placeholder={t("jij@restaurant.nl")} className="mt-1.5" data-testid="forgot-email-input" />
              </div>
              <Button type="submit" disabled={loading} className="w-full bg-emerald-600 hover:bg-emerald-700" data-testid="forgot-submit-button">
                {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />} {t("Verstuur resetlink")}
              </Button>
            </form>
            {backLogin("forgot-to-login")}
          </>
        )}
      </div>
    </div>
  );
}
