import requests


def send_google_chat_message(
    *,
    message: str,
    webhook_url: str,
) -> None:
    """todo

    Args:
        message: TODO: describe.
        webhook_url: TODO: describe.
    """

    payload = {"text": message}
    requests.post(
        webhook_url,
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=30,
    )
