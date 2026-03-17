from p04_error_handling.s00_get_env_vars import get_environment_variables
from p04_error_handling.s01_filter_messages import filter_messages
from p04_error_handling.s02_send_gchat_message import send_notification


def handle_errors(*, message):
    """Send notification to Google Chat using webhook"""
    # --- Get environment variables ---
    env_vars = get_environment_variables()
    environment = env_vars.require_environment()

    # --- Filter messages ---
    if environment == "PROD":
        send_message = filter_messages(message)
        match send_message:
            case True:
                _response = send_notification(
                    webhook_url=env_vars.require_webhook_url(),
                    message=message,
                )
            case False:
                pass
