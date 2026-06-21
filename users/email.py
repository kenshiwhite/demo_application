import resend
from django.conf import settings

def send_verification_email(user):
    code = user.generate_verification_code()
    
    resend.api_key = settings.RESEND_API_KEY
    
    resend.Emails.send({
        'from': 'SupplierApp <onboarding@resend.dev>',
        'to': user.email,
        'subject': 'Подтверждение email — SupplierApp',
        'text': f'''
Здравствуйте, {user.username}!

Ваш код подтверждения: {code}

Введите этот код в приложении для подтверждения email.
Код действителен 10 минут.

Если вы не регистрировались в SupplierApp, игнорируйте это письмо.
        '''
    })