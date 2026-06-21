import urllib.request
import urllib.error
import urllib.parse
import json
import base64
from django.conf import settings

def send_verification_email(user):
    code = user.generate_verification_code()
    
    credentials = base64.b64encode(
        f'api:{settings.MAILGUN_API_KEY}'.encode()
    ).decode()
    
    data = urllib.parse.urlencode({
        'from': f'SupplierApp <mailgun@{settings.MAILGUN_DOMAIN}>',
        'to': user.email,
        'subject': 'Подтверждение email — SupplierApp',
        'text': f'Здравствуйте, {user.username}!\n\nВаш код подтверждения: {code}\n\nВведите этот код в приложении.\nКод действителен 10 минут.',
    }).encode('utf-8')

    # new Mailgun uses api.eu.mailgun.net for EU or api.mailgun.net for US
    req = urllib.request.Request(
        f'https://api.mailgun.net/v3/{settings.MAILGUN_DOMAIN}/messages',
        data=data,
        headers={
            'Authorization': f'Basic {credentials}',
        },
        method='POST'
    )
    
    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode())
            print(f'Mailgun success: {result}')
            return code
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        print(f'Mailgun error {e.code}: {error_body}')
        raise Exception(f'Mailgun error {e.code}: {error_body}')