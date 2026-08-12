from django.urls import path
from .views import (
    RegisterView, SupplierListView, SupplierDetailView,
    MeView, ProfileView, ChangePasswordView,
    VerifyEmailView, ResendVerificationView,
    UpdateEmailView, UpdatePushTokenView, DeleteAccountView, DeleteProfilePictureView, get_cities,
    SendPhoneVerificationView, VerifyPhoneView,
    PhoneLoginRequestView, PhoneLoginVerifyView, WorkerListCreateView, WorkerDetailView,
    BusinessClientListCreateView, AssignClientRepView
)

urlpatterns = [
    path('register/', RegisterView.as_view()),
    path('suppliers/', SupplierListView.as_view()),
    path('suppliers/<int:pk>/', SupplierDetailView.as_view()),
    path('me/', MeView.as_view()),
    path('profile/', ProfileView.as_view()),
    path('profile/picture/', DeleteProfilePictureView.as_view()),
    path('account/', DeleteAccountView.as_view()),
    path('change-password/', ChangePasswordView.as_view()),
    path('me/update/', UpdateEmailView.as_view()),
    path('push-token/', UpdatePushTokenView.as_view()),
    path('verify-email/', VerifyEmailView.as_view()),
    path('resend-verification/', ResendVerificationView.as_view()),
    path('send-phone-code/', SendPhoneVerificationView.as_view()),
    path('verify-phone/', VerifyPhoneView.as_view()),
    path('phone-login/request/', PhoneLoginRequestView.as_view()),
    path('phone-login/verify/', PhoneLoginVerifyView.as_view()),
    path('cities/', get_cities),
    path('workers/', WorkerListCreateView.as_view()),
    path('workers/<int:pk>/', WorkerDetailView.as_view()),
    path('business-clients/', BusinessClientListCreateView.as_view()),
    path('clients/<str:client_type>/<int:pk>/assign-rep/', AssignClientRepView.as_view()),
]