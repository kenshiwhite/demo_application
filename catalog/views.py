from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from users.permissions import IsSupplier
from .analytics import get_supplier_analytics
from rest_framework import viewsets, permissions
from .models import Product, CATEGORY_CHOICES
from .serializers import ProductSerializer
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
    filterset_fields = ['category', 'is_available', 'supplier']
    search_fields = ['name', 'description']
    ordering_fields = ['price', 'created_at', 'stock_quantity']

    def get_queryset(self):
        user = self.request.user
        if user.role == 'supplier':
            return Product.objects.filter(supplier=user)

        qs = Product.objects.filter(is_available=True)
        city = self.request.query_params.get('city')
        if city:
            qs = qs.filter(supplier__city=city)
        return qs

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated(), IsSupplier()]
        return [permissions.IsAuthenticated()]

    def perform_create(self, serializer):
        if not self.request.user.is_phone_verified:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('Verify your phone number before adding products')
        serializer.save(supplier=self.request.user)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsSupplier])
def supplier_analytics(request):
    period = int(request.query_params.get('period', 30))
    data = get_supplier_analytics(request.user, period)
    return Response(data)
