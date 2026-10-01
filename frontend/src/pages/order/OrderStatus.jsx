import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { Loader2, ShoppingBag, Truck, MapPin, Check, Clock, XCircle } from "lucide-react";
import api from "../../lib/api";
import { euro } from "../../lib/format";
import { Logo } from "../../components/Logo";

const STEPS = ["new", "accepted", "preparing", "ready", "completed"];

function stepLabel(key, orderType) {
  if (key === "new") return "Wacht op bevestiging";
  if (key === "accepted") return "Bevestigd";
  if (key === "preparing") return "In bereiding";
  if (key === "ready") return orderType === "delivery" ? "Onderweg" : "Klaar om af te halen";
  return "Voltooid";
}

export default function OrderStatus() {
  const { token } = useParams();
  const [order, setOrder] = useState(undefined);

  const load = () => api.get(`/public/order-status/${token}`).then(({ data }) => setOrder(data)).catch(() => setOrder(null));
  useEffect(() => {
    load();
    const t = setInterval(load, 15000);
    return () => clearInterval(t);
    // eslint-disable-next-line
  }, [token]);

  if (order === undefined) return <div className="grid min-h-screen place-items-center bg-slate-50"><Loader2 className="h-6 w-6 animate-spin text-emerald-600" /></div>;
  if (order === null) return (
    <div className="grid min-h-screen place-items-center bg-slate-50 px-6 text-center">
      <div><h1 className="font-heading text-xl font-bold text-slate-900">Bestelling niet gevonden</h1><p className="mt-2 text-sm text-slate-500">Deze link is ongeldig.</p></div>
    </div>
  );

  const cancelled = order.status === "cancelled";
  const currentIdx = STEPS.indexOf(order.status);
  const etaLabel = order.orderType === "delivery" ? "Verwachte bezorgtijd" : "Verwachte afhaaltijd";
  const showEta = order.estimatedTime && ["accepted", "preparing", "ready"].includes(order.status);

  return (
    <div className="min-h-screen bg-slate-50 px-4 py-8" data-testid="order-status-page">
      <div className="mx-auto max-w-lg">
        <div className="flex justify-center"><Logo /></div>
        <div className="mt-6 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="text-center">
            <p className="font-heading text-2xl font-bold text-slate-900" data-testid="status-order-number">Bestelling #{order.orderNumber}</p>
            <p className="mt-1 text-sm text-slate-500">{order.restaurantName}</p>
            <div className="mt-2 inline-flex items-center gap-1.5 text-sm font-medium text-slate-600">
              {order.orderType === "delivery" ? <><Truck className="h-4 w-4" /> Bezorgen</> : <><ShoppingBag className="h-4 w-4" /> Afhalen</>}
            </div>
          </div>

          {cancelled ? (
            <div className="mt-6 flex items-center gap-3 rounded-lg border border-rose-200 bg-rose-50 p-4 text-rose-800" data-testid="status-cancelled">
              <XCircle className="h-5 w-5" /> <span className="font-semibold">Deze bestelling is geannuleerd.</span>
            </div>
          ) : (
            <>
              {order.status === "new" && (
                <p className="mt-5 rounded-lg bg-amber-50 p-3 text-center text-sm font-medium text-amber-800" data-testid="status-awaiting">
                  Je bestelling is ontvangen en wacht op bevestiging van het restaurant.
                </p>
              )}
              {showEta && (
                <div className="mt-5 rounded-lg bg-emerald-50 p-4 text-center" data-testid="status-eta">
                  <p className="text-xs font-medium text-emerald-700">{etaLabel}</p>
                  <p className="font-heading text-3xl font-bold text-emerald-700">{order.estimatedTime}</p>
                </div>
              )}
              <ol className="mt-6 space-y-3" data-testid="status-timeline">
                {STEPS.map((key, i) => {
                  const done = i < currentIdx;
                  const active = i === currentIdx;
                  return (
                    <li key={key} className="flex items-center gap-3" data-testid={`timeline-step-${key}`}>
                      <span className={`grid h-7 w-7 shrink-0 place-items-center rounded-full ${done ? "bg-emerald-600 text-white" : active ? "bg-amber-400 text-white" : "bg-slate-200 text-slate-400"}`}>
                        {done ? <Check className="h-4 w-4" /> : active ? <Clock className="h-4 w-4" /> : <span className="text-xs">{i + 1}</span>}
                      </span>
                      <span className={`text-sm ${active ? "font-semibold text-slate-900" : done ? "text-slate-600" : "text-slate-400"}`}>
                        {stepLabel(key, order.orderType)}
                      </span>
                    </li>
                  );
                })}
              </ol>
            </>
          )}

          {order.orderType === "delivery" && order.deliveryAddress && (
            <p className="mt-6 flex items-start gap-1 border-t border-slate-100 pt-4 text-sm text-slate-500">
              <MapPin className="mt-0.5 h-4 w-4 shrink-0" />
              {order.deliveryAddress.street} {order.deliveryAddress.houseNumber}, {order.deliveryAddress.postalCode} {order.deliveryAddress.city}
            </p>
          )}

          <ul className="mt-4 space-y-2 border-t border-slate-100 pt-4 text-sm">
            {order.items?.map((it, i) => (
              <li key={i}>
                <div className="flex justify-between">
                  <span className="text-slate-700"><span className="font-semibold">{it.quantity}×</span> {it.productName}</span>
                  <span className="tabular text-slate-600">{euro(it.lineTotal)}</span>
                </div>
                {it.selectedOptions?.length > 0 && <p className="pl-5 text-xs text-slate-400">{it.selectedOptions.map((s) => s.optionName).join(", ")}</p>}
              </li>
            ))}
          </ul>
          <div className="mt-4 space-y-1 border-t border-slate-100 pt-4 text-sm">
            <div className="flex justify-between text-slate-500"><span>Subtotaal</span><span className="tabular">{euro(order.subtotal)}</span></div>
            {order.orderType === "delivery" && <div className="flex justify-between text-slate-500"><span>Bezorgkosten</span><span className="tabular">{order.deliveryFee > 0 ? euro(order.deliveryFee) : "Gratis"}</span></div>}
            <div className="flex justify-between text-base font-bold text-slate-900"><span>Totaal</span><span className="tabular">{euro(order.total)}</span></div>
          </div>
          {order.notes && <p className="mt-4 rounded-lg bg-slate-50 p-3 text-sm text-slate-600"><span className="font-medium">Opmerking:</span> {order.notes}</p>}
          <p className="mt-4 text-center text-xs text-slate-400">Deze pagina werkt automatisch bij. Betaling bij {order.orderType === "delivery" ? "levering" : "afhalen"}.</p>
        </div>
      </div>
    </div>
  );
}
