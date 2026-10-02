import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  ClipboardList,
  Bell,
  ChefHat,
  CheckCircle2,
  Power,
  ShoppingBag,
  Truck,
  ArrowRight,
  Copy,
} from "lucide-react";
import { toast } from "sonner";
import api from "../../lib/api";
import { useAuth } from "../../context/AuthContext";
import { useT } from "../../context/I18nContext";
import { Card } from "../../components/ui/card";

function Stat({ icon: Icon, label, value, tone = "slate", testid }) {
  const tones = {
    amber: "bg-amber-50 text-amber-600",
    blue: "bg-blue-50 text-blue-600",
    emerald: "bg-emerald-50 text-emerald-600",
    slate: "bg-slate-100 text-slate-500",
  };
  return (
    <Card className="flex items-start justify-between rounded-xl border-slate-200 p-5 shadow-sm" data-testid={testid}>
      <div>
        <p className="text-sm font-medium text-slate-500">{label}</p>
        <p className="mt-1 font-heading text-3xl font-bold tracking-tight text-slate-900 tabular">{value}</p>
      </div>
      <span className={`grid h-10 w-10 place-items-center rounded-lg ${tones[tone]}`}>
        <Icon className="h-5 w-5" />
      </span>
    </Card>
  );
}

export default function Overview() {
  const { restaurant } = useAuth();
  const t = useT();
  const [stats, setStats] = useState(null);

  useEffect(() => {
    const load = () => api.get("/orders/stats").then(({ data }) => setStats(data)).catch(() => {});
    load();
    const id = setInterval(load, 10000);
    return () => clearInterval(id);
  }, []);

  const orderUrl = restaurant?.slug ? `${window.location.origin}/order/${restaurant.slug}` : "";

  const copyLink = () => {
    navigator.clipboard.writeText(orderUrl);
    toast.success(t("Bestellink gekopieerd"));
  };

  return (
    <div className="space-y-6" data-testid="overview-page">
      <div>
        <h1 className="font-heading text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl">{t("Overzicht")}</h1>
        <p className="mt-1 text-sm text-slate-500">{t("Een snel beeld van je zaak vandaag.")}</p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Stat icon={Bell} label={t("Nieuwe bestellingen")} value={stats?.newOrders ?? "—"} tone="amber" testid="stat-new-orders" />
        <Stat icon={ClipboardList} label={t("Bestellingen vandaag")} value={stats?.ordersToday ?? "—"} tone="blue" testid="stat-orders-today" />
        <Stat icon={ChefHat} label={t("Actief")} value={stats?.activeOrders ?? "—"} tone="slate" testid="stat-active-orders" />
        <Stat icon={CheckCircle2} label={t("Afgerond vandaag")} value={stats?.completedToday ?? "—"} tone="emerald" testid="stat-completed-today" />
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="rounded-xl border-slate-200 p-5 shadow-sm lg:col-span-2">
          <h2 className="font-heading text-lg font-semibold text-slate-900">{t("Status van je zaak")}</h2>
          <div className="mt-4 grid gap-3 sm:grid-cols-3">
            <StatusPill on={stats?.orderingEnabled} icon={Power} label={t("Online bestellen")} t={t} />
            <StatusPill on={stats?.pickupEnabled} icon={ShoppingBag} label={t("Afhalen")} t={t} />
            <StatusPill on={stats?.deliveryEnabled} icon={Truck} label={t("Bezorgen")} t={t} />
          </div>
          <div className="mt-5 flex flex-wrap gap-3">
            <Link to="/dashboard/bestellingen" className="inline-flex items-center gap-1.5 text-sm font-semibold text-emerald-600 hover:underline" data-testid="quick-orders">
              {t("Bekijk bestellingen")} <ArrowRight className="h-4 w-4" />
            </Link>
            <Link to="/dashboard/menu" className="inline-flex items-center gap-1.5 text-sm font-semibold text-emerald-600 hover:underline" data-testid="quick-menu">
              {t("Beheer menu")} <ArrowRight className="h-4 w-4" />
            </Link>
            <Link to="/dashboard/instellingen" className="inline-flex items-center gap-1.5 text-sm font-semibold text-emerald-600 hover:underline" data-testid="quick-settings">
              {t("Instellingen")} <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
        </Card>

        <Card className="rounded-xl border-slate-200 p-5 shadow-sm">
          <h2 className="font-heading text-lg font-semibold text-slate-900">{t("Jouw bestellink")}</h2>
          <p className="mt-1 text-sm text-slate-500">{t("Deel deze link of maak er een QR-code van.")}</p>
          <div className="mt-4 flex items-center gap-2 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2">
            <span className="truncate text-xs text-slate-600" data-testid="order-link">{orderUrl}</span>
          </div>
          <button onClick={copyLink} data-testid="copy-order-link"
            className="mt-3 inline-flex items-center gap-1.5 rounded-lg bg-slate-900 px-3 py-2 text-sm font-medium text-white hover:bg-slate-800">
            <Copy className="h-4 w-4" /> {t("Kopieer link")}
          </button>
        </Card>
      </div>
    </div>
  );
}

function StatusPill({ on, icon: Icon, label, t }) {
  return (
    <div className={`flex items-center gap-3 rounded-lg border px-3 py-3 ${on ? "border-emerald-200 bg-emerald-50" : "border-slate-200 bg-slate-50"}`}>
      <span className={`grid h-9 w-9 place-items-center rounded-lg ${on ? "bg-emerald-600 text-white" : "bg-slate-200 text-slate-500"}`}>
        <Icon className="h-4.5 w-4.5" size={18} />
      </span>
      <div>
        <p className="text-sm font-semibold text-slate-900">{label}</p>
        <p className={`text-xs font-medium ${on ? "text-emerald-600" : "text-slate-400"}`}>{on ? t("Aan") : t("Uit")}</p>
      </div>
    </div>
  );
}
