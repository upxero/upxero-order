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

## Customer Order Status & Timing — V2 refinement (2026-06)
- **ETA as duration**: replaced `estimatedTime` (HH:MM clock) with `estimatedMinutes` (int 1-600). Dashboard accept/update use minute presets 10/15/20/30/45/60/90 + custom field (MinutesPicker). Status page & emails show "ongeveer X minuten" (no clock time, no timezone issues). Pickup label "Verwachte bereidingstijd", delivery "Verwachte bezorgtijd". Historical orders keep their `estimatedTime` string and still render.
- **Customer email required**: `CustomerReq.email` is now `EmailStr` (server-side), enforced in addition to frontend regex. Phone still required. Helper copy: "We gebruiken je e-mailadres voor je bestelbevestiging en statusupdates."
- **Secure status token + expiry**: token is HMAC-derived from the order id (`derive_status_token`, JWT_SECRET), only its SHA-256 hash (`statusTokenHash`) is persisted — plaintext never stored for new orders. 30-day expiry (`statusTokenExpiresAt`); expired → 410, order never deleted. Legacy plaintext `statusToken` orders still resolve via fallback. New index `orders.statusTokenHash`.
- **Customer emails**: every customer email keeps a "Bekijk je bestelling" button → `/order-status/<token>`; accepted email shows the minute estimate; ETA-change email states the new minutes. `customerEmailsEnabled` and `orderEmailsEnabled` remain independent. All emails stay async BackgroundTasks — failure never rolls back order/status writes. `_assert_safe_email` still gates every send.
- **Status page** stays optional (customer can close the tab and rely on emails).
- **Verified (2026-06)**: 49/49 backend pytest pass (new test_upxero_status_timing.py), 100% of exercised frontend flows; email/phone validation (422), hashed token, legacy fallback (200), expiry (410), random token (404), read-only customer endpoint, accept/eta minute presets, invalid minutes (422), full workflow + cancel, tenant isolation on order routes. No regressions.

## New-order alerts on Bestellingen (2026-06)
- **Frontend-only** (no backend/API changes) on `dashboard/Orders.jsx`. Keeps the existing 10s polling — no WebSockets/SSE/push.
- Genuinely-new detection: first successful `/orders` load seeds a `knownNewIds` ref (no alert); only ids first seen after mount count as new, so polling never re-alerts the same order.
- Short two-tone WebAudio chime + browser Notification (permission-gated, never bypassed) fire only after the user clicks "Meldingen aanzetten" (that click also satisfies the autoplay gesture gate).
- Tab-title badge: `(N) Bestellingen · Upxero Ordering` when there are unseen new orders; restores on unmount.
- Explicit "Markeer als gezien (N)" button resets the badge; seen ids stay known so they are not re-counted. Works identically for admin & staff; tenant isolation unchanged.
- **Verified (2026-06)**: backend regression 49/49 pass (no regressions); frontend 100% — first-load seeding, new-order detection <10s, badge format, dedup across poll cycles, mark-seen reset, toggle on/off for admin+staff; no AudioContext/Notification/title console errors.

## Order deletion + logo rendering fix (2026-06)
- **Delete completed/cancelled orders** (Part 1 of the uploads task). New admin-only `DELETE /api/orders/{id}` (`routers/orders.py`, dep `require_roles('restaurant_admin')`): tenant-scoped `{_id, restaurantId}`, 404 if missing, 400 if status not in {completed, cancelled}, else hard delete. Staff → 403. Order numbers stay monotonic (counter uses `$inc`, never reset). Deleted order's customer status link returns 404 (lookup finds nothing). Dashboard shows a "Verwijderen" button with an AlertDialog confirmation on completed/cancelled cards, admin-only (`Orders.jsx`).
- **Logo rendering bug fixed**: `components/Logo.jsx` now takes an optional `src` prop and renders the restaurant logo (`object-contain`, aspect preserved, stateful fallback to the Upxero brand on load error). Wired into the public ordering page header (`OrderPage.jsx`, `src={restaurant.logo}`) and the dashboard sidebar + mobile header (`DashboardLayout.jsx`). No upload/storage introduced — still a URL field for now.
- **Verified (2026-06)**: 59/59 backend pytest (incl. new `tests/test_order_delete.py`), 100% frontend — full delete authz matrix, tenant isolation, status-link invalidation, counter integrity, UI gating for admin vs staff, logo render + fallback. No regressions.

