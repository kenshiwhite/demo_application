from django.contrib.auth import get_user_model
from django.db.models import Sum, Count, Avg, F, Q
from django.utils import timezone
from datetime import timedelta
from product_requests.models import ProductRequest, RequestItem
from users.models import BusinessClient

User = get_user_model()


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

    sales_reps = list(User.objects.filter(
        role=User.Role.SALES_REP,
        business_supplier=supplier,
    ).values('id', 'username'))

    client_counts = {
        item['sales_rep_id']: item['count']
        for item in BusinessClient.objects.filter(
            supplier=supplier,
            sales_rep__isnull=False,
        ).values('sales_rep_id').annotate(count=Count('id'))
    }
    sales_stats = {
        item['sales_rep_id']: item
        for item in ProductRequest.objects.filter(
            supplier=supplier,
            sales_rep__isnull=False,
            updated_at__gte=since,
        ).values('sales_rep_id').annotate(
            request_count=Count('id'),
            fulfilled_count=Count('id', filter=Q(status='fulfilled')),
            revenue=Sum('total_price', filter=Q(status='fulfilled')),
        )
    }

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
        },
        'sales_reps': [
            {
                'id': rep['id'],
                'name': rep['username'],
                'client_count': client_counts.get(rep['id'], 0),
                'request_count': sales_stats.get(rep['id'], {}).get('request_count', 0),
                'fulfilled_count': sales_stats.get(rep['id'], {}).get('fulfilled_count', 0),
                'revenue': float(sales_stats.get(rep['id'], {}).get('revenue') or 0),
            }
            for rep in sales_reps
        ],
    }


def get_rep_analytics(rep, period_days=30):
    """Same shape as get_supplier_analytics, but scoped to just the
    requests a single sales rep personally handled — this is what a rep
    sees on their own stats page, not the whole company's numbers."""
    since = timezone.now() - timedelta(days=period_days)

    fulfilled = ProductRequest.objects.filter(
        sales_rep=rep,
        status='fulfilled',
        updated_at__gte=since
    )

    total_revenue = fulfilled.aggregate(total=Sum('total_price'))['total'] or 0
    total_orders = fulfilled.count()
    avg_order = fulfilled.aggregate(avg=Avg('total_price'))['avg'] or 0
    total_products_sold = RequestItem.objects.filter(
        request__in=fulfilled
    ).aggregate(total=Sum('quantity'))['total'] or 0

    from django.db.models.functions import TruncDate
    revenue_by_day = fulfilled.annotate(
        date=TruncDate('updated_at')
    ).values('date').annotate(
        revenue=Sum('total_price'),
        orders=Count('id')
    ).order_by('date')

    top_products = RequestItem.objects.filter(
        request__in=fulfilled
    ).values('product__name').annotate(
        total_quantity=Sum('quantity'),
        total_revenue=Sum('total')
    ).order_by('-total_revenue')[:5]

    status_counts = ProductRequest.objects.filter(
        sales_rep=rep
    ).values('status').annotate(count=Count('id'))

    pending_count = ProductRequest.objects.filter(
        sales_rep=rep,
        status='pending'
    ).count()

    client_count = BusinessClient.objects.filter(sales_rep=rep).count()
    client_count += User.objects.filter(role=User.Role.CLIENT, assigned_sales_rep=rep).count()

    return {
        'total_revenue': float(total_revenue),
        'total_orders': total_orders,
        'avg_order_value': float(avg_order),
        'total_products_sold': total_products_sold,
        'pending_requests': pending_count,
        'client_count': client_count,
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
        },
    }