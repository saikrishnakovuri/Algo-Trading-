import requests
import json
import logging

logger = logging.getLogger("WebhookService")

def push_to_webhook(url: str, payload: dict, auth_token: str = None):
    """REQ 30-2: External signal export via Webhook."""
    try:
        headers = {"Content-Type": "application/json"}
        if auth_token:
            headers["Authorization"] = f"Bearer {auth_token}"
            
        resp = requests.post(url, data=json.dumps(payload), headers=headers, timeout=5)
        if resp.status_code == 200:
            logger.info(f"Webhook push successful to {url}")
        else:
            logger.warning(f"Webhook push failed ({resp.status_code}): {resp.text}")
    except Exception as e:
        logger.error(f"Webhook error: {e}")
