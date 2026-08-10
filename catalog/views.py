# catalog/views.py
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Q, Sum, F, DecimalField
from django.db.models.functions import Coalesce
from django.utils import timezone
from calendar import monthrange
from datetime import datetime
from users.permissions import IsSupplier, IsSupplierStaff
from .analytics import get_supplier_analytics, get_rep_analytics
from rest_framework import viewsets, permissions
from .models import Product, SupplierExpense, CATEGORY_CHOICES
from .serializers import ProductSerializer, SupplierExpenseSerializer
from .filters import ProductFilter
from users.permissions import IsSupplier
from product_requests.models import ProductRequest, RequestItem
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_categories(request):
    categories = [{'value': v, 'label': l} for v, l in CATEGORY_CHOICES]
    return Response(categories)


class ProductViewSet(viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = ProductFilter
    search_fields = ['name', 'description']
    ordering_fields = ['price', 'created_at', 'stock_quantity']

    def get_queryset(self):
        user = self.request.user
        city = self.request.query_params.get('city')

        if user.role in ['supplier', 'sales_rep']:
            supplier = user if user.role == 'supplier' else user.business_supplier
            qs = Product.objects.filter(supplier=supplier)
            # A sales rep assigned to a specific city only manages that
            # city's stock. Reps with no city set (or suppliers themselves)
            # see every city, optionally narrowed by ?city=.
            if user.role == 'sales_rep' and user.city:
                qs = qs.filter(city=user.city)
            elif city:
                qs = qs.filter(city=city)
            return qs

        qs = Product.objects.filter(is_available=True)
        if city:
            qs = qs.filter(city=city)
        return qs

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated(), IsSupplierStaff()]
        return [permissions.IsAuthenticated()]

    def perform_create(self, serializer):
        user = self.request.user
        if not user.is_phone_verified:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('Verify your phone number before adding products')
        supplier = user if user.role == 'supplier' else user.business_supplier
        # A rep assigned to a specific city can only stock that city.
        city = serializer.validated_data.get('city')
        if user.role == 'sales_rep' and user.city and city != user.city:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('Вы можете управлять товарами только своего города.')
        serializer.save(supplier=supplier)


class SupplierExpenseViewSet(viewsets.ModelViewSet):
    serializer_class = SupplierExpenseSerializer
    permission_classes = [permissions.IsAuthenticated, IsSupplier]

    def get_queryset(self):
        qs = SupplierExpense.objects.filter(supplier=self.request.user)
        period = self.request.query_params.get('period')
        if period in ['day', 'month']:
            qs = qs.filter(period=period)
        return qs

    def perform_create(self, serializer):
        serializer.save(supplier=self.request.user)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsSupplier])
def supplier_analytics(request):
    period = int(request.query_params.get('period', 30))
    data = get_supplier_analytics(request.user, period)
    return Response(data)


@api_view(['GET'])
<<<<<<< Updated upstream
@permission_classes([IsAuthenticated])
def rep_analytics(request):
    if request.user.role != 'sales_rep':
        return Response({'detail': 'Only sales reps can view their own stats here.'}, status=403)
    period = int(request.query_params.get('period', 30))
    data = get_rep_analytics(request.user, period)
    return Response(data)
=======
@permission_classes([IsAuthenticated, IsSupplier])
def supplier_finance_summary(request):
    period = request.query_params.get('period', 'day')
    include_bonuses = request.query_params.get('include_bonuses', 'true') != 'false'
    selected = request.query_params.get('date')

    try:
        anchor = datetime.strptime(selected, '%Y-%m-%d').date() if selected else timezone.localdate()
    except ValueError:
        anchor = timezone.localdate()

    if period == 'month':
        start = anchor.replace(day=1)
        end = anchor.replace(day=monthrange(anchor.year, anchor.month)[1])
        salary_factor = 1
    else:
        period = 'day'
        start = end = anchor
        salary_factor = 1 / monthrange(anchor.year, anchor.month)[1]

    fulfilled = ProductRequest.objects.filter(
        supplier=request.user,
        status=ProductRequest.Status.FULFILLED,
        updated_at__date__gte=start,
        updated_at__date__lte=end,
    )
    revenue = fulfilled.aggregate(total=Coalesce(Sum('total_price'), 0, output_field=DecimalField()))['total']

    cogs = RequestItem.objects.filter(request__in=fulfilled).aggregate(
        total=Coalesce(Sum(F('quantity') * F('product__cost_price')), 0, output_field=DecimalField())
    )['total']

    workers = request.user.workers.filter(role='sales_rep')
    salary_total = sum(float(w.salary or 0) * salary_factor for w in workers)
    bonus_total = sum(float(w.bonus or 0) * salary_factor for w in workers) if include_bonuses else 0

    manual_expenses = SupplierExpense.objects.filter(
        supplier=request.user,
        date__gte=start,
        date__lte=end,
    )
    if period == 'day':
        manual_expenses = manual_expenses.filter(period='day')
    manual_total = manual_expenses.aggregate(
        total=Coalesce(Sum('amount'), 0, output_field=DecimalField())
    )['total']

    total_expenses = float(cogs) + salary_total + bonus_total + float(manual_total)
    clear_revenue = float(revenue) - total_expenses
    margin = (clear_revenue / float(revenue) * 100) if float(revenue) else 0

    return Response({
        'period': period,
        'start_date': start,
        'end_date': end,
        'include_bonuses': include_bonuses,
        'revenue': float(revenue),
        'cost_of_goods': float(cogs),
        'salary_expenses': salary_total,
        'bonus_expenses': bonus_total,
        'manual_expenses_total': float(manual_total),
        'total_expenses': total_expenses,
        'clear_revenue': clear_revenue,
        'profit_margin': margin,
        'orders_count': fulfilled.count(),
        'manual_expenses': SupplierExpenseSerializer(manual_expenses, many=True).data,
        'workers': [
            {
                'id': worker.id,
                'username': worker.username,
                'salary': float(worker.salary or 0),
                'bonus': float(worker.bonus or 0),
            }
            for worker in workers.order_by('username')
        ],
    })
>>>>>>> Stashed changes
