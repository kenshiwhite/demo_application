from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models import Q, Count
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import (
    RegisterSerializer, SupplierSerializer,
    ProfileSerializer, ChangePasswordSerializer, BusinessMemberSerializer
)
from .email import send_verification_email
from .sms import normalize_phone, send_phone_verification_code
from users.models import KAZAKHSTAN_CITIES
import threading
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


def verify_phone_code(user, code, allow_already_verified=False):
    if user.is_phone_verified and allow_already_verified:
        return None
    if not code:
        return 'Enter the verification code'
    if user.phone_verification_attempts >= 5:
        return 'Too many attempts. Request a new code.'
    if not user.phone_verification_code:
        return 'Request a new verification code'
    if (
        user.phone_verification_expires_at and
        user.phone_verification_expires_at < timezone.now()
    ):
        return 'Verification code expired'
    if user.phone_verification_code != code:
        user.phone_verification_attempts += 1
        user.save(update_fields=['phone_verification_attempts'])
        return 'Invalid verification code'

    user.is_phone_verified = True
    user.phone_verification_code = ''
    user.phone_verification_expires_at = None
    user.phone_verification_attempts = 0
    user.save(update_fields=[
        'is_phone_verified',
        'phone_verification_code',
        'phone_verification_expires_at',
        'phone_verification_attempts',
    ])
    return None

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_cities(request):
    cities = [{'value': v, 'label': l} for v, l in KAZAKHSTAN_CITIES]
    return Response(cities)

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def perform_create(self, serializer):
        user = serializer.save()
        user.generate_verification_code()
        try:
            send_phone_verification_code(user)
        except Exception as exc:
            logger.warning('Failed to send phone verification code: %s', exc)


class SendPhoneVerificationView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        if not user.phone:
            return Response(
                {'detail': 'Phone number is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if user.is_phone_verified:
            return Response({'detail': 'Phone number is already verified'})

        try:
            result = send_phone_verification_code(user)
        except Exception:
            logger.exception('Failed to send phone verification code')
            return Response(
                {'detail': 'Failed to send SMS code'},
                status=status.HTTP_502_BAD_GATEWAY
            )

        data = {'detail': 'Verification code sent'}
        if result.get('code'):
            data['code'] = result['code']
        return Response(data)


class VerifyPhoneView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        error = verify_phone_code(
            request.user,
            request.data.get('code'),
            allow_already_verified=True
        )
        if error:
            return Response({'detail': error}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'detail': 'Phone number verified'})


class PhoneLoginRequestView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        try:
            phone = normalize_phone(request.data.get('phone', ''))
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(phone=phone)
        except User.DoesNotExist:
            return Response(
                {'detail': 'No account found for this phone number'},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            result = send_phone_verification_code(user)
        except Exception:
            logger.exception('Failed to send phone login code')
            return Response(
                {'detail': 'Failed to send SMS code'},
                status=status.HTTP_502_BAD_GATEWAY
            )

        data = {'detail': 'Login code sent'}
        if result.get('code'):
            data['code'] = result['code']
        return Response(data)


class PhoneLoginVerifyView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        try:
            phone = normalize_phone(request.data.get('phone', ''))
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(phone=phone)
        except User.DoesNotExist:
            return Response(
                {'detail': 'No account found for this phone number'},
                status=status.HTTP_404_NOT_FOUND
            )

        error = verify_phone_code(user, request.data.get('code'))
        if error:
            return Response({'detail': error}, status=status.HTTP_400_BAD_REQUEST)

        refresh = RefreshToken.for_user(user)
        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': ProfileSerializer(user).data,
        })

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
        return Response({'detail': 'Код сгенерирован', 'code': code})

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
            request.user, data=request.data, partial=True
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

