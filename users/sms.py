import logging
import re

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def normalize_phone(phone):
    digits = re.sub(r'\D', '', phone or '')

    if len(digits) == 11 and digits.startswith('8'):
        digits = '7' + digits[1:]
    elif len(digits) == 10:
        digits = '7' + digits

    if len(digits) != 11 or not digits.startswith('7'):
        raise ValueError('Phone must be a Kazakhstan number in +7 format')

    return f'+{digits}'


def format_phone_for_smsc(phone):
    return normalize_phone(phone).lstrip('+')


def send_sms(phone, message):
    login = getattr(settings, 'SMSC_LOGIN', '')
    password = getattr(settings, 'SMSC_PASSWORD', '')
    sender = getattr(settings, 'SMSC_SENDER', '')

    if not login or not password:
        logger.info('SMSC credentials are not configured. SMS skipped for %s', phone)
        return {'debug': True, 'sent': False}

    params = {
        'login': login,
        'psw': password,
        'phones': format_phone_for_smsc(phone),
        'mes': message,
        'fmt': 3,
        'charset': 'utf-8',
    }
    if sender:
        params['sender'] = sender

    response = requests.get(
        'https://smsc.kz/sys/send.php',
        params=params,
        timeout=10,
    )
    response.raise_for_status()
    data = response.json()

    if data.get('error'):
        logger.warning('SMSC rejected message for %s: %s', phone, data)
        raise RuntimeError(data.get('error'))

    return data


def send_phone_verification_code(user):
    code = user.generate_phone_verification_code()
    try:
        result = send_sms(
            user.phone,
            f'InStock verification code: {code}',
        )
    except Exception as exc:
        if not getattr(settings, 'SMS_DEBUG_CODES', False):
            raise
        logger.warning(
            'SMS delivery failed for %s, returning debug code: %s',
            user.phone,
            exc,
        )
        result = {'debug': True, 'sent': False, 'error': str(exc)}

    if result.get('debug'):
        result['code'] = code
    return result
