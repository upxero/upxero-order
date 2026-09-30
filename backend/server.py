import logging
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

from fastapi import APIRouter, FastAPI  # noqa: E402
from starlette.middleware.cors import CORSMiddleware  # noqa: E402

from db import ensure_indexes  # noqa: E402
from routers import admin, auth, menu, orders, public, restaurants  # noqa: E402
from seed import seed_data  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("upxero")

app = FastAPI(title="Upxero Ordering API", version="1.0.0")

health = APIRouter(prefix="/api")


@health.get("/")
async def root():
    return {"service": "Upxero Ordering API", "status": "ok"}


@health.get("/health")
async def health_check():
    return {"status": "healthy"}


app.include_router(health)
app.include_router(auth.router, prefix="/api")
app.include_router(restaurants.router, prefix="/api")
app.include_router(menu.router, prefix="/api")
app.include_router(orders.router, prefix="/api")
app.include_router(public.router, prefix="/api")
app.include_router(admin.router, prefix="/api")

frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:3000")
allowed = list({frontend_url, "http://localhost:3000"})
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def on_startup():
    await ensure_indexes()
    await seed_data()
    logger.info("Upxero Ordering API gestart")


@app.on_event("shutdown")
async def on_shutdown():
    from db import client
    client.close()
