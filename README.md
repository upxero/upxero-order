# Upxero Ordering

Commission-free online ordering for independent restaurants, takeaways and snack bars in Belgium and the Netherlands. Each restaurant manages its own menu and orders; customers order pickup or delivery from a public page — no account required.

Built as a real, multi-tenant SaaS: **React** frontend, **FastAPI** backend, **MongoDB** database.

---

## Features

- **Self-registration** — an owner signs up and their restaurant is created in one step.
- **Secure auth** — email/password with bcrypt hashing and JWT sessions (httpOnly cookies). Roles: `super_admin`, `restaurant_admin`, `restaurant_staff`.
- **Strict multi-tenant isolation** — every request is authorized server-side; a restaurant can never read or modify another restaurant's data.
- **Dutch restaurant dashboard** — Overzicht, Bestellingen, Menu, Categorieën, Bezorging, Openingstijden, Instellingen, Profiel.
- **Menu management** — categories and products with options/add-ons (required/optional, single/multiple), availability toggles, images by URL.
- **Delivery zones** — distance-based zones with fee and minimum order; optional free delivery threshold.
- **Public ordering page** — `/order/<slug>`, mobile-first, cart, options, pickup/delivery checkout.
- **Server-authoritative order integrity** — all prices, option prices, subtotal, delivery fee and total are recalculated on the server from the live menu; orders store a snapshot so later menu changes never alter past orders.
- **Delivery calculation** — address geocoding via OpenStreetMap/Nominatim + haversine distance, behind a replaceable `services/distance.py` abstraction.
- **Order workflow** — Nieuw → Geaccepteerd → In bereiding → Klaar → Afgerond (+ Annuleren); dashboard auto-refreshes every ~10s.
- **Duplicate-order protection** via idempotency keys.
- **No online payments in V1** — payment on pickup/delivery (model leaves room to add payments later).

---

## Architecture

```
/app
├── backend/                 FastAPI app (multi-tenant REST API)
│   ├── server.py            entry point (app, routers, CORS, startup)
│   ├── db.py                Mongo client + index creation
│   ├── security.py          password hashing, JWT, auth dependencies, role guards
│   ├── models.py            Pydantic request models
│   ├── utils.py             serialization, slugs, order numbers
│   ├── seed.py              seeds super admin + demo restaurant
│   ├── routers/             auth, restaurants, menu, orders, public, admin
│   └── services/            distance (geocoding), notifications (abstractions)
└── frontend/                React (CRA) SPA
    └── src/
        ├── context/         AuthContext
        ├── components/      layout, protected route, shared UI
        ├── pages/           auth, dashboard/*, order/* (public)
        └── lib/             api client, formatting, constants
```

The backend is the security boundary. All protected routes validate authentication, role, and restaurant ownership. The frontend is never authoritative for prices, fees, totals or availability.

---

## Local development

Requirements: Node.js 18+, Python 3.11+, MongoDB (local or Atlas).

### Backend
```bash
cd backend
pip install -r requirements.txt
# create .env from /.env.example
uvicorn server:app --reload --host 0.0.0.0 --port 8001
```

### Frontend
```bash
cd frontend
npm install        # (yarn also works)
# set REACT_APP_BACKEND_URL in frontend/.env
npm start
```

App: http://localhost:3000 · API: http://localhost:8001/api

### Demo credentials (seeded on first boot)
- Restaurant admin: `owner@demo.upxero.com` / `Demo!2025`
- Restaurant staff: `staff@demo.upxero.com` / `Demo!2025`
- Platform super admin: `admin@upxero.com` / (value of `ADMIN_PASSWORD`)
- Demo ordering page: `/order/bistro-demo`

---

## Environment variables

See `.env.example`. Backend reads `MONGO_URL`, `DB_NAME`, `JWT_SECRET`, `FRONTEND_URL`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`, `NOMINATIM_USER_AGENT`, `CORS_ORIGINS`. Frontend reads `REACT_APP_BACKEND_URL`. Never commit real secrets.

---

## MongoDB Atlas

1. Create a cluster and a database user.
2. Copy the connection string into `MONGO_URL`, set `DB_NAME`.
3. Whitelist your Render service IPs (or allow 0.0.0.0/0 for testing).
4. Indexes are created automatically on backend startup (`db.py::ensure_indexes`).

---

## Deploy to Render

**Backend (Web Service)**
- Root: `backend`
- Build: `pip install -r requirements.txt`
- Start: `uvicorn server:app --host 0.0.0.0 --port $PORT`
- Env vars: `MONGO_URL`, `DB_NAME`, `JWT_SECRET`, `FRONTEND_URL`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`, `NOMINATIM_USER_AGENT`, `CORS_ORIGINS`.

**Frontend (Static Site)**
- Root: `frontend`
- Build: `npm install && npm run build`
- Publish directory: `build`
- Env var: `REACT_APP_BACKEND_URL` = your backend service URL.

Set the backend `FRONTEND_URL`/`CORS_ORIGINS` to the static site URL.

---

## API overview

```
POST   /api/auth/register          POST /api/auth/login   POST /api/auth/logout
GET    /api/auth/me                POST /api/auth/refresh

GET    /api/restaurant/me          PUT  /api/restaurant/profile
PUT    /api/restaurant/delivery    PUT  /api/restaurant/opening-hours   PUT /api/restaurant/settings

GET/POST         /api/menu/categories        PUT/DELETE /api/menu/categories/:id
GET/POST         /api/menu/items             PUT/DELETE /api/menu/items/:id
PATCH            /api/menu/items/:id/availability

GET   /api/orders    GET /api/orders/stats    GET /api/orders/:id    PATCH /api/orders/:id/status

GET   /api/public/restaurant/:slug
POST  /api/public/restaurant/:slug/quote      POST /api/public/restaurant/:slug/orders
GET   /api/public/orders/:id

GET   /api/admin/restaurants   GET /api/admin/users   POST /api/admin/restaurants   (super_admin)
```

---

## Production checklist

- [ ] `MONGO_URL` points to Atlas, `DB_NAME` set
- [ ] Strong random `JWT_SECRET`
- [ ] `FRONTEND_URL` / `CORS_ORIGINS` set to the deployed frontend origin
- [ ] `REACT_APP_BACKEND_URL` set to the deployed backend URL
- [ ] `ADMIN_PASSWORD` changed from default
- [ ] Indexes verified (auto-created on boot)
- [ ] Restaurant address set so delivery distances resolve

---

## Roadmap (not in V1)

Realtime push (WebSockets/SSE), password reset & email verification, staff invitations, notifications (email/SMS/WhatsApp) via `services/notifications.py`, in-app QR generation, driving-distance provider swap, online payments, Whop entitlements, full FR/EN translations, analytics.
