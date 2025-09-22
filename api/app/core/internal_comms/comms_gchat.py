import requests


def send_google_chat_message(
    *,
    message: str,
    webhook_url: str,
) -> None:
    """
    Send notification via Google Chat webhook

    Args:
        notification: The notification data to send

    Returns:
        bool: True if sent successfully, False otherwise
    """

    payload = {"text": message}
    response = requests.post(
        webhook_url,
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=30,
    )
