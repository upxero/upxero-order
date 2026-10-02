import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import { Loader2 } from "lucide-react";
import api, { apiError } from "../lib/api";
import { makeT } from "../lib/i18n";
import { useAuth } from "../context/AuthContext";
import { Logo } from "../components/Logo";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";

export default function StaffInvitation() {
  const [params] = useSearchParams();
  const token = params.get("token") || "";
  const navigate = useNavigate();
  const { refetch } = useAuth();
  const [invite, setInvite] = useState(undefined); // undefined=loading, null=invalid
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!token) { setInvite(null); return; }
    api.get(`/public/invitation/${token}`)
      .then(({ data }) => setInvite(data))
      .catch(() => setInvite(null));
  }, [token]);

  const submit = async (e) => {
    e.preventDefault();
    if (password !== confirm) { toast.error("Passwords do not match"); return; }
    setLoading(true);
    try {
      await api.post("/public/invitation/accept", { token, name, password });
      toast.success("Account created! Welcome to the team.");
      await refetch();
      navigate("/dashboard", { replace: true });
    } catch (err) {
      toast.error(makeT("en")(apiError(err)));
    } finally { setLoading(false); }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 px-6 py-12">
      <div className="w-full max-w-sm rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
        <Logo />
        {invite === undefined ? (
          <div className="grid place-items-center py-10"><Loader2 className="h-6 w-6 animate-spin text-emerald-600" /></div>
        ) : invite === null ? (
          <div className="mt-8" data-testid="invite-invalid">
            <h1 className="font-heading text-xl font-bold text-slate-900">Invalid invitation</h1>
            <p className="mt-2 text-sm text-slate-500">This invitation is invalid, expired or already used. Ask the restaurant owner for a new one.</p>
            <Link to="/login" className="mt-6 inline-block text-sm font-semibold text-emerald-600 hover:underline" data-testid="invite-to-login">To login</Link>
          </div>
        ) : (
          <>
            <h1 className="mt-8 font-heading text-2xl font-bold tracking-tight text-slate-900">Create account</h1>
            <p className="mt-2 text-sm text-slate-500">
              You've been invited to <span className="font-semibold text-slate-700">{invite.restaurantName}</span>. Create your password for <span className="font-medium">{invite.email}</span>.
            </p>
            <form onSubmit={submit} className="mt-6 space-y-4" data-testid="accept-form">
              <div>
                <Label htmlFor="name">Your name</Label>
                <Input id="name" value={name} onChange={(e) => setName(e.target.value)} required placeholder="First Last" className="mt-1.5" data-testid="accept-name-input" />
              </div>
              <div>
                <Label htmlFor="password">Password</Label>
                <Input id="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required minLength={6} placeholder="At least 6 characters" className="mt-1.5" data-testid="accept-password-input" />
              </div>
              <div>
                <Label htmlFor="confirm">Confirm password</Label>
                <Input id="confirm" type="password" value={confirm} onChange={(e) => setConfirm(e.target.value)} required minLength={6} placeholder="Repeat password" className="mt-1.5" data-testid="accept-confirm-input" />
              </div>
              <Button type="submit" disabled={loading} className="w-full bg-emerald-600 hover:bg-emerald-700" data-testid="accept-submit-button">
                {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />} Create account
              </Button>
            </form>
          </>
        )}
      </div>
    </div>
  );
}
