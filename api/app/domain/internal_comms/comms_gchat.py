import requests


def send_google_chat_message(
    *,
    message: str,
    webhook_url: str,
) -> None:
    """Send a message to Google Chat via webhook.

    Args:
        message: Message text to send.
        webhook_url: Google Chat incoming webhook URL.
    """

    payload = {"text": message}
    requests.post(
        webhook_url,
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=30,
    )
