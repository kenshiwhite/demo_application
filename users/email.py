import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from django.conf import settings

def send_verification_email(user):
    code = user.generate_verification_code()

    msg = MIMEMultipart()
    msg['From'] = settings.EMAIL_HOST_USER
    msg['To'] = user.email
    msg['Subject'] = 'Подтверждение email — SupplierApp'

    body = f'''Здравствуйте, {user.username}!

Ваш код подтверждения: {code}

Введите этот код в приложении.
Код действителен 10 минут.'''

    msg.attach(MIMEText(body, 'plain'))

    context = ssl.create_default_context()

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=context) as server:
            server.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
            server.sendmail(settings.EMAIL_HOST_USER, user.email, msg.as_string())
            print(f'Email sent successfully to {user.email}')
            return code
    except Exception as e:
        print(f'Gmail error: {str(e)}')
        raise Exception(f'Gmail error: {str(e)}')