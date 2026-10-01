import { useEffect, useMemo, useRef, useState } from "react";
import { Loader2, Phone, MapPin, StickyNote, ShoppingBag, Truck, RefreshCw, Clock, Pencil, Bell, BellRing, Check, Trash2 } from "lucide-react";
import { toast } from "sonner";
import api, { apiError } from "../../lib/api";
import { euro, formatTime } from "../../lib/format";
import { STATUS_LABELS, STATUS_STYLES } from "../../lib/constants";
import { useAuth } from "../../context/AuthContext";
import { EmptyState } from "../../components/EmptyState";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter,
} from "../../components/ui/dialog";
import {
  AlertDialog, AlertDialogContent, AlertDialogHeader, AlertDialogTitle, AlertDialogDescription,
  AlertDialogFooter, AlertDialogCancel, AlertDialogAction,
} from "../../components/ui/alert-dialog";

const FILTERS = [
  { key: "actief", label: "Actief", statuses: ["new", "accepted", "preparing", "ready"] },
  { key: "new", label: "Nieuw", statuses: ["new"] },
  { key: "completed", label: "Afgerond", statuses: ["completed"] },
  { key: "cancelled", label: "Geannuleerd", statuses: ["cancelled"] },
  { key: "all", label: "Alles", statuses: null },
];

const MINUTE_PRESETS = [10, 15, 20, 30, 45, 60, 90];

function MinutesPicker({ value, onChange, testPrefix }) {
  const isCustom = value != null && !MINUTE_PRESETS.includes(value);
  return (
    <div className="mt-1.5 space-y-2" data-testid={`minutes-picker-${testPrefix}`}>
      <div className="flex flex-wrap gap-2">
        {MINUTE_PRESETS.map((m) => (
          <button key={m} type="button" onClick={() => onChange(m)}
            data-testid={`minutes-${testPrefix}-${m}`}
            className={`rounded-lg border px-3 py-1.5 text-sm font-medium transition-colors ${value === m ? "border-emerald-600 bg-emerald-600 text-white" : "border-slate-200 text-slate-600 hover:bg-slate-50"}`}>
            {m} min
          </button>
        ))}
      </div>
      <div className="flex items-center gap-2">
        <Input type="number" min="1" max="600" placeholder="Aangepast"
          value={isCustom ? value : ""}
          onChange={(e) => onChange(e.target.value ? parseInt(e.target.value, 10) : null)}
          className="w-32" data-testid={`minutes-${testPrefix}-custom`} />
        <span className="text-sm text-slate-400">minuten</span>
      </div>
    </div>
  );
}

// Next forward action per status; `ready` label depends on order type.
function nextAction(order) {
  switch (order.status) {
    case "accepted": return { status: "preparing", label: "In bereiding" };
    case "preparing": return { status: "ready", label: order.orderType === "delivery" ? "Onderweg" : "Klaar om af te halen" };
    case "ready": return { status: "completed", label: "Voltooid" };
    default: return null;
  }
}

