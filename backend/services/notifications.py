"""Notification abstraction for future email / SMS / push / WhatsApp.

V1 only logs. Callers use notify(...) so a real channel can be added later
without changing business logic.
"""
import logging

logger = logging.getLogger("upxero.notifications")


async def notify_new_order(restaurant_id: str, order_number: int):
    logger.info("Nieuwe bestelling #%s voor restaurant %s", order_number, restaurant_id)


async def notify_status_change(restaurant_id: str, order_number: int, status: str):
    logger.info("Bestelling #%s status -> %s (restaurant %s)", order_number, status, restaurant_id)
