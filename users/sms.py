import logging
import re

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

GATEWAY_BASE_URL = 'https://gatewayapi.telegram.org/'


def normalize_phone(phone):
    digits = re.sub(r'\D', '', phone or '')

    if len(digits) == 11 and digits.startswith('8'):
        digits = '7' + digits[1:]
    elif len(digits) == 10:
        digits = '7' + digits

    if len(digits) != 11 or not digits.startswith('7'):
        raise ValueError('Phone must be a Kazakhstan number in +7 format')

    return f'+{digits}'


def send_telegram_verification(phone, code):
    """
    Deliver a verification code via Telegram Gateway
    (https://core.telegram.org/gateway) instead of SMS. We generate and
    store the code ourselves (User.generate_phone_verification_code), so
    Telegram is used purely as a delivery channel here — we pass our own
    `code` and never need to call checkVerificationStatus, meaning the
    rest of the verify-phone flow (attempts, expiry, code comparison)
    stays exactly as it was with SMSC.

    Note the real trade-off versus SMS: this only reaches numbers that
    have an active Telegram account. Anyone without Telegram gets
    nothing back from this call — there is no separate "undeliverable"
    signal beyond `ok: false` / a non-2xx response, which we treat the
    same as any other delivery failure below.
    """
    token = getattr(settings, 'TELEGRAM_GATEWAY_TOKEN', '')
    if not token:
        logger.info('Telegram Gateway token is not configured. Verification skipped for %s', phone)
        return {'debug': True, 'sent': False}

    response = requests.post(
        GATEWAY_BASE_URL + 'sendVerificationMessage',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'phone_number': phone,
            'code': code,
            'sender_username': getattr(settings, 'TELEGRAM_GATEWAY_SENDER', '') or None,
            'ttl': 600,  # matches the 10-minute expiry set in generate_phone_verification_code
        },
        timeout=10,
    )
    response.raise_for_status()
    data = response.json()

    if not data.get('ok'):
        logger.warning('Telegram Gateway rejected verification for %s: %s', phone, data)
        raise RuntimeError(data.get('error', 'Telegram Gateway request failed'))

    return data.get('result', {})


def send_phone_verification_code(user):
    code = user.generate_phone_verification_code()
    try:
        result = send_telegram_verification(user.phone, code)
    except Exception as exc:
        if not getattr(settings, 'SMS_DEBUG_CODES', False):
            raise
        logger.warning(
            'Telegram verification delivery failed for %s, returning debug code: %s',
            user.phone,
            exc,
        )
        result = {'debug': True, 'sent': False, 'error': str(exc)}

    if result.get('debug'):
        result['code'] = code
    return result