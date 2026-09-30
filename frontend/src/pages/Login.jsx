import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Loader2 } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { apiError } from "../lib/api";
import { Logo } from "../components/Logo";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";

export default function Login() {
  const { login, user } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (user) navigate("/dashboard", { replace: true });
  }, [user, navigate]);

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await login(email, password);
      toast.success("Welkom terug!");
      navigate("/dashboard", { replace: true });
    } catch (err) {
      toast.error(apiError(err, "Inloggen mislukt"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      <div className="flex flex-col justify-center px-6 py-12 sm:px-12 lg:px-16">
        <div className="mx-auto w-full max-w-sm">
          <Logo />
          <h1 className="mt-10 font-heading text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl">
            Inloggen
          </h1>
          <p className="mt-2 text-sm text-slate-500">
            Beheer je menu en bestellingen op één plek.
          </p>

          <form onSubmit={submit} className="mt-8 space-y-4" data-testid="login-form">
            <div>
              <Label htmlFor="email">E-mailadres</Label>
              <Input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoComplete="email"
                placeholder="jij@restaurant.be"
                className="mt-1.5"
                data-testid="login-email-input"
              />
            </div>
            <div>
              <Label htmlFor="password">Wachtwoord</Label>
              <Input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                autoComplete="current-password"
                placeholder="••••••••"
                className="mt-1.5"
                data-testid="login-password-input"
              />
            </div>
            <Button
              type="submit"
              disabled={loading}
              className="w-full bg-emerald-600 hover:bg-emerald-700"
              data-testid="login-submit-button"
            >
              {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Inloggen
            </Button>
          </form>

          <p className="mt-6 text-sm text-slate-500">
            Nog geen account?{" "}
            <Link to="/registreren" className="font-semibold text-emerald-600 hover:underline" data-testid="login-to-register">
              Registreer je restaurant
            </Link>
          </p>

          <div className="mt-8 rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs text-slate-500">
            <p className="font-semibold text-slate-600">Demo-account</p>
            <p>owner@demo.upxero.com · Demo!2025</p>
          </div>
        </div>
      </div>
      <div className="relative hidden bg-slate-900 lg:block">
        <img
          src="https://images.unsplash.com/photo-1517248135467-4c7edcad34c4"
          alt="Restaurant"
          className="absolute inset-0 h-full w-full object-cover opacity-40"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-slate-900 via-slate-900/60 to-transparent" />
        <div className="absolute bottom-0 p-12">
          <p className="font-heading text-2xl font-bold text-white">Commissievrij online bestellen</p>
          <p className="mt-2 max-w-sm text-slate-300">
            Jouw eigen bestelpagina voor afhalen en bezorgen. Geen commissies, volledige controle.
          </p>
        </div>
      </div>
    </div>
  );
}
