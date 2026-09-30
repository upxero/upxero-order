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

export default function Register() {
  const { register, user } = useAuth();
  const navigate = useNavigate();
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
      await register(form);
      toast.success("Restaurant aangemaakt! Welkom bij Upxero Ordering.");
      navigate("/dashboard", { replace: true });
    } catch (err) {
      toast.error(apiError(err, "Registreren mislukt"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 px-6 py-12">
      <div className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
        <Logo />
        <h1 className="mt-8 font-heading text-2xl font-bold tracking-tight text-slate-900">
          Registreer je restaurant
        </h1>
        <p className="mt-2 text-sm text-slate-500">
          Maak een account aan en je restaurant wordt direct aangemaakt.
        </p>

        <form onSubmit={submit} className="mt-6 space-y-4" data-testid="register-form">
          <div>
            <Label htmlFor="restaurantName">Restaurantnaam</Label>
            <Input id="restaurantName" value={form.restaurantName} onChange={upd("restaurantName")} required
              placeholder="Bistro De Hoek" className="mt-1.5" data-testid="register-restaurant-input" />
          </div>
          <div>
            <Label htmlFor="name">Jouw naam</Label>
            <Input id="name" value={form.name} onChange={upd("name")} required
              placeholder="Jan Janssens" className="mt-1.5" data-testid="register-name-input" />
          </div>
          <div>
            <Label htmlFor="email">E-mailadres</Label>
            <Input id="email" type="email" value={form.email} onChange={upd("email")} required
              placeholder="jij@restaurant.be" className="mt-1.5" data-testid="register-email-input" />
          </div>
          <div>
            <Label htmlFor="password">Wachtwoord</Label>
            <Input id="password" type="password" value={form.password} onChange={upd("password")} required
              minLength={6} placeholder="Minimaal 6 tekens" className="mt-1.5" data-testid="register-password-input" />
          </div>
          <Button type="submit" disabled={loading} className="w-full bg-emerald-600 hover:bg-emerald-700"
            data-testid="register-submit-button">
            {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Account aanmaken
          </Button>
        </form>

        <p className="mt-6 text-sm text-slate-500">
          Al een account?{" "}
          <Link to="/login" className="font-semibold text-emerald-600 hover:underline" data-testid="register-to-login">
            Inloggen
          </Link>
        </p>
      </div>
    </div>
  );
}
