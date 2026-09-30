import uuid

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from db import db
from models import AvailabilityReq, CategoryReq, MenuItemReq
from security import require_roles, restaurant_id_of
from utils import now_iso, oid, serialize

router = APIRouter(prefix="/menu", tags=["menu"])

admin_only = require_roles("restaurant_admin")
any_staff = require_roles("restaurant_admin", "restaurant_staff")


# ---------- Categories ----------


@router.get("/categories")
async def list_categories(user: dict = Depends(any_staff)):
    rid = str(restaurant_id_of(user))
    cats = await db.menu_categories.find({"restaurantId": rid}).sort("sortOrder", 1).to_list(500)
    return [serialize(c) for c in cats]


@router.post("/categories")
async def create_category(payload: CategoryReq, user: dict = Depends(admin_only)):
    rid = str(restaurant_id_of(user))
    ts = now_iso()
    doc = {**payload.model_dump(), "restaurantId": rid, "createdAt": ts, "updatedAt": ts}
    res = await db.menu_categories.insert_one(doc)
    doc["_id"] = res.inserted_id
    return serialize(doc)


@router.put("/categories/{category_id}")
async def update_category(category_id: str, payload: CategoryReq, user: dict = Depends(admin_only)):
    rid = str(restaurant_id_of(user))
    result = await db.menu_categories.update_one(
        {"_id": oid(category_id), "restaurantId": rid},
        {"$set": {**payload.model_dump(), "updatedAt": now_iso()}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Categorie niet gevonden")
    doc = await db.menu_categories.find_one({"_id": oid(category_id)})
    return serialize(doc)


@router.delete("/categories/{category_id}")
async def delete_category(category_id: str, user: dict = Depends(admin_only)):
    rid = str(restaurant_id_of(user))
    result = await db.menu_categories.delete_one({"_id": oid(category_id), "restaurantId": rid})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Categorie niet gevonden")
    await db.menu_items.delete_many({"categoryId": category_id, "restaurantId": rid})
    return {"message": "Categorie verwijderd"}


# ---------- Items ----------


@router.get("/items")
async def list_items(user: dict = Depends(any_staff)):
    rid = str(restaurant_id_of(user))
    items = await db.menu_items.find({"restaurantId": rid}).sort("sortOrder", 1).to_list(1000)
    return [serialize(i) for i in items]


def _prepare_groups(groups):
    out = []
    for g in groups:
        gd = g.model_dump()
        gd["id"] = gd.get("id") or str(uuid.uuid4())
        for opt in gd["options"]:
            opt["id"] = opt.get("id") or str(uuid.uuid4())
        out.append(gd)
    return out


@router.post("/items")
async def create_item(payload: MenuItemReq, user: dict = Depends(admin_only)):
    rid = str(restaurant_id_of(user))
    cat = await db.menu_categories.find_one({"_id": oid(payload.categoryId), "restaurantId": rid})
    if not cat:
        raise HTTPException(status_code=400, detail="Ongeldige categorie")
    ts = now_iso()
    doc = payload.model_dump()
    doc["optionGroups"] = _prepare_groups(payload.optionGroups)
    doc.update({"restaurantId": rid, "createdAt": ts, "updatedAt": ts})
    res = await db.menu_items.insert_one(doc)
    doc["_id"] = res.inserted_id
    return serialize(doc)


@router.put("/items/{item_id}")
async def update_item(item_id: str, payload: MenuItemReq, user: dict = Depends(admin_only)):
    rid = str(restaurant_id_of(user))
    cat = await db.menu_categories.find_one({"_id": oid(payload.categoryId), "restaurantId": rid})
    if not cat:
        raise HTTPException(status_code=400, detail="Ongeldige categorie")
    doc = payload.model_dump()
    doc["optionGroups"] = _prepare_groups(payload.optionGroups)
    doc["updatedAt"] = now_iso()
    result = await db.menu_items.update_one(
        {"_id": oid(item_id), "restaurantId": rid}, {"$set": doc}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Product niet gevonden")
    updated = await db.menu_items.find_one({"_id": oid(item_id)})
    return serialize(updated)


@router.patch("/items/{item_id}/availability")
async def set_availability(item_id: str, payload: AvailabilityReq, user: dict = Depends(any_staff)):
    rid = str(restaurant_id_of(user))
    result = await db.menu_items.update_one(
        {"_id": oid(item_id), "restaurantId": rid},
        {"$set": {"isAvailable": payload.isAvailable, "updatedAt": now_iso()}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Product niet gevonden")
    updated = await db.menu_items.find_one({"_id": oid(item_id)})
    return serialize(updated)


@router.delete("/items/{item_id}")
async def delete_item(item_id: str, user: dict = Depends(admin_only)):
    rid = str(restaurant_id_of(user))
    result = await db.menu_items.delete_one({"_id": oid(item_id), "restaurantId": rid})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Product niet gevonden")
    return {"message": "Product verwijderd"}
