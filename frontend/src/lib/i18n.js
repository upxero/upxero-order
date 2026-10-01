// Lightweight i18n. The Dutch string is the KEY, so Dutch renders byte-identical
// and any unconverted string safely falls back to Dutch. English is a lookup table.
// French can be added later as another map without changing call sites.
export const EN = {
  // Navigation / layout
  "Overzicht": "Overview",
  "Bestellingen": "Orders",
  "Menu": "Menu",
  "Categorieën": "Categories",
  "Bezorging": "Delivery",
  "Openingstijden": "Opening hours",
  "Instellingen": "Settings",
  "Profiel": "Profile",
  "Personeel": "Staff",
  "Platform": "Platform",
  "Beheerder": "Admin",
  "Medewerker": "Staff",
  "Bekijk bestelpagina": "View order page",
  "Uitloggen": "Log out",

  // Order statuses
  "Nieuw": "New",
  "Geaccepteerd": "Accepted",
  "In bereiding": "Preparing",
  "Klaar": "Ready",
  "Afgerond": "Completed",
  "Geannuleerd": "Cancelled",

  // Order status page / confirmation
  "Bestelling niet gevonden": "Order not found",
  "Deze link is ongeldig of verlopen.": "This link is invalid or has expired.",
  "Bestelling bevestigd!": "Order confirmed!",
  "Bezorgen": "Delivery",
  "Afhalen": "Pickup",
  "Subtotaal": "Subtotal",
  "Bezorgkosten": "Delivery fee",
  "Totaal": "Total",
  "Gratis": "Free",
  "Opmerking:": "Note:",
  "Terug naar restaurant": "Back to restaurant",
  "Verwachte bezorgtijd": "Estimated delivery time",
  "Verwachte bereidingstijd": "Estimated preparation time",
  "Wacht op bevestiging van het restaurant.": "Waiting for the restaurant to confirm.",
  "Klaar om af te halen": "Ready for pickup",
  "Geschatte tijd": "Estimated time",
  "Status": "Status",
  "Restaurant": "Restaurant",
  "Bestelling": "Order",
  "Wacht op bevestiging": "Awaiting confirmation",
  "Bevestigd": "Confirmed",
  "Onderweg": "On its way",
  "Voltooid": "Completed",
  "Deze bestelling is geannuleerd.": "This order has been cancelled.",
  "Je bestelling is ontvangen en wacht op bevestiging van het restaurant.": "Your order has been received and is awaiting confirmation from the restaurant.",
  "Deze pagina werkt automatisch bij. Betaling bij {pay}.": "This page updates automatically. Payment on {pay}.",
  "Betaling bij {pay}.": "Payment on {pay}.",
  "levering": "delivery",
  "afhalen": "pickup",
  "Bedankt {name}. {resto} heeft je bestelling ontvangen.": "Thank you {name}. {resto} has received your order.",
  "Bestelling niet gevonden.": "Order not found.",

  // Profile / language
  "Taal": "Language",
  "Profiel opgeslagen. Adres wordt automatisch gelokaliseerd voor bezorging.": "Profile saved. The address is geocoded automatically for delivery.",
};

const MAPS = { en: EN };

export function makeT(lang) {
  const code = lang === "nl" ? "nl" : "en";
  const map = MAPS[code];
  return (s, vars) => {
    let out = code === "nl" || !map ? s : (map[s] ?? s);
    if (vars) for (const k of Object.keys(vars)) out = out.replaceAll(`{${k}}`, vars[k]);
    return out;
  };
}

export const LANGUAGES = [
  { code: "en", label: "English" },
  { code: "nl", label: "Nederlands" },
];
