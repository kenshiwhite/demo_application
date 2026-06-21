import urllib.request
import urllib.error
import json
from django.conf import settings

def send_verification_email(user):
    code = user.generate_verification_code()
    
    data = json.dumps({
        'from': 'SupplierApp <onboarding@resend.dev>',
        'to': [user.email],
        'subject': 'Подтверждение email — SupplierApp',
        'text': f'''Здравствуйте, {user.username}!\n\nВаш код подтверждения: {code}\n\nВведите этот код в приложении.\nКод действителен 10 минут.'''
    }).encode('utf-8')
    
    req = urllib.request.Request(
        'https://api.resend.com/emails',
        data=data,
        headers={
            'Authorization': f'Bearer {settings.RESEND_API_KEY}',
            'Content-Type': 'application/json',
        },
        method='POST'
    )
    
    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode())
            print(f'Resend success: {result}')
            return code
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        print(f'Resend HTTP error {e.code}: {error_body}')
        raise Exception(f'Resend error {e.code}: {error_body}')