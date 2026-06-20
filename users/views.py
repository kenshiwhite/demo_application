from rest_framework import generics, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import get_user_model
from .serializers import RegisterSerializer, SupplierSerializer
from .email import send_verification_email

User = get_user_model()

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def perform_create(self, serializer):
        user = serializer.save()
        # send verification email after registration
        try:
            send_verification_email(user)
        except Exception as e:
            print(f'Email send failed: {e}')

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
        try:
            send_verification_email(user)
            return Response({'detail': 'Код отправлен повторно'})
        except Exception as e:
            return Response(
                {'detail': 'Не удалось отправить письмо'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class MeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'role': user.role,
            'company_name': user.company_name,
            'phone': user.phone,
            'is_email_verified': user.is_email_verified,
        })

class SupplierListView(generics.ListAPIView):
    serializer_class = SupplierSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return User.objects.filter(role='supplier')