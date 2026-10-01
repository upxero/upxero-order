export const STATUS_LABELS = {
  new: "Nieuw",
  accepted: "Geaccepteerd",
  preparing: "In bereiding",
  ready: "Klaar",
  completed: "Afgerond",
  cancelled: "Geannuleerd",
};

export const STATUS_LABELS_EN = {
  new: "New",
  accepted: "Accepted",
  preparing: "Preparing",
  ready: "Ready",
  completed: "Completed",
  cancelled: "Cancelled",
};

export const statusLabel = (status, lang) =>
  (lang === "nl" ? STATUS_LABELS : STATUS_LABELS_EN)[status] || status;

export const STATUS_STYLES = {
  new: "bg-amber-100 text-amber-800 border-amber-200",
  accepted: "bg-blue-100 text-blue-800 border-blue-200",
  preparing: "bg-indigo-100 text-indigo-800 border-indigo-200",
  ready: "bg-emerald-100 text-emerald-800 border-emerald-200",
  completed: "bg-slate-100 text-slate-600 border-slate-200",
  cancelled: "bg-rose-100 text-rose-800 border-rose-200",
};

// Next status button per current status
export const NEXT_ACTION = {
  new: { status: "accepted", label: "Accepteren" },
  accepted: { status: "preparing", label: "In bereiding" },
  preparing: { status: "ready", label: "Klaar" },
  ready: { status: "completed", label: "Afronden" },
};

export const DAYS = [
  ["monday", "Maandag"],
  ["tuesday", "Dinsdag"],
  ["wednesday", "Woensdag"],
  ["thursday", "Donderdag"],
  ["friday", "Vrijdag"],
  ["saturday", "Zaterdag"],
  ["sunday", "Zondag"],
];
