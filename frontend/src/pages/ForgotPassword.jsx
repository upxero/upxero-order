import { useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { Loader2, MailCheck } from "lucide-react";
import api, { apiError } from "../lib/api";
import { makeT } from "../lib/i18n";
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
      toast.error(makeT("en")(apiError(err)));
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
            <h1 className="mt-4 font-heading text-xl font-bold text-slate-900">Check your email</h1>
            <p className="mt-2 text-sm text-slate-500">If this email address is known to us, we've sent a reset link. The link expires within 1 hour.</p>
            <Link to="/login" className="mt-6 inline-block text-sm font-semibold text-emerald-600 hover:underline" data-testid="forgot-back-login">Back to login</Link>
          </div>
        ) : (
          <>
            <h1 className="mt-8 font-heading text-2xl font-bold tracking-tight text-slate-900">Forgot password?</h1>
            <p className="mt-2 text-sm text-slate-500">Enter your email address and we'll send you a link to reset your password.</p>
            <form onSubmit={submit} className="mt-6 space-y-4" data-testid="forgot-form">
              <div>
                <Label htmlFor="email">Email address</Label>
                <Input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required
                  placeholder="you@restaurant.com" className="mt-1.5" data-testid="forgot-email-input" />
              </div>
              <Button type="submit" disabled={loading} className="w-full bg-emerald-600 hover:bg-emerald-700" data-testid="forgot-submit-button">
                {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />} Send reset link
              </Button>
            </form>
            <Link to="/login" className="mt-6 inline-block text-sm font-semibold text-emerald-600 hover:underline" data-testid="forgot-to-login">Back to login</Link>
          </>
        )}
      </div>
    </div>
  );
}