## Storage decision for Parts 2–4 (uploads) — pending implementation
- Chosen: **Emergent-managed Object Storage** (via integration proxy; uses `EMERGENT_LLM_KEY` + `INTEGRATION_PROXY_URL`, soft-delete in DB, files served through authenticated backend endpoints).
- ⚠️ **Production caveat (Render + MongoDB Atlas)**: Emergent Object Storage is reached through the Emergent integration proxy and keyed by `EMERGENT_LLM_KEY`. Even when the app is hosted on Render, uploads/downloads continue to route through `integrations.emergentagent.com` and require a valid `EMERGENT_LLM_KEY` in the Render env. Files persist (not ephemeral), but the app stays dependent on the Emergent proxy + key being present in production. No native S3/Atlas-local storage. This must be confirmed/accepted before building parts 2–4.
- Parts 2 (logo upload), 3 (menu-item image upload), 4 (menu-file upload) are NOT implemented yet, per instruction to verify storage first.

## File uploads via GridFS (Parts 2–4, 2026-06)
- **Storage**: MongoDB GridFS on the existing Atlas connection — bucket `uploads` (`uploads.files` / `uploads.chunks`). New `services/storage.py` (`save_upload`, `open_file`, `delete_file`). No Emergent Object Storage, no local filesystem, no new service. Server-side **magic-byte MIME sniffing** (PNG/JPEG/WebP/PDF) is authoritative; size caps enforced server-side.
- **Part 2 — Restaurant logo**: admin-only `POST/DELETE /api/restaurant/logo` (JPG/PNG/WebP, ≤5 MB). Stored as `restaurants.logoFileId`; replace deletes the old file. Served publicly at `GET /api/public/restaurant/{slug}/logo`. Rendered on the public ordering page header + dashboard sidebar; falls back to legacy `logo` URL then the Upxero brand.
- **Part 3 — Menu item images**: admin-only `POST/DELETE /api/menu/items/{id}/image` (≤5 MB). Stored as `menu_items.imageFileId`; served at `GET /api/public/restaurant/{slug}/menu-item/{id}/image` (scoped to the item's restaurant). Legacy `image` URLs still work; public payload returns a route path and never leaks `imageFileId`. Deleting an item cleans up its GridFS image.
- **Part 4 — Restaurant menu file**: admin-only `POST/DELETE /api/restaurant/menu-file` (PDF/JPG/PNG, ≤10 MB). Stored as `restaurants.menuFileId/menuFileName/menuFileType`; served at `GET /api/public/restaurant/{slug}/menu-file` (inline). Admin view/replace/remove in Profile page.
- **Security**: all upload/delete endpoints are `restaurant_admin` only (staff → 403); tenant-scoped `{_id, restaurantId}`; public serving routes derive the file from the restaurant/item (file id never user-supplied), so no cross-tenant access or enumeration; deleted/replaced files are hard-removed from GridFS; no generic `/files/{id}` route; images served with content-type + Cache-Control.
- **Frontend**: new `lib/files.js` URL resolver; Profile + MenuItems upload widgets with preview/replace/remove; `Logo.jsx` src + brand fallback.
- **Production note (Render + Atlas)**: fully self-contained in Atlas — no Emergent runtime dependency. For scale, front `order.upxero.com` with Cloudflare for image caching (ingress currently rewrites `/api` Cache-Control to no-store on preview).
- **Verified (2026-06)**: 78/78 backend pytest (incl. new `tests/test_uploads.py` — upload/replace/remove cycles, magic-byte rejection, empty/oversized, unauth, staff 403, cross-tenant 404, legacy URL passthrough, no-file fallback), 100% frontend. No regressions to Part 1 deletion or logo fallback.

## Public menu PDF link + FINAL V1 production-readiness audit (2026-06)
- **Public PDF link**: added "Bekijk menukaart als PDF" on the public ordering page header (`OrderPage.jsx`, data-testid `public-menu-pdf-link`), shown only when `restaurant.menuFileUrl` exists; opens the existing unauthenticated route `GET /api/public/restaurant/{slug}/menu-file` (correct application/pdf, 404 when removed, no GridFS ids leaked). Works mobile + desktop.
- **Docs hardening (P3)**: `server.py` now gates FastAPI `/docs`, `/redoc`, `/openapi.json` behind `ENABLE_DOCS` (default on for preview). Set `ENABLE_DOCS=false` on Render to hide them.
- **Final audit result**: 81/81 backend pytest pass (1 pre-existing geocoding skip), 100% frontend, **no P0/P1/P2 bugs**. Security review passed: explicit-origin CORS + credentials (no wildcard), HttpOnly+Secure+SameSite=None auth cookies, HS256 JWT w/ tokenVersion invalidation, bcrypt, login brute-force lockout, env-only secrets, no debug/reload, no stray test endpoints, GridFS-only storage (no Emergent Object Storage, no local FS), status tokens hashed + 30-day expiry, email failures never corrupt orders.
- **Deployment env checklist (Render + Atlas)**: set `MONGO_URL` (Atlas SRV), `DB_NAME`, `JWT_SECRET` (strong), `CORS_ORIGINS`/`FRONTEND_URL`=https://order.upxero.com, `EMERGENT_EMAIL_KEY`, `EMAIL_FROM_NAME`, `ADMIN_EMAIL`/`ADMIN_PASSWORD`, `NOMINATIM_USER_AGENT`, `ENABLE_DOCS=false`; frontend `REACT_APP_BACKEND_URL`=production backend URL. **V1 is ready to deploy.**
- P1: true realtime (WebSockets/SSE), password reset & email verification, staff invitations, in-app QR generation, richer super-admin, SEO/OG polish, PWA install.
- P2: online payments, Whop entitlements/subscriptions, full FR/EN translations, analytics, driving-distance provider, POS integrations.

## Next tasks
- Wire notifications channel (email/browser) via existing abstraction.

## Staff Invites (2026-10)
- **Backend**: admin-only, tenant-scoped endpoints on `/restaurant/staff` (invite, list, PATCH active, revoke invitation) + public `/public/invitation/{token}` (GET) and `/public/invitation/accept` (POST). New `staff_invitations` collection: hashed single-use tokens (SHA-256), 7-day TTL, `used`/`revoked` flags, atomic claim via find_one_and_update. restaurantId + email come ONLY from the stored invitation (never the request), so an invitee cannot be attached to another tenant. Accept creates a `restaurant_staff` user (bcrypt pw, tokenVersion 0) and auto-logs-in. Deactivation bumps tokenVersion to kill live sessions; inactive users blocked at login. Tokens never returned in any response.
- **Frontend**: `/dashboard/personeel` (admin) — invite by email, list staff with activate/deactivate, list + revoke pending invites; sidebar "Personeel" item (admin-only); public `/staff-uitnodiging?token=` acceptance page.
- **Email**: `send_staff_invitation_email` reuses the managed email integration (fixed template).
- **Verified**: accept/reuse/expired/revoked handling, staff-scoped access, admin-endpoint 403 for staff, foreign-order 404, deactivation kills session + blocks login, reactivation restores. Existing suite 19 passed / 3 skipped — no regressions.