export default function Orders() {
  const { user } = useAuth();
  const isAdmin = user?.role === "restaurant_admin";
  const [orders, setOrders] = useState(null);
  const [filter, setFilter] = useState("actief");
  const [busy, setBusy] = useState(null);
  const [unseenIds, setUnseenIds] = useState([]);
  const [alertsOn, setAlertsOn] = useState(false);
  const unseen = unseenIds.length;
  const knownNewIds = useRef(new Set());
  const seededRef = useRef(false);
  const audioRef = useRef(null);
  const masterGainRef = useRef(null);
  const ringTimerRef = useRef(null);

  // One loud, phone-like trill burst via Web Audio (no asset, no 3rd party).
  // Routed through a master gain node so the loop can be cut instantly.
  const playRing = () => {
    const ctx = audioRef.current;
    const master = masterGainRef.current;
    if (!ctx || !master) return;
    try {
      const now = ctx.currentTime;
      const pulses = 4, pulseDur = 0.14, gap = 0.06;
      for (let i = 0; i < pulses; i++) {
        const start = now + i * (pulseDur + gap);
        const gain = ctx.createGain();
        gain.connect(master);
        gain.gain.setValueAtTime(0.0001, start);
        gain.gain.exponentialRampToValueAtTime(0.6, start + 0.02);
        gain.gain.setValueAtTime(0.6, start + pulseDur - 0.03);
        gain.gain.exponentialRampToValueAtTime(0.0001, start + pulseDur);
        [800, 1000].forEach((freq) => {
          const osc = ctx.createOscillator();
          osc.type = "triangle";
          osc.frequency.value = freq;
          osc.connect(gain);
          osc.start(start);
          osc.stop(start + pulseDur);
        });
      }
    } catch { /* ignore */ }
  };

  // Single repeating loop — guarded so overlapping orders never stack loops.
  const startRing = () => {
    const ctx = audioRef.current, master = masterGainRef.current;
    if (!ctx || !master) return;
    try { master.gain.cancelScheduledValues(ctx.currentTime); master.gain.setValueAtTime(1, ctx.currentTime); } catch { /* ignore */ }
    if (ringTimerRef.current) return;
    playRing();
    ringTimerRef.current = setInterval(playRing, 3000);
  };

  const stopRing = () => {
    if (ringTimerRef.current) { clearInterval(ringTimerRef.current); ringTimerRef.current = null; }
    const ctx = audioRef.current, master = masterGainRef.current;
    if (ctx && master) {
      try { master.gain.cancelScheduledValues(ctx.currentTime); master.gain.setValueAtTime(0, ctx.currentTime); } catch { /* ignore */ }
    }
  };

  const enableAlerts = async () => {
    try {
      const AC = window.AudioContext || window.webkitAudioContext;
      if (AC && !audioRef.current) {
        audioRef.current = new AC();
        masterGainRef.current = audioRef.current.createGain();
        masterGainRef.current.gain.value = 1;
        masterGainRef.current.connect(audioRef.current.destination);
      }
      if (audioRef.current?.state === "suspended") await audioRef.current.resume();
    } catch { /* ignore */ }
    if ("Notification" in window && Notification.permission === "default") {
      try { await Notification.requestPermission(); } catch { /* ignore */ }
    }
    setAlertsOn(true);
    toast.success("Meldingen ingeschakeld");
  };

  const notifyBrowser = (count) => {
    if ("Notification" in window && Notification.permission === "granted") {
      try {
        new Notification(count === 1 ? "Nieuwe bestelling" : `${count} nieuwe bestellingen`, {
          body: "Open het dashboard om de bestelling te bekijken.",
          tag: "upxero-new-order",
        });
      } catch { /* ignore */ }
    }
  };

  // Genuinely-new detection. First successful load seeds known ids (no alert);
  // afterwards only never-seen ids count as new. unseenIds is also pruned when an
  // order leaves "new" (accepted/rejected), which stops the ring automatically.
  const detectNew = (data) => {
    const newIds = data.filter((o) => o.status === "new").map((o) => o.id);
    const newIdSet = new Set(newIds);
    if (!seededRef.current) {
      newIds.forEach((id) => knownNewIds.current.add(id));
      seededRef.current = true;
      return;
    }
    const fresh = newIds.filter((id) => !knownNewIds.current.has(id));
    fresh.forEach((id) => knownNewIds.current.add(id));
    setUnseenIds((prev) => {
      const kept = prev.filter((id) => newIdSet.has(id));
      const added = fresh.filter((id) => !kept.includes(id));
      if (!added.length && kept.length === prev.length) return prev;
      return [...kept, ...added];
    });
    if (fresh.length > 0 && alertsOn) notifyBrowser(fresh.length);
  };

  const load = async () => {
    try { const { data } = await api.get("/orders"); setOrders(data); detectNew(data); }
    catch { setOrders([]); }
  };

  useEffect(() => {
    load();
    const t = setInterval(load, 10000);
    return () => clearInterval(t);
    // eslint-disable-next-line
  }, [alertsOn]);

  // Repeating alert loop: rings while alerts are on and >=1 unseen order remains.
  useEffect(() => {
    if (alertsOn && unseen > 0) startRing();
    else stopRing();
    return stopRing;
    // eslint-disable-next-line
  }, [alertsOn, unseen]);

  // Clean up audio + timers on unmount / navigation.
  useEffect(() => () => {
    stopRing();
    if (audioRef.current) { try { audioRef.current.close(); } catch { /* ignore */ } audioRef.current = null; masterGainRef.current = null; }
    document.title = "Upxero Ordering";
    // eslint-disable-next-line
  }, []);

  useEffect(() => {
    const base = "Bestellingen · Upxero Ordering";
    document.title = unseen > 0 ? `(${unseen}) ${base}` : base;
  }, [unseen]);

  const markSeen = () => setUnseenIds([]);

  const current = FILTERS.find((f) => f.key === filter);
  const filtered = useMemo(() => {
    if (!orders) return [];
    if (!current.statuses) return orders;
    return orders.filter((o) => current.statuses.includes(o.status));
  }, [orders, current]);

  const changeStatus = async (id, status, estimatedMinutes) => {
    setBusy(id + status);
    try {
      await api.patch(`/orders/${id}/status`, estimatedMinutes ? { status, estimatedMinutes } : { status });
      toast.success(`Bestelling → ${STATUS_LABELS[status]}`);
      await load();
    } catch (e) { toast.error(apiError(e)); } finally { setBusy(null); }
  };

  const updateEta = async (id, estimatedMinutes) => {
    setBusy(id + "eta");
    try {
      await api.patch(`/orders/${id}/eta`, { estimatedMinutes });
      toast.success("Verwachte tijd bijgewerkt");
      await load();
    } catch (e) { toast.error(apiError(e)); } finally { setBusy(null); }
  };

  const deleteOrder = async (id) => {
    setBusy(id + "delete");
    try {
      await api.delete(`/orders/${id}`);
      toast.success("Bestelling verwijderd");
      await load();
    } catch (e) { toast.error(apiError(e)); } finally { setBusy(null); }
  };

  return (
    <div className="space-y-6" data-testid="orders-page">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="font-heading text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl">Bestellingen</h1>
          <p className="mt-1 text-sm text-slate-500">Vernieuwt automatisch elke 10 seconden.</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {unseen > 0 && (
            <Button variant="outline" onClick={markSeen} className="border-emerald-300 bg-emerald-50 text-emerald-700 hover:bg-emerald-100" data-testid="orders-mark-seen">
              <Check className="mr-2 h-4 w-4" /> Markeer als gezien ({unseen})
            </Button>
          )}
          <Button variant="outline" onClick={alertsOn ? () => setAlertsOn(false) : enableAlerts}
            className={`border-slate-300 ${alertsOn ? "text-emerald-700" : ""}`} data-testid="orders-alerts-toggle">
            {alertsOn ? <BellRing className="mr-2 h-4 w-4 text-emerald-600" /> : <Bell className="mr-2 h-4 w-4" />}
            {alertsOn ? "Meldingen aan" : "Meldingen aanzetten"}
          </Button>
          <Button variant="outline" onClick={load} className="border-slate-300" data-testid="orders-refresh">
            <RefreshCw className="mr-2 h-4 w-4" /> Vernieuwen
          </Button>
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        {FILTERS.map((f) => (
          <button key={f.key} onClick={() => setFilter(f.key)} data-testid={`orders-filter-${f.key}`}
            className={`rounded-full px-4 py-1.5 text-sm font-medium transition-colors ${filter === f.key ? "bg-slate-900 text-white" : "bg-white text-slate-600 border border-slate-200 hover:bg-slate-50"}`}>
            {f.label}
          </button>
        ))}
      </div>

      {orders === null ? (
        <div className="grid place-items-center py-20"><Loader2 className="h-6 w-6 animate-spin text-emerald-600" /></div>
      ) : filtered.length === 0 ? (
        <EmptyState icon={ShoppingBag} title="Nog geen bestellingen" description="Nieuwe bestellingen verschijnen hier automatisch." testid="orders-empty" />
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {filtered.map((o) => (
            <OrderCard key={o.id} order={o} onStatus={changeStatus} onEta={updateEta} onDelete={deleteOrder} isAdmin={isAdmin} busy={busy} />
          ))}
        </div>
      )}
    </div>
  );
}

