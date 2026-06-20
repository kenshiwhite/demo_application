from django.urls import path
from .views import RegisterView, SupplierListView, MeView, VerifyEmailView, ResendVerificationView

urlpatterns = [
    path('register/', RegisterView.as_view()),
    path('suppliers/', SupplierListView.as_view()),
    path('me/', MeView.as_view()),
    path('verify-email/', VerifyEmailView.as_view()),
    path('resend-verification/', ResendVerificationView.as_view()),
]