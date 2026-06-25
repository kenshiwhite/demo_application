from exponent_server_sdk import (
    DeviceNotRegisteredError,
    PushClient,
    PushMessage,
    PushServerError,
    PushTicketError,
)
from requests.exceptions import ConnectionError, HTTPError
import logging

logger = logging.getLogger(__name__)

def send_push_notification(expo_token, title, body, data=None):
    if not expo_token or not expo_token.startswith('ExponentPushToken'):
        logger.warning(f'Invalid expo token: {expo_token}')
        return False

    try:
        response = PushClient().publish(
            PushMessage(
                to=expo_token,
                title=title,
                body=body,
                data=data or {},
                sound='default',
                priority='high',
            )
        )
        response.validate_response()
        logger.info(f'Push sent successfully to {expo_token}')
        return True
    except DeviceNotRegisteredError:
        logger.warning(f'Device not registered: {expo_token}')
        return False
    except (PushServerError, PushTicketError, ConnectionError, HTTPError) as e:
        logger.error(f'Push notification error: {str(e)}')
        return False
    except Exception as e:
        logger.error(f'Unexpected push error: {str(e)}')
        return False