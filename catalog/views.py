# catalog/views.py
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Q
from users.permissions import IsSupplier, IsSupplierStaff
from .analytics import get_supplier_analytics
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