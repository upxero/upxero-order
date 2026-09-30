import { useEffect, useMemo, useRef, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  Loader2, Plus, Minus, ShoppingBag, Truck, X, MapPin, Clock, ChevronRight, ArrowLeft,
} from "lucide-react";
import { toast } from "sonner";
import api, { apiError } from "../../lib/api";
import { euro } from "../../lib/format";
import { DAYS } from "../../lib/constants";
import { Logo } from "../../components/Logo";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { Textarea } from "../../components/ui/textarea";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription,
} from "../../components/ui/dialog";

const lineUnit = (l) => l.unitPrice + l.selectedOptions.reduce((s, o) => s + o.price, 0);

export default function OrderPage() {
  const { slug } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState(undefined);
  const [activeCat, setActiveCat] = useState(null);
  const [cart, setCart] = useState(() => {
    try { return JSON.parse(localStorage.getItem(`upxero-cart-${slug}`) || "[]"); } catch { return []; }
  });
  const [optItem, setOptItem] = useState(null);
  const [cartOpen, setCartOpen] = useState(false);
  const [checkout, setCheckout] = useState(false);
  const idemRef = useRef(null);

  useEffect(() => {
    api.get(`/public/restaurant/${slug}`)
      .then(({ data }) => { setData(data); setActiveCat(data.categories[0]?.id || null); })
      .catch(() => setData(null));
  }, [slug]);

  useEffect(() => {
    localStorage.setItem(`upxero-cart-${slug}`, JSON.stringify(cart));
  }, [cart, slug]);

  const subtotal = useMemo(() => cart.reduce((s, l) => s + lineUnit(l) * l.quantity, 0), [cart]);
  const cartCount = cart.reduce((s, l) => s + l.quantity, 0);

  if (data === undefined) return <div className="grid min-h-screen place-items-center bg-slate-50"><Loader2 className="h-6 w-6 animate-spin text-emerald-600" /></div>;
  if (data === null) return (
    <div className="grid min-h-screen place-items-center bg-slate-50 px-6 text-center">
      <div>
        <h1 className="font-heading text-2xl font-bold text-slate-900">Restaurant niet gevonden</h1>
        <p className="mt-2 text-slate-500">Controleer de link en probeer het opnieuw.</p>
      </div>
    </div>
  );

  const { restaurant, categories, items } = data;
  const canOrder = restaurant.orderingEnabled && restaurant.isOpen;
  const itemsByCat = (cid) => items.filter((i) => i.categoryId === cid);

  const addToCart = (item, selectedOptions, quantity) => {
    const line = {
      cartId: `${Date.now()}-${Math.random()}`,
      productId: item.id, productName: item.name, unitPrice: item.price,
      image: item.image, selectedOptions, quantity,
    };
    setCart((c) => [...c, line]);
    toast.success(`${item.name} toegevoegd`);
  };

  const setQty = (cartId, delta) =>
    setCart((c) => c.flatMap((l) => {
      if (l.cartId !== cartId) return [l];
      const q = l.quantity + delta;
      return q <= 0 ? [] : [{ ...l, quantity: q }];
    }));

  const openItem = (item) => {
    if (!canOrder) return;
    if (item.optionGroups && item.optionGroups.length > 0) setOptItem(item);
    else addToCart(item, [], 1);
  };

  return (
    <div className="min-h-screen bg-slate-50 pb-28 lg:pb-8">
      {/* Header */}
      <div className="relative bg-slate-900">
        <img src="https://images.unsplash.com/photo-1517248135467-4c7edcad34c4" alt="" className="absolute inset-0 h-full w-full object-cover opacity-30" />
        <div className="absolute inset-0 bg-gradient-to-t from-slate-900 to-slate-900/50" />
        <div className="relative mx-auto max-w-5xl px-4 py-8 sm:px-6">
          <div className="flex items-center justify-between">
            <span className="rounded-lg bg-white/10 px-1 py-0.5 backdrop-blur"><Logo /></span>
            <span className={`rounded-full px-3 py-1 text-xs font-semibold ${restaurant.isOpen ? "bg-emerald-500 text-white" : "bg-rose-500 text-white"}`} data-testid="restaurant-open-status">
              {restaurant.isOpen ? "Open" : "Gesloten"}
            </span>
          </div>
          <h1 className="mt-6 font-heading text-3xl font-bold tracking-tight text-white sm:text-4xl" data-testid="restaurant-name">{restaurant.name}</h1>
          {restaurant.description && <p className="mt-2 max-w-2xl text-sm text-slate-200">{restaurant.description}</p>}
          <div className="mt-3 flex flex-wrap gap-4 text-sm text-slate-300">
            {(restaurant.street || restaurant.city) && (
              <span className="flex items-center gap-1"><MapPin className="h-4 w-4" /> {restaurant.street} {restaurant.houseNumber}, {restaurant.city}</span>
            )}
            <span className="flex items-center gap-1">
              {restaurant.pickupEnabled && <><ShoppingBag className="h-4 w-4" /> Afhalen</>}
              {restaurant.deliveryEnabled && <><Truck className="ml-2 h-4 w-4" /> Bezorgen</>}
            </span>
          </div>
        </div>
      </div>

      {!canOrder && (
        <div className="mx-auto mt-4 max-w-5xl px-4 sm:px-6">
          <div className="flex items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm font-medium text-amber-800" data-testid="ordering-unavailable">
            <Clock className="h-4 w-4" />
            {restaurant.orderingEnabled ? "Het restaurant is momenteel gesloten." : "Online bestellen is momenteel niet beschikbaar."}
          </div>
        </div>
      )}

      {/* Category nav */}
      <div className="sticky top-0 z-20 mt-4 border-b border-slate-200 bg-white/95 backdrop-blur">
        <div className="mx-auto flex max-w-5xl gap-2 overflow-x-auto px-4 py-3 scroll-thin sm:px-6">
          {categories.map((c) => (
            <button key={c.id} onClick={() => {
              setActiveCat(c.id);
              document.getElementById(`cat-${c.id}`)?.scrollIntoView({ behavior: "smooth", block: "start" });
            }}
              data-testid={`category-tab-${c.id}`}
              className={`whitespace-nowrap rounded-full px-4 py-1.5 text-sm font-medium transition-colors ${activeCat === c.id ? "bg-emerald-600 text-white" : "bg-slate-100 text-slate-600 hover:bg-slate-200"}`}>
              {c.name}
            </button>
          ))}
        </div>
      </div>

      {/* Menu */}
      <div className="mx-auto max-w-5xl px-4 py-6 sm:px-6">
        {categories.length === 0 && <p className="py-16 text-center text-slate-500">Dit menu is nog leeg.</p>}
        {categories.map((c) => (
          <section key={c.id} id={`cat-${c.id}`} className="mb-8 scroll-mt-20">
            <h2 className="font-heading text-xl font-bold text-slate-900">{c.name}</h2>
            {c.description && <p className="text-sm text-slate-500">{c.description}</p>}
            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              {itemsByCat(c.id).map((item) => (
                <button key={item.id} onClick={() => openItem(item)} disabled={!canOrder || !item.isAvailable}
                  data-testid={`product-card-${item.id}`}
                  className="flex gap-4 rounded-xl border border-slate-200 bg-white p-4 text-left transition-shadow hover:shadow-md disabled:opacity-60">
                  <div className="min-w-0 flex-1">
                    <p className="font-semibold text-slate-900">{item.name}</p>
                    {item.description && <p className="mt-0.5 line-clamp-2 text-sm text-slate-500">{item.description}</p>}
                    <p className="mt-2 tabular font-semibold text-emerald-700">{euro(item.price)}</p>
                    {!item.isAvailable && <span className="mt-1 inline-block rounded bg-slate-100 px-1.5 py-0.5 text-xs font-medium text-slate-500">Niet beschikbaar</span>}
                  </div>
                  {item.image && (
                    <div className="relative">
                      <img src={item.image} alt={item.name} className="h-24 w-24 shrink-0 rounded-lg object-cover" />
                      {canOrder && item.isAvailable && <span className="absolute -bottom-1.5 -right-1.5 grid h-8 w-8 place-items-center rounded-full bg-emerald-600 text-white shadow"><Plus className="h-4 w-4" /></span>}
                    </div>
                  )}
                </button>
              ))}
            </div>
          </section>
        ))}
      </div>

      {/* Sticky cart bar */}
      {cartCount > 0 && !checkout && (
        <div className="fixed inset-x-0 bottom-0 z-30 border-t border-slate-200 bg-white p-3 shadow-[0_-4px_20px_rgba(0,0,0,0.06)] lg:sticky lg:bottom-6 lg:mx-auto lg:max-w-md lg:rounded-xl lg:border">
          <Button onClick={() => setCartOpen(true)} data-testid="view-cart-button"
            className="flex w-full items-center justify-between bg-emerald-600 px-4 py-6 text-base hover:bg-emerald-700">
            <span className="flex items-center gap-2"><ShoppingBag className="h-5 w-5" /> {cartCount} in winkelmand</span>
            <span className="tabular font-bold">{euro(subtotal)}</span>
          </Button>
        </div>
      )}

      {optItem && <OptionsModal item={optItem} onClose={() => setOptItem(null)} onAdd={addToCart} />}

      <CartSheet open={cartOpen} onClose={() => setCartOpen(false)} cart={cart} setQty={setQty} subtotal={subtotal}
        onCheckout={() => { setCartOpen(false); setCheckout(true); }} />

      {checkout && (
        <Checkout slug={slug} restaurant={restaurant} cart={cart} subtotal={subtotal}
          onBack={() => setCheckout(false)}
          onSuccess={(orderId) => { setCart([]); localStorage.removeItem(`upxero-cart-${slug}`); navigate(`/order/${slug}/bevestiging/${orderId}`); }}
          idemRef={idemRef} />
      )}
    </div>
  );
}

