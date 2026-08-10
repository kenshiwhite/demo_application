from django.urls import path, include
from rest_framework.routers import DefaultRouter
<<<<<<< Updated upstream
from .views import ProductViewSet, supplier_analytics, rep_analytics, get_categories
=======
from .views import (
    ProductViewSet, SupplierExpenseViewSet,
    supplier_analytics, supplier_finance_summary, get_categories
)
>>>>>>> Stashed changes

router = DefaultRouter()
router.register('products', ProductViewSet, basename='product')
router.register('expenses', SupplierExpenseViewSet, basename='supplier-expense')

urlpatterns = [
    path('', include(router.urls)),
    path('analytics/', supplier_analytics),
<<<<<<< Updated upstream
    path('rep-analytics/', rep_analytics),
=======
    path('finance-summary/', supplier_finance_summary),
>>>>>>> Stashed changes
    path('categories/', get_categories),
]
