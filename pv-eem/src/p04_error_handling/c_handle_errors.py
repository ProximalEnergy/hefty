from p04_error_handling.s00_get_env_vars import get_environment_variables
from p04_error_handling.s01_filter_messages import filter_messages
from p04_error_handling.s02_send_gchat_message import send_notification


def handle_errors(message):
    """Send notification to Google Chat using webhook"""
    # --- Get environment variables ---
    env_vars = get_environment_variables()
    WEBHOOK_URL = env_vars["WEBHOOK_URL"]
    ENVIRONMENT = env_vars["ENVIRONMENT"]

    # --- Filter messages ---
    if ENVIRONMENT == "PROD":
        send_message = filter_messages(message)
        match send_message:
            case True:
                _response = send_notification(WEBHOOK_URL, message)
            case False:
                pass
