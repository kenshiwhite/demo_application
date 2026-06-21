from django.db.models import Sum, Count, Avg, F
from django.utils import timezone
from datetime import timedelta
from requests.models import ProductRequest, RequestItem


def get_supplier_analytics(supplier, period_days=30):
    since = timezone.now() - timedelta(days=period_days)

    # base queryset — fulfilled requests for this supplier
    fulfilled = ProductRequest.objects.filter(
        supplier=supplier,
        status='fulfilled',
        updated_at__gte=since
    )

    # total revenue
    total_revenue = fulfilled.aggregate(
        total=Sum('total_price')
    )['total'] or 0

    # total orders
    total_orders = fulfilled.count()

    # average order value
    avg_order = fulfilled.aggregate(
        avg=Avg('total_price')
    )['avg'] or 0

    # total products sold
    total_products_sold = RequestItem.objects.filter(
        request__in=fulfilled
    ).aggregate(total=Sum('quantity'))['total'] or 0

    # revenue by day
    from django.db.models.functions import TruncDate
    revenue_by_day = fulfilled.annotate(
        date=TruncDate('updated_at')
    ).values('date').annotate(
        revenue=Sum('total_price'),
        orders=Count('id')
    ).order_by('date')

    # top products
    top_products = RequestItem.objects.filter(
        request__in=fulfilled
    ).values(
        'product__name'
    ).annotate(
        total_quantity=Sum('quantity'),
        total_revenue=Sum('total')
    ).order_by('-total_revenue')[:5]

    # orders by status (all time for this supplier)
    status_counts = ProductRequest.objects.filter(
        supplier=supplier
    ).values('status').annotate(count=Count('id'))

    # pending requests count
    pending_count = ProductRequest.objects.filter(
        supplier=supplier,
        status='pending'
    ).count()

    return {
        'total_revenue': float(total_revenue),
        'total_orders': total_orders,
        'avg_order_value': float(avg_order),
        'total_products_sold': total_products_sold,
        'pending_requests': pending_count,
        'revenue_by_day': [
            {
                'date': str(item['date']),
                'revenue': float(item['revenue']),
                'orders': item['orders']
            }
            for item in revenue_by_day
        ],
        'top_products': [
            {
                'name': item['product__name'],
                'quantity': item['total_quantity'],
                'revenue': float(item['total_revenue'])
            }
            for item in top_products
        ],
        'status_counts': {
            item['status']: item['count']
            for item in status_counts
        }
    }