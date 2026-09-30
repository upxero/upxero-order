import { useEffect, useMemo, useState } from "react";
import { Loader2, Phone, MapPin, StickyNote, ShoppingBag, Truck, RefreshCw } from "lucide-react";
import { toast } from "sonner";
import api, { apiError } from "../../lib/api";
import { euro, formatTime } from "../../lib/format";
import { STATUS_LABELS, STATUS_STYLES, NEXT_ACTION } from "../../lib/constants";
import { EmptyState } from "../../components/EmptyState";
import { Button } from "../../components/ui/button";

const FILTERS = [
  { key: "actief", label: "Actief", statuses: ["new", "accepted", "preparing", "ready"] },
  { key: "new", label: "Nieuw", statuses: ["new"] },
  { key: "completed", label: "Afgerond", statuses: ["completed"] },
  { key: "cancelled", label: "Geannuleerd", statuses: ["cancelled"] },
  { key: "all", label: "Alles", statuses: null },
];

export default function Orders() {
  const [orders, setOrders] = useState(null);
  const [filter, setFilter] = useState("actief");
  const [busy, setBusy] = useState(null);

  const load = async () => {
    try {
      const { data } = await api.get("/orders");
      setOrders(data);
    } catch (e) {
      setOrders([]);
    }
  };

  useEffect(() => {
    load();
    const t = setInterval(load, 10000);
    return () => clearInterval(t);
  }, []);

  const current = FILTERS.find((f) => f.key === filter);
  const filtered = useMemo(() => {
    if (!orders) return [];
    if (!current.statuses) return orders;
    return orders.filter((o) => current.statuses.includes(o.status));
  }, [orders, current]);

  const changeStatus = async (id, status) => {
    setBusy(id + status);
    try {
      await api.patch(`/orders/${id}/status`, { status });
      toast.success(`Bestelling → ${STATUS_LABELS[status]}`);
      await load();
    } catch (e) {
      toast.error(apiError(e));
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="space-y-6" data-testid="orders-page">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="font-heading text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl">Bestellingen</h1>
          <p className="mt-1 text-sm text-slate-500">Vernieuwt automatisch elke 10 seconden.</p>
        </div>
        <Button variant="outline" onClick={load} className="border-slate-300" data-testid="orders-refresh">
          <RefreshCw className="mr-2 h-4 w-4" /> Vernieuwen
        </Button>
      </div>

      <div className="flex flex-wrap gap-2">
        {FILTERS.map((f) => (
          <button
            key={f.key}
            onClick={() => setFilter(f.key)}
            data-testid={`orders-filter-${f.key}`}
            className={`rounded-full px-4 py-1.5 text-sm font-medium transition-colors ${
              filter === f.key ? "bg-slate-900 text-white" : "bg-white text-slate-600 border border-slate-200 hover:bg-slate-50"
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {orders === null ? (
        <div className="grid place-items-center py-20"><Loader2 className="h-6 w-6 animate-spin text-emerald-600" /></div>
      ) : filtered.length === 0 ? (
        <EmptyState
          icon={ShoppingBag}
          title="Nog geen bestellingen"
          description="Nieuwe bestellingen verschijnen hier automatisch."
          testid="orders-empty"
        />
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {filtered.map((o) => (
            <OrderCard key={o.id} order={o} onStatus={changeStatus} busy={busy} />
          ))}
        </div>
      )}
    </div>
  );
}

function OrderCard({ order, onStatus, busy }) {
  const next = NEXT_ACTION[order.status];
  const canCancel = !["completed", "cancelled"].includes(order.status);
  return (
    <div className="flex flex-col rounded-xl border border-slate-200 bg-white p-4 shadow-sm" data-testid={`order-card-${order.orderNumber}`}>
      <div className="flex items-start justify-between">
        <div>
          <p className="font-heading text-lg font-bold text-slate-900 tabular">#{order.orderNumber}</p>
          <p className="text-xs text-slate-500">{formatTime(order.createdAt)}</p>
        </div>
        <span className={`rounded-md border px-2 py-0.5 text-xs font-semibold ${STATUS_STYLES[order.status]}`} data-testid={`order-status-${order.orderNumber}`}>
          {STATUS_LABELS[order.status]}
        </span>
      </div>

      <div className="mt-3 flex items-center gap-2 text-sm">
        <span className={`inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-xs font-medium ${order.orderType === "delivery" ? "bg-blue-50 text-blue-700" : "bg-emerald-50 text-emerald-700"}`}>
          {order.orderType === "delivery" ? <><Truck className="h-3.5 w-3.5" /> Bezorgen</> : <><ShoppingBag className="h-3.5 w-3.5" /> Afhalen</>}
        </span>
      </div>

      <div className="mt-3 border-t border-slate-100 pt-3 text-sm">
        <p className="font-semibold text-slate-900">{order.customer?.name}</p>
        <a href={`tel:${order.customer?.phone}`} className="mt-0.5 inline-flex items-center gap-1 text-slate-500 hover:text-emerald-600">
          <Phone className="h-3.5 w-3.5" /> {order.customer?.phone}
        </a>
        {order.orderType === "delivery" && order.deliveryAddress && (
          <p className="mt-1 flex items-start gap-1 text-slate-500">
            <MapPin className="mt-0.5 h-3.5 w-3.5 shrink-0" />
            <span>{order.deliveryAddress.street} {order.deliveryAddress.houseNumber}, {order.deliveryAddress.postalCode} {order.deliveryAddress.city}{order.deliveryAddress.extra ? ` — ${order.deliveryAddress.extra}` : ""}</span>
          </p>
        )}
      </div>

      <ul className="mt-3 space-y-1.5 border-t border-slate-100 pt-3 text-sm">
        {order.items?.map((it, i) => (
          <li key={i}>
            <div className="flex justify-between gap-2">
              <span className="text-slate-700"><span className="font-semibold text-slate-900">{it.quantity}×</span> {it.productName}</span>
              <span className="tabular text-slate-600">{euro(it.lineTotal)}</span>
            </div>
            {it.selectedOptions?.length > 0 && (
              <p className="pl-5 text-xs text-slate-400">{it.selectedOptions.map((s) => s.optionName).join(", ")}</p>
            )}
          </li>
        ))}
      </ul>

      {order.notes && (
        <p className="mt-3 flex items-start gap-1.5 rounded-lg bg-amber-50 p-2 text-xs text-amber-800">
          <StickyNote className="mt-0.5 h-3.5 w-3.5 shrink-0" /> {order.notes}
        </p>
      )}

      <div className="mt-3 space-y-0.5 border-t border-slate-100 pt-3 text-sm">
        <div className="flex justify-between text-slate-500"><span>Subtotaal</span><span className="tabular">{euro(order.subtotal)}</span></div>
        {order.orderType === "delivery" && (
          <div className="flex justify-between text-slate-500"><span>Bezorgkosten</span><span className="tabular">{order.deliveryFee > 0 ? euro(order.deliveryFee) : "Gratis"}</span></div>
        )}
        <div className="flex justify-between font-semibold text-slate-900"><span>Totaal</span><span className="tabular">{euro(order.total)}</span></div>
      </div>

      {(next || canCancel) && (
        <div className="mt-4 flex gap-2">
          {next && (
            <Button
              onClick={() => onStatus(order.id, next.status)}
              disabled={busy === order.id + next.status}
              className="flex-1 bg-emerald-600 hover:bg-emerald-700 active:scale-[0.98]"
              data-testid={`order-advance-${order.orderNumber}`}
            >
              {busy === order.id + next.status && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {next.label}
            </Button>
          )}
          {canCancel && (
            <Button
              variant="outline"
              onClick={() => onStatus(order.id, "cancelled")}
              disabled={busy === order.id + "cancelled"}
              className="border-slate-300 text-rose-600 hover:bg-rose-50 hover:text-rose-700"
              data-testid={`order-cancel-${order.orderNumber}`}
            >
              Annuleren
            </Button>
          )}
        </div>
      )}
    </div>
  );
}
