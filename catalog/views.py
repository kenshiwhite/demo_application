from rest_framework import viewsets, permissions
from .models import Category, Product
from .serializers import CategorySerializer, ProductSerializer
from users.permissions import IsSupplier

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticated]

class ProductViewSet(viewsets.ModelViewSet):
    serializer_class = ProductSerializer

    def get_queryset(self):
        user = self.request.user
        # suppliers only see their own products
        # clients see all available products
        if user.role == 'supplier':
            return Product.objects.filter(supplier=user)
        return Product.objects.filter(is_available=True)

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated(), IsSupplier()]
        return [permissions.IsAuthenticated()]

    def perform_create(self, serializer):
        # automatically assign the logged-in supplier as the owner
        serializer.save(supplier=self.request.user)