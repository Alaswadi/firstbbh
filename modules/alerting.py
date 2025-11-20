import requests
import json
from config import WEBHOOK_URL

def send_alert(message, severity="info", details=None):
    """
    Sends an alert to the configured webhook.
    
    Args:
        message (str): The main alert message.
        severity (str): Severity level (info, low, medium, high, critical).
        details (dict, optional): Additional details to include in the payload.
    """
    if not WEBHOOK_URL:
        print(f"[Alert - {severity}] {message}")
        if details:
            print(f"Details: {json.dumps(details, indent=2)}")
        return

    payload = {
        "message": message,
        "severity": severity,
        "details": details or {}
    }

    try:
        response = requests.post(WEBHOOK_URL, json=payload, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Failed to send alert: {e}")
