import { useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { Loader2, MailCheck } from "lucide-react";
import api, { apiError } from "../lib/api";
import { Logo } from "../components/Logo";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";

export default function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await api.post("/auth/forgot-password", { email });
      setSent(true);
    } catch (err) {
      toast.error(apiError(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 px-6 py-12">
      <div className="w-full max-w-sm rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
        <Logo />
        {sent ? (
          <div className="mt-8 text-center" data-testid="forgot-sent">
            <span className="mx-auto grid h-12 w-12 place-items-center rounded-full bg-emerald-100 text-emerald-600"><MailCheck className="h-6 w-6" /></span>
            <h1 className="mt-4 font-heading text-xl font-bold text-slate-900">Controleer je e-mail</h1>
            <p className="mt-2 text-sm text-slate-500">Als dit e-mailadres bij ons bekend is, hebben we een resetlink verstuurd. De link verloopt binnen 1 uur.</p>
            <Link to="/login" className="mt-6 inline-block text-sm font-semibold text-emerald-600 hover:underline" data-testid="forgot-back-login">Terug naar inloggen</Link>
          </div>
        ) : (
          <>
            <h1 className="mt-8 font-heading text-2xl font-bold tracking-tight text-slate-900">Wachtwoord vergeten?</h1>
            <p className="mt-2 text-sm text-slate-500">Vul je e-mailadres in en we sturen je een link om je wachtwoord opnieuw in te stellen.</p>
            <form onSubmit={submit} className="mt-6 space-y-4" data-testid="forgot-form">
              <div>
                <Label htmlFor="email">E-mailadres</Label>
                <Input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required
                  placeholder="jij@restaurant.be" className="mt-1.5" data-testid="forgot-email-input" />
              </div>
              <Button type="submit" disabled={loading} className="w-full bg-emerald-600 hover:bg-emerald-700" data-testid="forgot-submit-button">
                {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />} Verstuur resetlink
              </Button>
            </form>
            <Link to="/login" className="mt-6 inline-block text-sm font-semibold text-emerald-600 hover:underline" data-testid="forgot-to-login">Terug naar inloggen</Link>
          </>
        )}
      </div>
    </div>
  );
}
