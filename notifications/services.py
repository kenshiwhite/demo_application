from .models import Notification

def notify_supplier_new_request(product_request):
    supplier = product_request.supplier
    item_count = product_request.items.count()
    Notification.objects.create(
        recipient=supplier,
        notification_type=Notification.Type.NEW_REQUEST,
        title='Новая заявка',
        message=f'{product_request.client.username} оформил заявку на {item_count} товар(ов) на сумму {int(product_request.total_price):,} ₸'
    )

def notify_client_response(product_request):
    Notification.objects.create(
        recipient=product_request.client,
        notification_type=Notification.Type.NEW_RESPONSE,
        title='Поставщик ответил на вашу заявку',
        message=f'Ваша заявка от {product_request.supplier.company_name or product_request.supplier.username} принята'
    )

def notify_client_status_update(product_request):
    status_messages = {
        'fulfilled': 'Ваш заказ выполнен',
        'declined': 'Ваша заявка отклонена',
    }
    Notification.objects.create(
        recipient=product_request.client,
        notification_type=f'request_{product_request.status}',
        title=status_messages.get(product_request.status, 'Заявка обновлена'),
        message=f'Заявка от {product_request.supplier.company_name or product_request.supplier.username} теперь имеет статус: {product_request.status}'
    )