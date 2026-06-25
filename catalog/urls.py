from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProductViewSet, supplier_analytics, get_categories

router = DefaultRouter()
router.register('products', ProductViewSet, basename='product')

urlpatterns = [
    path('', include(router.urls)),
    path('analytics/', supplier_analytics),
    path('categories/', get_categories),
]