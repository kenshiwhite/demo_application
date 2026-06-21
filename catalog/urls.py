from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CategoryViewSet, ProductViewSet, supplier_analytics

router = DefaultRouter()
router.register('categories', CategoryViewSet)
router.register('products', ProductViewSet, basename='product')

urlpatterns = [
    path('', include(router.urls)),
    path('analytics/', supplier_analytics),
]