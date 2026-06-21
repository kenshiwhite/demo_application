from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from .serializers import (
    RegisterSerializer, SupplierSerializer,
    ProfileSerializer, ChangePasswordSerializer
)
from .email import send_verification_email
import threading

User = get_user_model()

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def perform_create(self, serializer):
        user = serializer.save()
        user.generate_verification_code()

class VerifyEmailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        code = request.data.get('code')
        if not code:
            return Response(
                {'detail': 'Введите код подтверждения'},
                status=status.HTTP_400_BAD_REQUEST
            )
        user = request.user
        if user.is_email_verified:
            return Response({'detail': 'Email уже подтверждён'})
        if user.email_verification_code != code:
            return Response(
                {'detail': 'Неверный код. Попробуйте снова.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        user.is_email_verified = True
        user.email_verification_code = ''
        user.save()
        return Response({'detail': 'Email успешно подтверждён!'})

class ResendVerificationView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        if user.is_email_verified:
            return Response({'detail': 'Email уже подтверждён'})
        code = user.generate_verification_code()
        return Response({
            'detail': 'Код сгенерирован',
            'code': code
        })

class MeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = ProfileSerializer(request.user)
        return Response(serializer.data)

class ProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = ProfileSerializer(request.user)
        return Response(serializer.data)

    def patch(self, request):
        serializer = ProfileSerializer(
            request.user,
            data=request.data,
            partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ChangePasswordView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        if serializer.is_valid():
            user = request.user
            if not user.check_password(serializer.validated_data['old_password']):
                return Response(
                    {'detail': 'Неверный текущий пароль'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            return Response({'detail': 'Пароль успешно изменён'})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UpdateEmailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request):
        email = request.data.get('email')
        if not email:
            return Response(
                {'detail': 'Введите email'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if User.objects.filter(email=email).exclude(id=request.user.id).exists():
            return Response(
                {'detail': 'Этот email уже используется'},
                status=status.HTTP_400_BAD_REQUEST
            )
        request.user.email = email
        request.user.is_email_verified = False
        request.user.save()
        return Response({'detail': 'Email обновлён'})

class SupplierListView(generics.ListAPIView):
    serializer_class = SupplierSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return User.objects.filter(role='supplier')

class SupplierDetailView(generics.RetrieveAPIView):
    serializer_class = SupplierSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return User.objects.filter(role='supplier')