class UpdatePushTokenView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        token = request.data.get('expo_push_token')
        if not token:
            return Response(
                {'detail': 'Token required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        request.user.expo_push_token = token
        request.user.save()
        return Response({'detail': 'Token saved'})

class SupplierListView(generics.ListAPIView):
    serializer_class = SupplierSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = User.objects.filter(role='supplier')
        city = self.request.query_params.get('city')
        if city:
            qs = qs.filter(city=city)
        return qs

class SupplierDetailView(generics.RetrieveAPIView):
    serializer_class = SupplierSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return User.objects.filter(role='supplier')


def supplier_business(user):
    return user if user.role == User.Role.SUPPLIER else user.business_supplier


class WorkerListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if request.user.role != User.Role.SUPPLIER:
            return Response({'detail': 'Only suppliers can view workers.'}, status=status.HTTP_403_FORBIDDEN)
        workers = request.user.workers.filter(role=User.Role.SALES_REP).order_by('username')
        return Response(BusinessMemberSerializer(workers, many=True).data)

    def post(self, request):
        if request.user.role != User.Role.SUPPLIER:
            return Response({'detail': 'Only suppliers can create worker accounts.'}, status=status.HTTP_403_FORBIDDEN)
        required = ['username', 'password', 'phone']
        missing = [field for field in required if not request.data.get(field)]
        if missing:
            return Response({'detail': 'Username, password and phone are required.'}, status=status.HTTP_400_BAD_REQUEST)
        if len(request.data['password']) < 8:
            return Response({'detail': 'Password must be at least 8 characters.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            phone = normalize_phone(request.data['phone'])
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        if User.objects.filter(username=request.data['username']).exists() or User.objects.filter(phone=phone).exists():
            return Response({'detail': 'A user with this username or phone already exists.'}, status=status.HTTP_400_BAD_REQUEST)
        worker = User.objects.create_user(
            username=request.data['username'], password=request.data['password'],
            email=request.data.get('email', ''), phone=phone, role=User.Role.SALES_REP,
            company_name=request.user.company_name, city=request.user.city,
            business_supplier=request.user, is_phone_verified=True
        )
        return Response(BusinessMemberSerializer(worker).data, status=status.HTTP_201_CREATED)


class BusinessClientListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def _business(self, request):
        business = supplier_business(request.user)
        if not business:
            return None
        return business

    def get(self, request):
        business = self._business(request)
        if not business:
            return Response({'detail': 'Supplier staff access required.'}, status=status.HTTP_403_FORBIDDEN)
        clients = User.objects.filter(role=User.Role.CLIENT).filter(
            Q(assigned_sales_rep__business_supplier=business) |
            Q(requests__supplier=business)
        ).distinct().annotate(request_count=Count('requests', filter=Q(requests__supplier=business))).order_by('username')
        if request.user.role == User.Role.SALES_REP:
            clients = clients.filter(
                Q(assigned_sales_rep=request.user) |
                Q(requests__sales_rep=request.user)
            ).distinct()
        return Response(BusinessMemberSerializer(clients, many=True).data)

    def post(self, request):
        business = self._business(request)
        if not business:
            return Response({'detail': 'Supplier staff access required.'}, status=status.HTTP_403_FORBIDDEN)
        required = ['username', 'password', 'phone']
        missing = [field for field in required if not request.data.get(field)]
        if missing:
            return Response({'detail': 'Name, password and phone are required.'}, status=status.HTTP_400_BAD_REQUEST)
        if len(request.data['password']) < 8:
            return Response({'detail': 'Password must be at least 8 characters.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            phone = normalize_phone(request.data['phone'])
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        if User.objects.filter(username=request.data['username']).exists() or User.objects.filter(phone=phone).exists():
            return Response({'detail': 'A client with this username or phone already exists.'}, status=status.HTTP_400_BAD_REQUEST)
        client = User.objects.create_user(
            username=request.data['username'], password=request.data['password'],
            email=request.data.get('email', ''), phone=phone, role=User.Role.CLIENT,
            company_name=request.data.get('company_name', ''), description=request.data.get('description', ''),
            city=business.city, assigned_sales_rep=(request.user if request.user.role == User.Role.SALES_REP else None),
            is_phone_verified=True
        )
        return Response(BusinessMemberSerializer(client).data, status=status.HTTP_201_CREATED)
