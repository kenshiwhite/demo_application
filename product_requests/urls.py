from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProductRequestViewSet

router = DefaultRouter()
router.register('', ProductRequestViewSet, basename='request')

urlpatterns = [
    path('', include(router.urls)),
]