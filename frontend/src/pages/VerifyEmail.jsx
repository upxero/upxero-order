import { useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { CheckCircle2, Loader2, XCircle } from "lucide-react";
import api from "../lib/api";
import { makeT } from "../lib/i18n";
import { usePublicLang } from "../lib/publicLang";
import { useAuth } from "../context/AuthContext";
import { AuthTopBar, BackHome } from "../components/AuthTopBar";

export default function VerifyEmail() {
  const [params] = useSearchParams();
  const token = params.get("token") || "";
  const [lang, setLang] = usePublicLang();
  const t = makeT(lang);
  const { user, refetch } = useAuth();
  const [state, setState] = useState(token ? "loading" : "error");
  const started = useRef(false);

  useEffect(() => {
    if (!token || started.current) { return; }
    started.current = true;
    api.post("/auth/verify-email", { token })
      .then(() => { setState("ok"); refetch(); })
      .catch(() => setState("error"));
  }, [token, refetch]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 px-6 py-12">
      <div className="w-full max-w-sm rounded-2xl border border-slate-200 bg-white p-8 shadow-sm" data-testid="verify-email-page">
        <AuthTopBar lang={lang} setLang={setLang} />
        <BackHome lang={lang} />
        <div className="mt-8 text-center">
          {state === "loading" && (
            <div data-testid="verify-loading">
              <Loader2 className="mx-auto h-8 w-8 animate-spin text-emerald-600" />
              <p className="mt-4 text-sm text-slate-500">{t("Bezig met bevestigen…")}</p>
            </div>
          )}
          {state === "ok" && (
            <div data-testid="verify-success">
              <CheckCircle2 className="mx-auto h-12 w-12 text-emerald-600" />
              <h1 className="mt-4 font-heading text-xl font-bold text-slate-900">{t("Je e-mailadres is bevestigd")}</h1>
              <p className="mt-2 text-sm text-slate-500">{t("Bedankt! Je account is volledig geactiveerd.")}</p>
              <Link to={user ? "/dashboard" : "/login"} className="mt-6 inline-block text-sm font-semibold text-emerald-600 hover:underline" data-testid="verify-continue-link">
                {user ? t("Naar dashboard") : t("Naar inloggen")}
              </Link>
            </div>
          )}
          {state === "error" && (
            <div data-testid="verify-error">
              <XCircle className="mx-auto h-12 w-12 text-rose-500" />
              <h1 className="mt-4 font-heading text-xl font-bold text-slate-900">{t("Deze bevestigingslink is ongeldig, verlopen of al gebruikt.")}</h1>
              <p className="mt-2 text-sm text-slate-500">{t("Log in en vraag een nieuwe bevestigingslink aan via het dashboard.")}</p>
              <Link to={user ? "/dashboard" : "/login"} className="mt-6 inline-block text-sm font-semibold text-emerald-600 hover:underline" data-testid="verify-error-link">
                {user ? t("Naar dashboard") : t("Naar inloggen")}
              </Link>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
