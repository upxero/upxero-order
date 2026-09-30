# Upxero Ordering — PRD

## Original problem statement
Build a real, production-ready V1 multi-tenant SaaS: commission-free online ordering for independent restaurants, takeaways and snack bars in Belgium & the Netherlands. React + FastAPI + MongoDB, GitHub/Atlas/Render-ready. Dutch-first UI, i18n-ready. Restaurant dashboard + public mobile-first ordering page. Server-authoritative pricing & delivery, reliable order persistence, strict tenant isolation. No online payments and no Whop in V1.

## Architecture
- **Backend** (`/app/backend`): FastAPI, modular routers (auth, restaurants, menu, orders, public, admin), `security.py` (bcrypt + JWT httpOnly cookies + role guards + tenant scoping), `services/distance.py` (Photon→Nominatim geocoding + haversine, cached), `services/notifications.py` (abstraction), `seed.py` (super admin + demo restaurant).
- **Frontend** (`/app/frontend/src`): React (CRA), AuthContext, ProtectedRoute, DashboardLayout (sidebar), dashboard pages, public order pages. Tailwind + shadcn/ui, emerald/slate brand, Outfit/Plus Jakarta Sans.
- **DB**: MongoDB, collections users/restaurants/menu_categories/menu_items/orders/counters/login_attempts/geocode_cache with indexes; partial-unique idempotency index on orders.

## User personas
- super_admin (Upxero platform), restaurant_admin (owner), restaurant_staff (employee), customer (guest, no account).

## Core requirements (static)
- Multi-tenant isolation enforced server-side on every request.
- Server-authoritative prices, option prices, subtotal, delivery fee, total; order snapshot at creation time.
- Distance-based delivery zones (fee + min order), optional free-delivery threshold, geocoding abstraction.
- Order workflow new→accepted→preparing→ready→completed (+cancelled) with transition rules.
- Duplicate-order protection via idempotency keys.
- Ordering enable/disable + opening-hours enforced server-side.

## Implemented (2026-06)
- JWT cookie auth: register (creates restaurant), login, logout, me, refresh; bcrypt; brute-force lockout.
- Restaurant dashboard: Overzicht (real stats/empty states), Bestellingen (auto-refresh 10s, status actions), Menu (products + option groups + availability), Categorieën CRUD, Bezorging (zones + free delivery), Openingstijden, Instellingen (ordering/pickup toggles), Profiel (address auto-geocoded).
- Public `/order/:slug`: header/open status, category tabs, product cards, options modal, cart sheet, pickup/delivery checkout, delivery quote, confirmation page.
- Server-side order pipeline validate→calculate→persist→confirm with edge-case guards (unavailable item, invalid option, ordering off, closed, out-of-zone, below minimum, duplicate).
- Basic super-admin platform view (list/create restaurants & users).
- Seeded demo restaurant (bistro-demo) with menu, options, zones; README + .env.example.
- **Tested**: 22/22 backend pytest pass; 100% of exercised frontend flows pass; tenant isolation, idempotency, price-security, below-minimum all verified.
- **Password reset (2026-06)**: /auth/forgot-password + /auth/reset-password with hashed single-use 1h tokens (password_reset_tokens, TTL), no user-enumeration (fixed generic response), per-email (5/15m) + app-wide (10/10m) throttling, tokenVersion bump invalidates old sessions, brute-force lockout cleared on reset. Reset email via Emergent-managed email (services/email.py). Frontend routes /wachtwoord-vergeten + /reset-wachtwoord + login "Wachtwoord vergeten?" link. Verified: real send 202 to mike.upxero@gmail.com; old pass rejected, new works, token reuse blocked. Super admin seeded as mike.upxero@gmail.com.

## Backlog / remaining (not in V1)
- P1: true realtime (WebSockets/SSE), password reset & email verification, staff invitations, in-app QR generation, richer super-admin, SEO/OG polish, PWA install.
- P2: online payments, Whop entitlements/subscriptions, full FR/EN translations, analytics, driving-distance provider, POS integrations.

## Next tasks
- Wire notifications channel (email/browser) via existing abstraction.
- Add realtime order push with dashboard fallback to polling.
- Complete FR/EN locale files.