function OrderCard({ order, onStatus, onEta, onDelete, isAdmin, busy }) {
  const next = nextAction(order);
  const canCancel = !["completed", "cancelled"].includes(order.status);
  const canDelete = isAdmin && ["completed", "cancelled"].includes(order.status);
  const etaEditable = ["accepted", "preparing", "ready"].includes(order.status);
  const etaLabel = order.orderType === "delivery" ? "Verwachte bezorgtijd" : "Verwachte bereidingstijd";
  const [acceptOpen, setAcceptOpen] = useState(false);
  const [acceptMins, setAcceptMins] = useState(null);
  const [etaOpen, setEtaOpen] = useState(false);
  const [etaMins, setEtaMins] = useState(order.estimatedMinutes || null);
  const [deleteOpen, setDeleteOpen] = useState(false);

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
            {it.selectedOptions?.length > 0 && <p className="pl-5 text-xs text-slate-400">{it.selectedOptions.map((s) => s.optionName).join(", ")}</p>}
          </li>
        ))}
      </ul>

      {order.notes && (
        <p className="mt-3 flex items-start gap-1.5 rounded-lg bg-amber-50 p-2 text-xs text-amber-800">
          <StickyNote className="mt-0.5 h-3.5 w-3.5 shrink-0" /> {order.notes}
        </p>
      )}

      {etaEditable && (
        <div className="mt-3 flex items-center justify-between rounded-lg bg-slate-50 px-3 py-2 text-sm" data-testid={`order-eta-${order.orderNumber}`}>
          <span className="flex items-center gap-1.5 text-slate-600"><Clock className="h-3.5 w-3.5" /> {etaLabel}: <strong className="text-slate-900">{order.estimatedMinutes ? `ongeveer ${order.estimatedMinutes} min` : (order.estimatedTime || "—")}</strong></span>
          <button onClick={() => { setEtaMins(order.estimatedMinutes || null); setEtaOpen(true); }} className="inline-flex items-center gap-1 text-xs font-semibold text-emerald-600" data-testid={`order-eta-edit-${order.orderNumber}`}>
            <Pencil className="h-3 w-3" /> Wijzigen
          </button>
        </div>
      )}

      <div className="mt-3 space-y-0.5 border-t border-slate-100 pt-3 text-sm">
        <div className="flex justify-between text-slate-500"><span>Subtotaal</span><span className="tabular">{euro(order.subtotal)}</span></div>
        {order.orderType === "delivery" && (
          <div className="flex justify-between text-slate-500"><span>Bezorgkosten</span><span className="tabular">{order.deliveryFee > 0 ? euro(order.deliveryFee) : "Gratis"}</span></div>
        )}
        <div className="flex justify-between font-semibold text-slate-900"><span>Totaal</span><span className="tabular">{euro(order.total)}</span></div>
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        {order.status === "new" && (
          <>
            <Button onClick={() => { setAcceptMins(null); setAcceptOpen(true); }} className="flex-1 bg-emerald-600 hover:bg-emerald-700 active:scale-[0.98]" data-testid={`order-accept-${order.orderNumber}`}>
              Accepteren
            </Button>
            <Button variant="outline" onClick={() => onStatus(order.id, "cancelled")} disabled={busy === order.id + "cancelled"}
              className="border-slate-300 text-rose-600 hover:bg-rose-50 hover:text-rose-700" data-testid={`order-reject-${order.orderNumber}`}>
              Weigeren
            </Button>
          </>
        )}
        {next && (
          <Button onClick={() => onStatus(order.id, next.status)} disabled={busy === order.id + next.status}
            className="flex-1 bg-emerald-600 hover:bg-emerald-700 active:scale-[0.98]" data-testid={`order-advance-${order.orderNumber}`}>
            {busy === order.id + next.status && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            {next.label}
          </Button>
        )}
        {order.status !== "new" && canCancel && (
          <Button variant="outline" onClick={() => onStatus(order.id, "cancelled")} disabled={busy === order.id + "cancelled"}
            className="border-slate-300 text-rose-600 hover:bg-rose-50 hover:text-rose-700" data-testid={`order-cancel-${order.orderNumber}`}>
            Annuleren
          </Button>
        )}
        {canDelete && (
          <Button variant="outline" onClick={() => setDeleteOpen(true)} disabled={busy === order.id + "delete"}
            className="border-slate-300 text-rose-600 hover:bg-rose-50 hover:text-rose-700" data-testid={`order-delete-${order.orderNumber}`}>
            {busy === order.id + "delete" ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Trash2 className="mr-2 h-4 w-4" />}
            Verwijderen
          </Button>
        )}
      </div>

      {/* Accept + ETA dialog */}
      <Dialog open={acceptOpen} onOpenChange={setAcceptOpen}>
        <DialogContent className="sm:max-w-sm" data-testid={`accept-dialog-${order.orderNumber}`}>
          <DialogHeader><DialogTitle>Bestelling #{order.orderNumber} accepteren</DialogTitle></DialogHeader>
          <DialogDescription className="sr-only">Kies een verwachte tijd en bevestig de bestelling.</DialogDescription>
          <div>
            <Label>{etaLabel} (optioneel)</Label>
            <MinutesPicker value={acceptMins} onChange={setAcceptMins} testPrefix={`accept-${order.orderNumber}`} />
            <p className="mt-2 text-xs text-slate-400">De klant ziet deze tijd op de statuspagina en ontvangt een e-mail.</p>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => { setAcceptOpen(false); onStatus(order.id, "accepted"); }} data-testid={`accept-skip-${order.orderNumber}`}>Zonder tijd</Button>
            <Button onClick={() => { setAcceptOpen(false); onStatus(order.id, "accepted", acceptMins || undefined); }}
              className="bg-emerald-600 hover:bg-emerald-700" data-testid={`accept-confirm-${order.orderNumber}`}>Bevestigen</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ETA update dialog */}
      <Dialog open={etaOpen} onOpenChange={setEtaOpen}>
        <DialogContent className="sm:max-w-sm" data-testid={`eta-dialog-${order.orderNumber}`}>
          <DialogHeader><DialogTitle>{etaLabel} aanpassen</DialogTitle></DialogHeader>
          <DialogDescription className="sr-only">Pas de verwachte tijd van deze bestelling aan.</DialogDescription>
          <div>
            <Label>{etaLabel}</Label>
            <MinutesPicker value={etaMins} onChange={setEtaMins} testPrefix={`eta-${order.orderNumber}`} />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setEtaOpen(false)}>Annuleren</Button>
            <Button onClick={() => { setEtaOpen(false); if (etaMins) onEta(order.id, etaMins); }}
              className="bg-emerald-600 hover:bg-emerald-700" data-testid={`eta-save-${order.orderNumber}`}>Opslaan</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete confirmation */}
      <AlertDialog open={deleteOpen} onOpenChange={setDeleteOpen}>
        <AlertDialogContent data-testid={`delete-dialog-${order.orderNumber}`}>
          <AlertDialogHeader>
            <AlertDialogTitle>Bestelling #{order.orderNumber} verwijderen?</AlertDialogTitle>
            <AlertDialogDescription>
              Deze bestelling wordt permanent verwijderd en verdwijnt uit het overzicht. De bestelstatuslink van de klant werkt daarna niet meer. Deze actie kan niet ongedaan worden gemaakt.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel data-testid={`delete-cancel-${order.orderNumber}`}>Annuleren</AlertDialogCancel>
            <AlertDialogAction onClick={() => { setDeleteOpen(false); onDelete(order.id); }}
              className="bg-rose-600 hover:bg-rose-700" data-testid={`delete-confirm-${order.orderNumber}`}>
              Verwijderen
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
