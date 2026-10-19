import { useState } from "react";
import { toast } from "sonner";
import { Loader2, MailWarning } from "lucide-react";
import api, { apiError } from "../lib/api";

export function VerifyEmailBanner({ email, t }) {
  const [loading, setLoading] = useState(false);

  const resend = async () => {
    setLoading(true);
    try {
      await api.post("/auth/resend-verification");
      toast.success(t("Bevestigingsmail verstuurd"));
    } catch (err) {
      toast.error(t(apiError(err)));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mb-6 flex flex-col gap-3 rounded-xl border border-amber-200 bg-amber-50 p-4 sm:flex-row sm:items-center sm:justify-between" data-testid="verify-email-banner">
      <div className="flex items-start gap-3">
        <MailWarning className="mt-0.5 h-5 w-5 shrink-0 text-amber-600" />
        <div>
          <p className="text-sm font-semibold text-amber-900">{t("Bevestig je e-mailadres")}</p>
          <p className="text-sm text-amber-800">{t("We hebben een bevestigingslink gestuurd naar {email}.", { email })}</p>
        </div>
      </div>
      <button type="button" onClick={resend} disabled={loading} data-testid="verify-email-resend-button"
        className="inline-flex items-center justify-center rounded-lg bg-amber-600 px-3.5 py-2 text-sm font-semibold text-white transition-colors hover:bg-amber-700 disabled:opacity-60">
        {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
        {t("Opnieuw versturen")}
      </button>
    </div>
  );
}
