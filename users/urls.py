from django.urls import path
from .views import RegisterView, SupplierListView, MeView


urlpatterns = [
    path('register/', RegisterView.as_view()),
    path('suppliers/', SupplierListView.as_view()),  # ← add this
    path('me/', MeView.as_view()),
]