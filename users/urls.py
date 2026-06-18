from django.urls import path
from .views import RegisterView, SupplierListView


urlpatterns = [
    path('register/', RegisterView.as_view()),
    path('suppliers/', SupplierListView.as_view()),  # ← add this

]