from .models import Notification

def notify_supplier_new_request(product_request):
    supplier = product_request.product.supplier
    Notification.objects.create(
        recipient=supplier,
        notification_type=Notification.Type.NEW_REQUEST,
        title='New product request',
        message=f'{product_request.client.username} requested '
                f'{product_request.quantity} x {product_request.product.name}'
    )

def notify_client_response(product_request):
    Notification.objects.create(
        recipient=product_request.client,
        notification_type=Notification.Type.NEW_RESPONSE,
        title='Supplier responded to your request',
        message=f'Your request for {product_request.product.name} '
                f'has been accepted by {product_request.product.supplier.company_name}'
    )

def notify_client_status_update(product_request):
    status_messages = {
        'fulfilled': 'Your order has been fulfilled',
        'declined': 'Your request has been declined',
    }
    Notification.objects.create(
        recipient=product_request.client,
        notification_type=f'request_{product_request.status}',
        title=status_messages.get(product_request.status, 'Request updated'),
        message=f'Your request for {product_request.product.name} '
                f'is now {product_request.status}'
    )