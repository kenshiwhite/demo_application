import urllib.request
import urllib.error
import json
from django.conf import settings

def send_verification_email(user):
    code = user.generate_verification_code()

    data = json.dumps({
        'sender': {'email': 'onsupply.noreply@gmail.com', 'name': 'SupplierApp'},
        'to': [{'email': user.email}],
        'subject': 'Подтверждение email — SupplierApp',
        'textContent': f'Здравствуйте, {user.username}!\n\nВаш код подтверждения: {code}\n\nВведите этот код в приложении.\nКод действителен 10 минут.',
    }).encode('utf-8')

    req = urllib.request.Request(
        'https://api.brevo.com/v3/smtp/email',
        data=data,
        headers={
            'api-key': settings.BREVO_API_KEY,
            'Content-Type': 'application/json',
        },
        method='POST'
    )

    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode())
            print(f'Brevo success: {result}')
            return code
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        print(f'Brevo error {e.code}: {error_body}')
        raise Exception(f'Brevo error {e.code}: {error_body}')