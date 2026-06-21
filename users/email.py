import resend
from django.conf import settings

def send_verification_email(user):
    try:
        code = user.generate_verification_code()
        
        resend.api_key = settings.RESEND_API_KEY
        
        response = resend.Emails.send({
            'from': 'SupplierApp <onboarding@resend.dev>',
            'to': [user.email],
            'subject': 'Подтверждение email — SupplierApp',
            'text': f'''
Здравствуйте, {user.username}!

Ваш код подтверждения: {code}

Введите этот код в приложении для подтверждения email.
Код действителен 10 минут.

Если вы не регистрировались в SupplierApp, игнорируйте это письмо.
            '''
        })
        print(f'Resend response: {response}')
        return code
    except Exception as e:
        print(f'Resend error: {str(e)}')
        raise e