function OptionsModal({ item, onClose, onAdd }) {
  const [selected, setSelected] = useState({});
  const [qty, setQty] = useState(1);

  const toggle = (g, opt) => {
    setSelected((s) => {
      const cur = s[g.id] || [];
      if (g.multiple) {
        const exists = cur.find((o) => o.optionId === opt.id);
        return { ...s, [g.id]: exists ? cur.filter((o) => o.optionId !== opt.id) : [...cur, mapOpt(g, opt)] };
      }
      return { ...s, [g.id]: [mapOpt(g, opt)] };
    });
  };
  const mapOpt = (g, opt) => ({ groupId: g.id, groupName: g.name, optionId: opt.id, optionName: opt.name, price: opt.price });
  const isSel = (gid, oid) => (selected[gid] || []).some((o) => o.optionId === oid);

  const missing = item.optionGroups.filter((g) => g.required && !(selected[g.id]?.length));
  const flat = Object.values(selected).flat();
  const unit = item.price + flat.reduce((s, o) => s + o.price, 0);

  const confirm = () => {
    if (missing.length) { toast.error(`Maak een keuze voor: ${missing.map((g) => g.name).join(", ")}`); return; }
    onAdd(item, flat, qty);
    onClose();
  };

  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent className="max-h-[90vh] overflow-y-auto scroll-thin sm:max-w-md" data-testid="options-modal">
        <DialogHeader><DialogTitle>{item.name}</DialogTitle></DialogHeader>
        <DialogDescription className="sr-only">Kies opties en aantal voor {item.name}</DialogDescription>
        {item.description && <p className="-mt-2 text-sm text-slate-500">{item.description}</p>}
        <div className="space-y-4">
          {item.optionGroups.map((g) => (
            <div key={g.id}>
              <p className="flex items-center gap-2 text-sm font-semibold text-slate-900">
                {g.name}
                {g.required ? <span className="rounded bg-rose-50 px-1.5 py-0.5 text-xs text-rose-600">Verplicht</span>
                  : <span className="text-xs font-normal text-slate-400">{g.multiple ? "Meerdere mogelijk" : "Optioneel"}</span>}
              </p>
              <div className="mt-2 space-y-1.5">
                {g.options.map((opt) => (
                  <label key={opt.id} data-testid={`option-${opt.id}`}
                    className={`flex cursor-pointer items-center justify-between rounded-lg border px-3 py-2.5 transition-colors ${isSel(g.id, opt.id) ? "border-emerald-500 bg-emerald-50" : "border-slate-200 hover:bg-slate-50"}`}>
                    <span className="flex items-center gap-2.5 text-sm text-slate-700">
                      <input type={g.multiple ? "checkbox" : "radio"} name={g.id} checked={isSel(g.id, opt.id)} onChange={() => toggle(g, opt)} className="accent-emerald-600" />
                      {opt.name}
                    </span>
                    {opt.price > 0 && <span className="tabular text-sm font-medium text-slate-500">+{euro(opt.price)}</span>}
                  </label>
                ))}
              </div>
            </div>
          ))}
        </div>
        <div className="mt-2 flex items-center justify-between">
          <div className="flex items-center gap-3 rounded-lg border border-slate-200 p-1">
            <button onClick={() => setQty((q) => Math.max(1, q - 1))} className="grid h-8 w-8 place-items-center rounded-md hover:bg-slate-100" data-testid="option-qty-minus"><Minus className="h-4 w-4" /></button>
            <span className="w-6 text-center font-semibold tabular" data-testid="option-qty">{qty}</span>
            <button onClick={() => setQty((q) => q + 1)} className="grid h-8 w-8 place-items-center rounded-md hover:bg-slate-100" data-testid="option-qty-plus"><Plus className="h-4 w-4" /></button>
          </div>
          <Button onClick={confirm} className="bg-emerald-600 hover:bg-emerald-700" data-testid="option-add-button">
            Toevoegen · {euro(unit * qty)}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

function CartSheet({ open, onClose, cart, setQty, subtotal, onCheckout }) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50">
      <div className="absolute inset-0 bg-slate-900/40 backdrop-blur-sm" onClick={onClose} />
      <div className="absolute inset-y-0 right-0 flex w-full max-w-md flex-col bg-white shadow-xl" data-testid="cart-sheet">
        <div className="flex items-center justify-between border-b border-slate-200 px-5 py-4">
          <h2 className="font-heading text-lg font-bold text-slate-900">Winkelmand</h2>
          <button onClick={onClose} data-testid="cart-close"><X className="h-5 w-5 text-slate-500" /></button>
        </div>
        <div className="flex-1 overflow-y-auto scroll-thin p-5">
          {cart.length === 0 ? (
            <p className="py-16 text-center text-slate-500">Je winkelmand is leeg.</p>
          ) : (
            <ul className="space-y-4">
              {cart.map((l) => (
                <li key={l.cartId} className="flex gap-3" data-testid={`cart-line-${l.productId}`}>
                  <div className="flex-1">
                    <p className="font-semibold text-slate-900">{l.productName}</p>
                    {l.selectedOptions.length > 0 && <p className="text-xs text-slate-400">{l.selectedOptions.map((o) => o.optionName).join(", ")}</p>}
                    <div className="mt-2 flex items-center gap-2">
                      <button onClick={() => setQty(l.cartId, -1)} className="grid h-7 w-7 place-items-center rounded-md border border-slate-200 hover:bg-slate-50" data-testid={`cart-minus-${l.productId}`}><Minus className="h-3.5 w-3.5" /></button>
                      <span className="w-5 text-center text-sm font-semibold tabular">{l.quantity}</span>
                      <button onClick={() => setQty(l.cartId, 1)} className="grid h-7 w-7 place-items-center rounded-md border border-slate-200 hover:bg-slate-50" data-testid={`cart-plus-${l.productId}`}><Plus className="h-3.5 w-3.5" /></button>
                    </div>
                  </div>
                  <span className="tabular font-semibold text-slate-900">{euro((l.unitPrice + l.selectedOptions.reduce((s, o) => s + o.price, 0)) * l.quantity)}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
        {cart.length > 0 && (
          <div className="border-t border-slate-200 p-5">
            <div className="flex justify-between text-sm"><span className="text-slate-500">Subtotaal</span><span className="tabular font-semibold">{euro(subtotal)}</span></div>
            <Button onClick={onCheckout} className="mt-3 w-full bg-emerald-600 py-6 text-base hover:bg-emerald-700" data-testid="cart-checkout-button">
              Afrekenen <ChevronRight className="ml-1 h-4 w-4" />
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}

function Checkout({ slug, restaurant, cart, subtotal, onBack, onSuccess, idemRef }) {
  const [orderType, setOrderType] = useState(restaurant.pickupEnabled ? "pickup" : "delivery");
  const [customer, setCustomer] = useState({ name: "", phone: "", email: "" });
  const [address, setAddress] = useState({ street: "", houseNumber: "", postalCode: "", city: "", extra: "" });
  const [notes, setNotes] = useState("");
  const [quote, setQuote] = useState(null);
  const [quoting, setQuoting] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const itemsPayload = cart.map((l) => ({
    productId: l.productId, quantity: l.quantity,
    selectedOptions: l.selectedOptions.map((o) => ({ groupId: o.groupId, optionId: o.optionId })),
  }));

  useEffect(() => { setQuote(null); }, [orderType, address.street, address.houseNumber, address.postalCode, address.city]);

  const getQuote = async () => {
    setQuoting(true);
    try {
      const { data } = await api.post(`/public/restaurant/${slug}/quote`, {
        orderType, items: itemsPayload,
        deliveryAddress: orderType === "delivery" ? address : null,
      });
      setQuote(data);
      if (data.available === false) toast.error(data.message);
      else if (data.belowMinimum) {
        const amt = euro(data.minimumOrderAmount);
        toast.error(`Voor bezorging in jouw gebied is een minimum bestelling van ${amt} vereist.`);
      }
    } catch (e) { toast.error(apiError(e)); } finally { setQuoting(false); }
  };

  const deliveryReady = orderType === "delivery" && address.street && address.houseNumber && address.postalCode && address.city;
  const canSubmit = customer.name && customer.phone &&
    (orderType === "pickup" || (deliveryReady && quote?.available && !quote?.belowMinimum));

  const fee = orderType === "delivery" ? (quote?.deliveryFee ?? 0) : 0;
  const total = orderType === "delivery" && quote?.available ? quote.total : subtotal;

  const submit = async () => {
    if (!idemRef.current) idemRef.current = (crypto.randomUUID ? crypto.randomUUID() : String(Date.now()) + Math.random());
    setSubmitting(true);
    try {
      const { data } = await api.post(`/public/restaurant/${slug}/orders`, {
        orderType, items: itemsPayload, customer,
        deliveryAddress: orderType === "delivery" ? address : null,
        notes, idempotencyKey: idemRef.current,
      });
      toast.success("Bestelling geplaatst!");
      onSuccess(data.id);
    } catch (e) {
      idemRef.current = null;
      toast.error(apiError(e));
    } finally { setSubmitting(false); }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-50 scroll-thin" data-testid="checkout-view">
      <div className="mx-auto max-w-lg px-4 py-6">
        <button onClick={onBack} className="mb-4 inline-flex items-center gap-1 text-sm font-medium text-slate-600" data-testid="checkout-back"><ArrowLeft className="h-4 w-4" /> Terug naar menu</button>
        <h1 className="font-heading text-2xl font-bold text-slate-900">Afrekenen</h1>

        {/* order type */}
        <div className="mt-5 grid grid-cols-2 gap-2 rounded-xl border border-slate-200 bg-white p-1">
          {restaurant.pickupEnabled && (
            <button onClick={() => setOrderType("pickup")} data-testid="checkout-type-pickup"
              className={`flex items-center justify-center gap-2 rounded-lg py-3 text-sm font-medium transition-colors ${orderType === "pickup" ? "bg-emerald-600 text-white" : "text-slate-600"}`}>
              <ShoppingBag className="h-4 w-4" /> Afhalen
            </button>
          )}
          {restaurant.deliveryEnabled && (
            <button onClick={() => setOrderType("delivery")} data-testid="checkout-type-delivery"
              className={`flex items-center justify-center gap-2 rounded-lg py-3 text-sm font-medium transition-colors ${orderType === "delivery" ? "bg-emerald-600 text-white" : "text-slate-600"}`}>
              <Truck className="h-4 w-4" /> Bezorgen
            </button>
          )}
        </div>

        {/* customer */}
        <div className="mt-4 space-y-3 rounded-xl border border-slate-200 bg-white p-4">
          <h2 className="font-heading font-semibold text-slate-900">Jouw gegevens</h2>
          <div><Label>Naam</Label><Input value={customer.name} onChange={(e) => setCustomer({ ...customer, name: e.target.value })} className="mt-1.5" data-testid="checkout-name" /></div>
          <div><Label>Telefoon</Label><Input value={customer.phone} onChange={(e) => setCustomer({ ...customer, phone: e.target.value })} className="mt-1.5" data-testid="checkout-phone" /></div>
          <div><Label>E-mail (optioneel)</Label><Input type="email" value={customer.email} onChange={(e) => setCustomer({ ...customer, email: e.target.value })} className="mt-1.5" data-testid="checkout-email" /></div>
        </div>

        {/* delivery address */}
        {orderType === "delivery" && (
          <div className="mt-4 space-y-3 rounded-xl border border-slate-200 bg-white p-4">
            <h2 className="font-heading font-semibold text-slate-900">Bezorgadres</h2>
            <div className="grid grid-cols-[2fr_1fr] gap-3">
              <div><Label>Straat</Label><Input value={address.street} onChange={(e) => setAddress({ ...address, street: e.target.value })} className="mt-1.5" data-testid="checkout-street" /></div>
              <div><Label>Nr.</Label><Input value={address.houseNumber} onChange={(e) => setAddress({ ...address, houseNumber: e.target.value })} className="mt-1.5" data-testid="checkout-housenr" /></div>
            </div>
            <div className="grid grid-cols-[1fr_2fr] gap-3">
              <div><Label>Postcode</Label><Input value={address.postalCode} onChange={(e) => setAddress({ ...address, postalCode: e.target.value })} className="mt-1.5" data-testid="checkout-postal" /></div>
              <div><Label>Stad</Label><Input value={address.city} onChange={(e) => setAddress({ ...address, city: e.target.value })} className="mt-1.5" data-testid="checkout-city" /></div>
            </div>
            <div><Label>Extra info (optioneel)</Label><Input value={address.extra} onChange={(e) => setAddress({ ...address, extra: e.target.value })} placeholder="Bel even aan" className="mt-1.5" /></div>
            <Button onClick={getQuote} disabled={!deliveryReady || quoting} variant="outline" className="w-full border-slate-300" data-testid="checkout-calc-delivery">
              {quoting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />} Bereken bezorgkosten
            </Button>
            {quote?.available === false && <p className="rounded-lg bg-rose-50 p-2.5 text-sm font-medium text-rose-700" data-testid="delivery-unavailable-msg">{quote.message}</p>}
            {quote?.belowMinimum && <p className="rounded-lg bg-amber-50 p-2.5 text-sm font-medium text-amber-800" data-testid="delivery-min-msg">Voor bezorging in jouw gebied is een minimum bestelling van {euro(quote.minimumOrderAmount)} vereist.</p>}
          </div>
        )}

        {/* notes */}
        <div className="mt-4 rounded-xl border border-slate-200 bg-white p-4">
          <Label>Opmerkingen (optioneel)</Label>
          <Textarea value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Geen ui aub." className="mt-1.5" data-testid="checkout-notes" />
        </div>

        {/* summary */}
        <div className="mt-4 space-y-1 rounded-xl border border-slate-200 bg-white p-4 text-sm">
          <div className="flex justify-between text-slate-500"><span>Subtotaal</span><span className="tabular">{euro(subtotal)}</span></div>
          {orderType === "delivery" && (
            <div className="flex justify-between text-slate-500"><span>Bezorgkosten</span><span className="tabular">{quote?.available ? (fee > 0 ? euro(fee) : "Gratis") : "—"}</span></div>
          )}
          <div className="flex justify-between border-t border-slate-100 pt-2 text-base font-bold text-slate-900"><span>Totaal</span><span className="tabular" data-testid="checkout-total">{euro(total)}</span></div>
        </div>

        <Button onClick={submit} disabled={!canSubmit || submitting} className="mt-4 w-full bg-emerald-600 py-6 text-base hover:bg-emerald-700" data-testid="checkout-submit-button">
          {submitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />} Bestelling plaatsen
        </Button>
        <p className="mt-2 text-center text-xs text-slate-400">Betaling bij {orderType === "delivery" ? "levering" : "afhalen"}.</p>
      </div>
    </div>
  );
}
