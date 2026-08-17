# catalog/views.py
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Q
from users.permissions import IsSupplier, IsSupplierStaff
from .analytics import get_supplier_analytics, get_rep_analytics
from rest_framework import viewsets, permissions
from .models import Product, CATEGORY_CHOICES
from .serializers import ProductSerializer
from .filters import ProductFilter
from users.permissions import IsSupplier
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
    # Every screen that fetches this list does client-side aggregation
    # (stock alerts, calendar marking, per-client stats) assuming it has
    # the complete set — same as every other list endpoint in this app
    # (workers, clients, expenses, bonuses). Paginating just this one
    # silently truncated suppliers with >20 products.
    pagination_class = None

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


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsSupplier])
def supplier_analytics(request):
    period = int(request.query_params.get('period', 30))
    data = get_supplier_analytics(request.user, period)
    return Response(data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def rep_analytics(request):
    if request.user.role != 'sales_rep':
        return Response({'detail': 'Only sales reps can view their own stats here.'}, status=403)
    period = int(request.query_params.get('period', 30))
    data = get_rep_analytics(request.user, period)

    # Bonus progress is always measured against the current calendar
    # month (matching the bonus rule itself), independent of whatever
    # `period` window the rest of this response uses.
    rep = request.user
    data['bonus_sales_threshold'] = str(rep.bonus_sales_threshold) if rep.bonus_sales_threshold is not None else None
    data['bonus_percent'] = str(rep.bonus_percent) if rep.bonus_percent is not None else None
    if rep.bonus_sales_threshold:
        from django.utils import timezone
        from django.db.models import Sum
        from product_requests.models import ProductRequest
        now = timezone.localtime()
        month_sales = ProductRequest.objects.filter(
            sales_rep=rep, status='fulfilled',
            updated_at__year=now.year, updated_at__month=now.month,
        ).aggregate(total=Sum('total_price'))['total'] or 0
        data['current_month_sales'] = str(month_sales)
        data['bonus_progress_percent'] = round(min(float(month_sales / rep.bonus_sales_threshold) * 100, 100), 1)
        data['bonus_earned'] = month_sales >= rep.bonus_sales_threshold
        data['bonus_amount'] = (
            str(round(rep.base_salary * rep.bonus_percent / 100, 2))
            if data['bonus_earned'] and rep.base_salary and rep.bonus_percent else None
        )
    else:
        data['current_month_sales'] = None
        data['bonus_progress_percent'] = None
        data['bonus_earned'] = False
        data['bonus_amount'] = None

    return Response(data)