# Upxero Ordering — V1 Build Plan

Commission-free online ordering for independent restaurants, takeaways and snack bars in Belgium and the Netherlands.
Each restaurant manages its own menu and orders; customers order pickup or delivery from a public page, no account needed.

## Who it's for
- **Restaurant owners/managers** — set up their restaurant, build a menu, configure pickup/delivery, and manage incoming orders from any device.
- **Restaurant staff** — handle live orders and move them through the kitchen workflow.
- **Customers (guests)** — browse a restaurant's menu via a link or QR code and place an order in a few taps.
- **Upxero admin (super admin)** — a basic internal view to create and oversee restaurants across the platform.

## Core features and experience

**Accounts & access**
- Open self-registration: a restaurant owner signs up and their restaurant is created in the same step.
- Secure login/logout. Three roles: super admin (Upxero), restaurant admin (owner), restaurant staff.
- Strict separation between restaurants — one restaurant can never see or touch another's menu, orders or settings. Enforced on the server for every request.

**Restaurant dashboard (Dutch UI)**
- **Overzicht** — today's order count, new-order count, current ordering status, pickup/delivery status, quick links. Real numbers only; empty states when there's nothing yet.
- **Bestellingen** — live order list that auto-refreshes every ~10 seconds. Shows order number, time, customer, pickup/delivery, items + options, subtotal, delivery fee, total, address, notes and status. Action buttons move an order: Nieuw → Geaccepteerd → In bereiding → Klaar → Afgerond, plus Annuleren.
- **Menu / Categorieën / Producten** — create, edit, reorder, activate/deactivate categories and products; set name, description, price, image, availability. Unavailable products can't be ordered.
- **Product options / add-ons** — option groups with individual options and extra prices (e.g. Extra kaas €1,50), required or optional, single or multiple choice.
- **Bezorging** — enable/disable delivery, set restaurant address/location, and configure multiple delivery zones (distance range, delivery fee, minimum order amount, on/off). Optional "gratis bezorgd vanaf €X".
- **Openingstijden** — per-weekday open/close times and closed days.
- **Instellingen / Profiel** — restaurant name, logo, description, phone, email, address, postal code, city, default language; master switch for "Online bestellen aan/uit"; pickup on/off.

**Public ordering page** (`/order/<restaurant-slug>`)
- Shows restaurant name, logo, description, open/closed status, categories, products, prices and options.
- Cart, then checkout: choose Afhalen or Bezorgen, enter contact details (name, phone, optional email), delivery address when applicable, and notes.
- For delivery: the address is geocoded (via free OpenStreetMap/Nominatim), distance from the restaurant is measured, the matching zone sets the fee and minimum order. Clear Dutch messages when outside the area ("Helaas bezorgen we niet op dit adres.") or below minimum ("Voor bezorging in jouw gebied is een minimum bestelling van €X vereist.").
- Order confirmation only after the order is genuinely saved.

**Order integrity (server-authoritative)**
- All prices, option prices, subtotals, delivery fees and totals are recalculated on the server from the live menu — the browser total is never trusted.
- Each order stores a snapshot of product names, options and prices at order time, so later menu/price changes never alter past orders.
- Human-friendly per-restaurant order numbers (#1042, #1043…).
- Guardrails for the real-world edge cases: item became unavailable, price changed, ordering disabled or restaurant closed mid-checkout, below minimum, outside zone, and accidental double-submit (duplicate protection).

**Super admin (basic)**
- Create restaurants and see the list of restaurants/users across the platform. Kept minimal; the restaurant experience is the priority.

**Languages**
- UI ships in natural Dutch. The system is structured for French and English to be added later, with a per-restaurant default language (Dutch to start).

## User flow

**Restaurant owner**
Registreren → restaurantgegevens invullen → openingstijden → afhalen/bezorgen instellen → bezorgzones → categorieën aanmaken → producten toevoegen → online bestellen inschakelen → bestellink/QR delen.

**Customer**
Open restaurantpagina (link/QR) → kies categorie → kies product → kies opties → toevoegen aan winkelmand → winkelmand bekijken → afhalen of bezorgen → gegevens (+ adres bij bezorging) → bezorgkosten en totaal → bestelling plaatsen → bevestiging.

**Restaurant handling the order**
Nieuwe bestelling verschijnt op dashboard → Accepteren → In bereiding → Klaar → Afronden (of Annuleren).

## UI/UX feel
- Serious, clean SaaS product — professional, modern, trustworthy, fast. Not a food marketplace, not a marketing site.
- Draws on Upxero's brand (commission-free, calm and practical, Dutch-first) without copying the marketing website; uses the Upxero name as "Upxero Ordering".
- Mobile-first throughout; the customer ordering flow is especially optimized for phones. Dashboard works well on desktop, tablet and phone.
- Restrained: minimal decoration, no fake charts or fabricated statistics, clear actions, useful empty states, good contrast and accessible forms.

## Implementation phases

**Phase 1 — MVP (built now)**
The complete end-to-end product: self-registration and login, multi-tenant security, restaurant dashboard, menu/category/product management with options, opening hours, pickup and delivery settings with configurable zones, the public ordering page, cart and checkout, server-side price and delivery calculation with Nominatim geocoding, reliable order persistence to MongoDB with confirmation, order management with statuses, auto-refreshing order list, a basic super admin, one seeded demo restaurant with menu and login credentials, plus README and .env.example. GitHub-, MongoDB Atlas- and Render-ready.

**Phase 2 — later**
True realtime order updates (WebSockets/SSE), password reset and email verification, staff invitations, notifications (email/browser), QR generation in-app, driving-distance delivery provider swap, richer super-admin, SEO/Open Graph polish, PWA install.

**Phase 3 — later**
Online payments, Whop subscriptions/entitlements, full French/English translations, analytics, and other growth features — all anticipated by the architecture but out of V1.

## Assumptions
- **Authentication**: custom email + password with secure hashing and JWT sessions (no third-party social login in V1), since the brief calls for real password-based auth.
- **Geocoding/distance**: free OpenStreetMap/Nominatim for address→coordinates plus straight-line (haversine) distance, behind a replaceable service so a driving-distance provider can be swapped in later. If geocoding ever fails, the customer is told clearly rather than given a fake result. Nominatim is used responsibly per its usage policy: requests send a proper identifying User-Agent, respect rate limits, restaurant coordinates are geocoded once and cached/reused, and repeated geocoding of the same address is avoided.
- **Order updates**: dashboard auto-refreshes every ~10 seconds in V1; live push is Phase 2.
- **Super admin**: minimal (create/list restaurants and users) — not a full admin suite.
- **Demo data**: one seeded demo restaurant with categories, products, options and delivery zones, and documented login credentials, so the full flow can be tested immediately.
- **Registration**: open self-service; the first user of a new restaurant becomes its restaurant admin.
- **No online payments in V1** — payment is handled on pickup/delivery; the order model leaves room to add payments later.
- **Images**: stored as URLs/references (with a simple upload approach) rather than binaries in the database, so external image storage can be connected later.
- **Currency/format**: euro, Dutch number/price formatting; initial markets Belgium and the Netherlands.
