import urllib.request
import urllib.error
import json
from django.conf import settings

def send_verification_email(user):
    code = user.generate_verification_code()

    data = json.dumps({
        'From': '221439@astanait.edu.kz',
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
            'X-Postmark-Server-Token': settings.POSTMARK_API_KEY,
        },
        method='POST'
    )

    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode())
            print(f'Postmark success: {result}')
            return code
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        print(f'Postmark error {e.code}: {error_body}')
        raise Exception(f'Postmark error {e.code}: {error_body}')