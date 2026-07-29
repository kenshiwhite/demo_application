import logging
import urllib.request
import urllib.error
import json
from django.conf import settings

logger = logging.getLogger(__name__)


def send_verification_email(user):
    code = user.generate_verification_code()

    api_key = getattr(settings, 'POSTMARK_API_KEY', '')
    from_email = getattr(settings, 'POSTMARK_FROM_EMAIL', '')
    if not api_key or not from_email:
        logger.warning('Postmark is not configured. Verification email skipped for %s', user.email)
        return {'debug': True, 'sent': False, 'code': code}

    data = json.dumps({
        'From': from_email,
        'To': user.email,
        'Subject': 'Подтверждение email — SupplierApp',
        'TextBody': f'Здравствуйте, {user.username}!\n\nВаш код подтверждения: {code}\n\nВведите этот код в приложении.\nКод действителен 10 минут.',
        'MessageStream': 'outbound'
    }).encode('utf-8')

    req = urllib.request.Request(
        'https://api.postmarkapp.com/email',
        data=data,
        headers={
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'X-Postmark-Server-Token': api_key,
        },
        method='POST'
    )

    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode())
            logger.info('Postmark accepted verification email for %s: %s', user.email, result)
            return {'debug': False, 'sent': True, 'code': code}
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        logger.warning('Postmark rejected verification email for %s (HTTP %s): %s', user.email, e.code, error_body)
        if not getattr(settings, 'SMS_DEBUG_CODES', False):
            raise Exception(f'Postmark error {e.code}: {error_body}')
        return {'debug': True, 'sent': False, 'code': code, 'error': error_body}