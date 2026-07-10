from .models import Notification
from .push import send_push_notification
import threading

def _send_push_async(user, title, body, data=None):
    if user.expo_push_token:
        thread = threading.Thread(
            target=send_push_notification,
            args=(user.expo_push_token, title, body, data)
        )
        thread.daemon = True
        thread.start()

def notify_supplier_new_request(request_obj):
    supplier = request_obj.supplier
    client = request_obj.client
    title = 'Новая заявка'
    client_name = (client.company_name or client.username) if client else request_obj.business_client.name
    body = f'{client_name} отправил заявку на {request_obj.items.count()} товар(ов)'

    Notification.objects.create(
        recipient=supplier,
        title=title,
        message=body,
        notification_type='new_request',
    )
    _send_push_async(supplier, title, body, {
        'type': 'new_request',
        'request_id': request_obj.id,
    })

def notify_client_response(request_obj):
    client = request_obj.client
    if not client:
        return
    supplier = request_obj.supplier
    title = 'Ответ на заявку'
    body = f'{supplier.company_name or supplier.username} ответил на вашу заявку #{request_obj.id}'

    Notification.objects.create(
        recipient=client,
        title=title,
        message=body,
        notification_type='new_response',
    )
    _send_push_async(client, title, body, {
        'type': 'new_response',
        'request_id': request_obj.id,
    })

def notify_client_status_update(request_obj):
    client = request_obj.client
    if not client:
        return
    supplier = request_obj.supplier
    status_labels = {
        'accepted': 'принята',
        'declined': 'отклонена',
        'fulfilled': 'выполнена',
    }
    status_label = status_labels.get(request_obj.status, request_obj.status)
    title = f'Заявка #{request_obj.id} {status_label}'
    body = f'{supplier.company_name or supplier.username} обновил статус вашей заявки'

    Notification.objects.create(
        recipient=client,
        title=title,
        message=body,
        notification_type=f'request_{request_obj.status}',
    )
    _send_push_async(client, title, body, {
        'type': f'request_{request_obj.status}',
        'request_id': request_obj.id,
    })
