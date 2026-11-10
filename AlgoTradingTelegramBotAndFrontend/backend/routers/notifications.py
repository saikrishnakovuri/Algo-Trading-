from fastapi import APIRouter
from pydantic import BaseModel
import os
import json

router = APIRouter(prefix="/api/notifications", tags=["notifications"])

@router.get("/subscriptions")
def get_subscriptions():
    # This would read from config/notifications.yaml or .env
    return {
        "telegram": {"enabled": True, "chat_id": "12345678"},
        "email": {"enabled": False}
    }

class ToggleSubscription(BaseModel):
    channel: str
    enabled: bool

@router.post("/toggle")
def toggle_subscription(req: ToggleSubscription):
    return {"status": "success", "message": f"{req.channel} subscription set to {req.enabled}"}

@router.post("/test-send")
def test_send_notification():
    # Call notification_service.py test method
    return {"status": "success", "message": "Test notification sent"}
