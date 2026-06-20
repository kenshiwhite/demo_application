from django.core.mail import send_mail
from django.conf import settings

def send_verification_email(user):
    code = user.generate_verification_code()
    send_mail(
        subject='Подтверждение email — SupplierApp',
        message=f'''
Здравствуйте, {user.username}!

Ваш код подтверждения: {code}

Введите этот код в приложении для подтверждения email.
Код действителен 10 минут.

Если вы не регистрировались в SupplierApp, проигнорируйте это письмо.
        ''',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )