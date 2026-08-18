from rest_framework import generics, permissions, status
from decimal import Decimal, InvalidOperation
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models import Q, Count
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import (
    RegisterSerializer, SupplierSerializer,
    ProfileSerializer, ChangePasswordSerializer, BusinessMemberSerializer,
    BusinessClientSerializer, RegisteredClientSerializer
)
from .email import send_verification_email
from .sms import normalize_phone, send_phone_verification_code
from users.models import KAZAKHSTAN_CITIES, BusinessClient
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
@permission_classes([permissions.AllowAny])
def get_cities(request):
    cities = [{'value': v, 'label': l} for v, l in KAZAKHSTAN_CITIES]
    return Response(cities)

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def perform_create(self, serializer):
        user = serializer.save()
        try:
            send_verification_email(user)
        except Exception as exc:
            logger.warning('Failed to send verification email: %s', exc)
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
        try:
            result = send_verification_email(user)
        except Exception:
            return Response(
                {'detail': 'Не удалось отправить письмо. Попробуйте позже.'},
                status=status.HTTP_502_BAD_GATEWAY
            )
        response_data = {'detail': 'Код отправлен на почту'}
        if result.get('debug'):
            # Email delivery isn't configured/working — surface the code
            # directly so development/staging can still proceed. This
            # never happens in production once Postmark is configured.
            response_data['code'] = result['code']
        return Response(response_data)

class MeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = ProfileSerializer(request.user)
        return Response(serializer.data)

class ProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

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


class DeleteProfilePictureView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request):
        user = request.user
        if user.profile_picture:
            user.profile_picture.delete(save=False)
            user.profile_picture = None
            user.save(update_fields=['profile_picture'])
        return Response(ProfileSerializer(user).data)


class DeleteAccountView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request):
        request.user.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

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
    pagination_class = None

    def get_queryset(self):
        qs = User.objects.filter(role='supplier')
        city = self.request.query_params.get('city')
        if city:
            # Match suppliers who list this city in their coverage area.
            # Fall back to the legacy single `city` field for any supplier
            # that hasn't been migrated to service_cities yet.
            qs = qs.filter(
                Q(service_cities__contains=[city]) |
                Q(service_cities=[], city=city)
            )
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
        business = supplier_business(request.user)
        if not business:
            return Response({'detail': 'Supplier staff access required.'}, status=status.HTTP_403_FORBIDDEN)
        workers = business.workers.filter(role=User.Role.SALES_REP).order_by('username')
        city = request.query_params.get('city')
        if city:
            workers = workers.filter(city=city)
        return Response(BusinessMemberSerializer(workers, many=True, context={'request': request}).data)

    def post(self, request):
        if request.user.role != User.Role.SUPPLIER:
            return Response({'detail': 'Only suppliers can create worker accounts.'}, status=status.HTTP_403_FORBIDDEN)
        required = ['name', 'username', 'password', 'phone']
        missing = [field for field in required if not request.data.get(field)]
        if missing:
            return Response({'detail': 'Имя, логин, пароль и телефон обязательны.'}, status=status.HTTP_400_BAD_REQUEST)
        if len(request.data['password']) < 8:
            return Response({'detail': 'Password must be at least 8 characters.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            phone = normalize_phone(request.data['phone'])
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        if User.objects.filter(username=request.data['username']).exists() or User.objects.filter(phone=phone).exists():
            return Response({'detail': 'A user with this username or phone already exists.'}, status=status.HTTP_400_BAD_REQUEST)
        # Which city this rep is assigned to work — must be one of the
        # supplier's own service cities. Falls back to the supplier's
        # primary city for suppliers who haven't set up multi-city coverage.
        city = request.data.get('city') or request.user.city
        if request.user.service_cities and city not in request.user.service_cities:
            return Response({'detail': 'Этот город не входит в список городов обслуживания.'}, status=status.HTTP_400_BAD_REQUEST)
        raw_salary = request.data.get('base_salary')
        try:
            base_salary = Decimal(str(raw_salary)) if raw_salary not in (None, '') else None
        except InvalidOperation:
            return Response({'detail': 'Некорректный оклад.'}, status=status.HTTP_400_BAD_REQUEST)
        worker = User.objects.create_user(
            username=request.data['username'], password=request.data['password'],
            first_name=request.data['name'].strip(),
            email=request.data.get('email', ''), phone=phone, role=User.Role.SALES_REP,
            company_name=request.user.company_name, city=city, base_salary=base_salary,
            business_supplier=request.user
            # is_phone_verified intentionally left at its default (False) —
            # the worker verifies their own phone the first time they log
            # in, same flow every other account goes through. The supplier
            # setting up this account doesn't have the worker's phone in
            # hand to receive that code.
        )
        return Response(BusinessMemberSerializer(worker, context={'request': request}).data, status=status.HTTP_201_CREATED)


class WorkerDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, pk):
        if request.user.role != User.Role.SUPPLIER:
            return Response({'detail': 'Only suppliers can update worker pay.'}, status=status.HTTP_403_FORBIDDEN)
        try:
            worker = User.objects.get(id=pk, role=User.Role.SALES_REP, business_supplier=request.user)
        except User.DoesNotExist:
            return Response({'detail': 'Сотрудник не найден.'}, status=status.HTTP_404_NOT_FOUND)

        update_fields = []

        if 'name' in request.data and request.data['name']:
            worker.first_name = request.data['name'].strip()
            update_fields.append('first_name')

        for field in ('base_salary', 'bonus_sales_threshold', 'bonus_percent'):
            if field not in request.data:
                continue
            raw = request.data[field]
            if raw in ('', None):
                setattr(worker, field, None)
            else:
                try:
                    setattr(worker, field, Decimal(str(raw)))
                except (InvalidOperation, ValueError):
                    return Response({'detail': f'Некорректное значение для поля {field}.'}, status=status.HTTP_400_BAD_REQUEST)
            update_fields.append(field)

        if update_fields:
            worker.save(update_fields=update_fields)
        return Response(BusinessMemberSerializer(worker, context={'request': request}).data)


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

        # A rep assigned to one city only ever works that city's clients;
        # ?city= lets a supplier (or an unassigned rep) narrow the list too.
        city = request.query_params.get('city')
        if request.user.role == User.Role.SALES_REP and request.user.city:
            city = request.user.city

        # CRM contacts a supplier/rep entered manually.
        crm_clients = BusinessClient.objects.filter(supplier=business).select_related('sales_rep').annotate(request_count=Count('requests')).order_by('name')
        if request.user.role == User.Role.SALES_REP:
            crm_clients = crm_clients.filter(sales_rep=request.user)
        if city:
            crm_clients = crm_clients.filter(city=city)
        crm_data = BusinessClientSerializer(crm_clients, many=True).data
        for row in crm_data:
            row['client_type'] = 'business'

        # Real clients who registered and ordered directly, with no CRM
        # entry needed — they're "saved" here automatically the moment
        # they place their first request with this business.
        registered_ids = User.objects.filter(
            role=User.Role.CLIENT, requests__supplier=business
        ).values_list('id', flat=True).distinct()
        registered_clients = User.objects.filter(id__in=registered_ids).select_related('assigned_sales_rep').annotate(
            request_count=Count('requests', filter=Q(requests__supplier=business))
        ).order_by('username')
        if request.user.role == User.Role.SALES_REP:
            registered_clients = registered_clients.filter(
                Q(assigned_sales_rep=request.user) | Q(assigned_sales_rep__isnull=True)
            )
        if city:
            registered_clients = registered_clients.filter(city=city)
        registered_data = RegisteredClientSerializer(
            registered_clients, many=True, context={'request': request}
        ).data
        for row in registered_data:
            row['client_type'] = 'registered'

        return Response(list(crm_data) + list(registered_data))

    def post(self, request):
        business = self._business(request)
        if not business:
            return Response({'detail': 'Supplier staff access required.'}, status=status.HTTP_403_FORBIDDEN)
        required = ['name', 'address']
        missing = [field for field in required if not request.data.get(field)]
        if missing:
            return Response({'detail': 'Client name and address are required.'}, status=status.HTTP_400_BAD_REQUEST)
        # A rep assigned to one city can only add clients in that city;
        # otherwise city must be given and be one the business services.
        city = request.data.get('city')
        if request.user.role == User.Role.SALES_REP and request.user.city:
            city = request.user.city
        if not city:
            return Response({'detail': 'City is required.'}, status=status.HTTP_400_BAD_REQUEST)
        if business.service_cities and city not in business.service_cities:
            return Response({'detail': 'Этот город не входит в список городов обслуживания.'}, status=status.HTTP_400_BAD_REQUEST)
        client = BusinessClient.objects.create(
            supplier=business, sales_rep=(request.user if request.user.role == User.Role.SALES_REP else None),
            name=request.data['name'].strip(), company_name=request.data.get('company_name', '').strip(),
            phone=request.data.get('phone', '').strip(), email=request.data.get('email', '').strip(),
            address=request.data['address'].strip(), latitude=request.data.get('latitude') or None,
            longitude=request.data.get('longitude') or None, notes=request.data.get('notes', '').strip(),
            city=city,
        )
        return Response(BusinessClientSerializer(client).data, status=status.HTTP_201_CREATED)


class AssignClientRepView(APIView):
    """Reassign (or clear) which sales rep is responsible for a client —
    either a CRM contact (BusinessClient) or a real registered client
    (User.assigned_sales_rep). A supplier can reassign anyone; a sales rep
    can only hand off a client that's currently theirs (or unclaimed)."""
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, client_type, pk):
        business = supplier_business(request.user)
        if not business:
            return Response({'detail': 'Supplier staff access required.'}, status=status.HTTP_403_FORBIDDEN)

        rep_id = request.data.get('sales_rep_id')
        worker = None
        if rep_id:
            try:
                worker = User.objects.get(id=rep_id, role=User.Role.SALES_REP, business_supplier=business)
            except (User.DoesNotExist, ValueError, TypeError):
                return Response({'detail': 'Выберите корректного сотрудника из вашей компании.'}, status=status.HTTP_400_BAD_REQUEST)

        if client_type == 'business':
            try:
                contact = BusinessClient.objects.get(id=pk, supplier=business)
            except BusinessClient.DoesNotExist:
                return Response({'detail': 'Клиент не найден.'}, status=status.HTTP_404_NOT_FOUND)
            if request.user.role == User.Role.SALES_REP and contact.sales_rep_id not in (None, request.user.id):
                return Response({'detail': 'Этот клиент закреплён за другим сотрудником.'}, status=status.HTTP_403_FORBIDDEN)
            contact.sales_rep = worker
            contact.save(update_fields=['sales_rep'])
            return Response(BusinessClientSerializer(contact).data)

        elif client_type == 'registered':
            try:
                registered = User.objects.get(id=pk, role=User.Role.CLIENT)
            except User.DoesNotExist:
                return Response({'detail': 'Клиент не найден.'}, status=status.HTTP_404_NOT_FOUND)
            if not registered.requests.filter(supplier=business).exists():
                return Response({'detail': 'Клиент не найден.'}, status=status.HTTP_404_NOT_FOUND)
            if request.user.role == User.Role.SALES_REP and registered.assigned_sales_rep_id not in (None, request.user.id):
                return Response({'detail': 'Этот клиент закреплён за другим сотрудником.'}, status=status.HTTP_403_FORBIDDEN)
            registered.assigned_sales_rep = worker
            registered.save(update_fields=['assigned_sales_rep'])
            return Response(RegisteredClientSerializer(registered, context={'request': request}).data)

        return Response({'detail': 'Unknown client type.'}, status=status.HTTP_400_BAD_REQUEST)