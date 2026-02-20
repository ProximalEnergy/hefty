import json

import urllib3


def send_notification(webhook_url, message):
    """Send notification to Google Chat using webhook"""
    http = urllib3.PoolManager()

    message_data = {"text": message}

    encoded_data = json.dumps(message_data).encode("utf-8")

    response = http.request(
        "POST",
        webhook_url,
        body=encoded_data,
        headers={"Content-Type": "application/json"},
    )

    return response
