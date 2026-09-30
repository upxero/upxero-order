import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { CheckCircle2, Loader2, ShoppingBag, Truck, MapPin } from "lucide-react";
import api from "../../lib/api";
import { euro, formatDateTime } from "../../lib/format";
import { STATUS_LABELS } from "../../lib/constants";
import { Logo } from "../../components/Logo";
import { Button } from "../../components/ui/button";

export default function OrderConfirmation() {
  const { slug, orderId } = useParams();
  const [order, setOrder] = useState(undefined);

  useEffect(() => {
    api.get(`/public/orders/${orderId}`).then(({ data }) => setOrder(data)).catch(() => setOrder(null));
  }, [orderId]);

  if (order === undefined) return <div className="grid min-h-screen place-items-center bg-slate-50"><Loader2 className="h-6 w-6 animate-spin text-emerald-600" /></div>;
  if (order === null) return (
    <div className="grid min-h-screen place-items-center bg-slate-50 px-6 text-center">
      <p className="text-slate-500">Bestelling niet gevonden.</p>
    </div>
  );

  return (
    <div className="min-h-screen bg-slate-50 px-4 py-10">
      <div className="mx-auto max-w-lg">
        <div className="flex justify-center"><Logo /></div>
        <div className="mt-8 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="flex flex-col items-center text-center">
            <span className="grid h-14 w-14 place-items-center rounded-full bg-emerald-100 text-emerald-600">
              <CheckCircle2 className="h-8 w-8" />
            </span>
            <h1 className="mt-4 font-heading text-2xl font-bold text-slate-900">Bestelling bevestigd!</h1>
            <p className="mt-1 text-sm text-slate-500">Bedankt {order.customer?.name}. {order.restaurantName} heeft je bestelling ontvangen.</p>
            <p className="mt-4 font-heading text-3xl font-bold tabular text-emerald-700" data-testid="order-confirmation-number">#{order.orderNumber}</p>
            <span className="mt-2 rounded-full bg-amber-100 px-3 py-1 text-xs font-semibold text-amber-800">{STATUS_LABELS[order.status]}</span>
          </div>

          <div className="mt-6 flex items-center justify-center gap-2 text-sm font-medium text-slate-600">
            {order.orderType === "delivery" ? <><Truck className="h-4 w-4" /> Bezorgen</> : <><ShoppingBag className="h-4 w-4" /> Afhalen</>}
            <span className="text-slate-300">·</span>
            <span>{formatDateTime(order.createdAt)}</span>
          </div>

          {order.orderType === "delivery" && order.deliveryAddress && (
            <p className="mt-3 flex items-start justify-center gap-1 text-center text-sm text-slate-500">
              <MapPin className="mt-0.5 h-4 w-4 shrink-0" />
              {order.deliveryAddress.street} {order.deliveryAddress.houseNumber}, {order.deliveryAddress.postalCode} {order.deliveryAddress.city}
            </p>
          )}

          <ul className="mt-6 space-y-2 border-t border-slate-100 pt-4 text-sm">
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
          <p className="mt-4 text-center text-xs text-slate-400">Betaling bij {order.orderType === "delivery" ? "levering" : "afhalen"}.</p>
        </div>

        <Link to={`/order/${slug}`}>
          <Button variant="outline" className="mt-4 w-full border-slate-300" data-testid="confirmation-back-button">Terug naar restaurant</Button>
        </Link>
      </div>
    </div>
  );
}
