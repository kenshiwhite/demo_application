# users/serializers.py
from decimal import Decimal
from django.db.models import Sum
from rest_framework import serializers
from django.contrib.auth import get_user_model
from users.models import KAZAKHSTAN_CITIES, BusinessClient, validate_city_codes
from .sms import normalize_phone

User = get_user_model()

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    phone = serializers.CharField(required=True, allow_blank=False)
    service_cities = serializers.ListField(
        child=serializers.CharField(), required=False, allow_empty=True
    )

    class Meta:
        model = User
        fields = [
            'email', 'username', 'password',
            'role', 'company_name', 'phone', 'city', 'service_cities'
        ]

    def create(self, validated_data):
        validated_data['phone'] = normalize_phone(validated_data['phone'])
        return User.objects.create_user(**validated_data)

    def validate_phone(self, value):
        phone = normalize_phone(value)
        if User.objects.filter(phone=phone).exists():
            raise serializers.ValidationError('This phone number is already registered.')
        return phone

    def validate_service_cities(self, value):
        if value and self.initial_data.get('role') != 'supplier':
            raise serializers.ValidationError('Only suppliers can set covered cities.')
        try:
            validate_city_codes(value)
        except Exception as exc:
            raise serializers.ValidationError(str(exc))
        # de-duplicate while preserving order
        return list(dict.fromkeys(value))

class SupplierSerializer(serializers.ModelSerializer):
    product_count = serializers.SerializerMethodField()
    city_display = serializers.SerializerMethodField()
    service_cities_display = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'username', 'company_name',
            'phone', 'description', 'product_count',
            'city', 'city_display', 'profile_picture',
            'service_cities', 'service_cities_display'
        ]

    def get_product_count(self, obj):
        return obj.products.filter(is_available=True).count()

    def get_city_display(self, obj):
        return dict(KAZAKHSTAN_CITIES).get(obj.city, obj.city)

    def get_service_cities_display(self, obj):
        labels = dict(KAZAKHSTAN_CITIES)
        return [labels.get(code, code) for code in obj.service_cities]

class ProfileSerializer(serializers.ModelSerializer):
    city_display = serializers.SerializerMethodField()
    service_cities_display = serializers.SerializerMethodField()
    business_supplier_name = serializers.CharField(source='business_supplier.company_name', read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'role',
            'company_name', 'phone', 'description',
            'profile_picture',
            'is_email_verified', 'is_phone_verified', 'date_joined',
            'city', 'city_display', 'service_cities', 'service_cities_display',
            'business_supplier', 'business_supplier_name',
            'assigned_sales_rep', 'low_stock_threshold'
        ]
        read_only_fields = [
            'id', 'username', 'role',
            'is_email_verified', 'is_phone_verified', 'date_joined',
            'business_supplier', 'assigned_sales_rep'
        ]

    def to_representation(self, instance):
        # A sales rep should see their supplier's configured threshold, not
        # their own account's default — the setting belongs to the business,
        # only the supplier can change it, but the whole team should use it.
        data = super().to_representation(instance)
        if instance.role == 'sales_rep' and instance.business_supplier_id:
            data['low_stock_threshold'] = instance.business_supplier.low_stock_threshold
        return data

    def validate_phone(self, value):
        phone = normalize_phone(value)
        if User.objects.filter(phone=phone).exclude(id=self.instance.id).exists():
            raise serializers.ValidationError('This phone number is already registered.')
        return phone

    def validate_service_cities(self, value):
        if value and self.instance.role != 'supplier':
            raise serializers.ValidationError('Only suppliers can set covered cities.')
        try:
            validate_city_codes(value)
        except Exception as exc:
            raise serializers.ValidationError(str(exc))
        return list(dict.fromkeys(value))

    def update(self, instance, validated_data):
        if 'phone' in validated_data and validated_data['phone'] != instance.phone:
            validated_data['is_phone_verified'] = False
            validated_data['phone_verification_code'] = ''
            validated_data['phone_verification_expires_at'] = None
            validated_data['phone_verification_attempts'] = 0
        return super().update(instance, validated_data)

    def get_city_display(self, obj):
        return dict(KAZAKHSTAN_CITIES).get(obj.city, obj.city)

    def get_service_cities_display(self, obj):
        labels = dict(KAZAKHSTAN_CITIES)
        return [labels.get(code, code) for code in obj.service_cities]

class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, min_length=8)


class BusinessMemberSerializer(serializers.ModelSerializer):
    assigned_sales_rep_name = serializers.CharField(
        source='assigned_sales_rep.username', read_only=True
    )
    request_count = serializers.IntegerField(read_only=True, required=False)
    city_display = serializers.SerializerMethodField()
    base_salary = serializers.SerializerMethodField()
    bonus_sales_threshold = serializers.SerializerMethodField()
    bonus_percent = serializers.SerializerMethodField()
    current_month_sales = serializers.SerializerMethodField()
    bonus_progress_percent = serializers.SerializerMethodField()
    bonus_earned = serializers.SerializerMethodField()
    bonus_amount = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'phone', 'company_name', 'description',
            'profile_picture',
            'city', 'city_display', 'date_joined', 'assigned_sales_rep', 'assigned_sales_rep_name',
            'request_count', 'base_salary',
            'bonus_sales_threshold', 'bonus_percent', 'current_month_sales',
            'bonus_progress_percent', 'bonus_earned', 'bonus_amount',
        ]
        read_only_fields = fields

    def get_city_display(self, obj):
        return dict(KAZAKHSTAN_CITIES).get(obj.city, obj.city)

    def _is_owner(self, obj):
        # Salary/bonus data is only visible to the supplier who owns this
        # worker — a rep listing colleagues (e.g. the reassignment picker)
        # must never see anyone's pay or sales-toward-bonus progress.
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        return bool(
            user and user.is_authenticated and user.role == 'supplier'
            and obj.business_supplier_id == user.id
        )

    def get_base_salary(self, obj):
        if self._is_owner(obj):
            return str(obj.base_salary) if obj.base_salary is not None else None
        return None

    def get_bonus_sales_threshold(self, obj):
        if self._is_owner(obj):
            return str(obj.bonus_sales_threshold) if obj.bonus_sales_threshold is not None else None
        return None

    def get_bonus_percent(self, obj):
        if self._is_owner(obj):
            return str(obj.bonus_percent) if obj.bonus_percent is not None else None
        return None

    def _current_month_sales(self, obj):
        # Lazy import — product_requests imports users.models, so importing
        # product_requests.models at module load time here would risk a
        # circular import depending on app-loading order.
        from django.utils import timezone
        from product_requests.models import ProductRequest
        now = timezone.localtime()
        total = ProductRequest.objects.filter(
            sales_rep=obj, status='fulfilled',
            updated_at__year=now.year, updated_at__month=now.month,
        ).aggregate(total=Sum('total_price'))['total']
        return total or Decimal('0')

    def get_current_month_sales(self, obj):
        if self._is_owner(obj):
            return str(self._current_month_sales(obj))
        return None

    def get_bonus_progress_percent(self, obj):
        if not self._is_owner(obj) or not obj.bonus_sales_threshold:
            return None
        sales = self._current_month_sales(obj)
        return round(min(float(sales / obj.bonus_sales_threshold) * 100, 100), 1)

    def get_bonus_earned(self, obj):
        if not self._is_owner(obj) or not obj.bonus_sales_threshold:
            return False
        return self._current_month_sales(obj) >= obj.bonus_sales_threshold

    def get_bonus_amount(self, obj):
        if not self.get_bonus_earned(obj) or not obj.base_salary or not obj.bonus_percent:
            return None
        return str(round(obj.base_salary * obj.bonus_percent / 100, 2))


class BusinessClientSerializer(serializers.ModelSerializer):
    sales_rep_name = serializers.CharField(source='sales_rep.username', read_only=True)
    request_count = serializers.IntegerField(read_only=True, required=False)
    city_display = serializers.SerializerMethodField()

    class Meta:
        model = BusinessClient
        fields = ['id', 'name', 'company_name', 'phone', 'email', 'address',
                  'latitude', 'longitude', 'notes', 'city', 'city_display',
                  'sales_rep', 'sales_rep_name',
                  'request_count', 'created_at']
        read_only_fields = ['id', 'sales_rep', 'sales_rep_name', 'request_count', 'created_at']

    def get_city_display(self, obj):
        return dict(KAZAKHSTAN_CITIES).get(obj.city, obj.city)


class RegisteredClientSerializer(serializers.ModelSerializer):
    """Represents a real (self-registered) client User inside the same
    "clients" list a supplier sees for their CRM (BusinessClient) contacts.
    Read-only: these are real accounts, not something a supplier edits."""
    name = serializers.CharField(source='username', read_only=True)
    address = serializers.SerializerMethodField()
    sales_rep = serializers.IntegerField(source='assigned_sales_rep_id', read_only=True)
    sales_rep_name = serializers.CharField(source='assigned_sales_rep.username', read_only=True)
    city_display = serializers.SerializerMethodField()
    request_count = serializers.IntegerField(read_only=True, required=False)

    class Meta:
        model = User
        fields = [
            'id', 'name', 'username', 'company_name', 'phone', 'email', 'address',
            'city', 'city_display', 'profile_picture',
            'is_phone_verified', 'is_email_verified', 'date_joined',
            'sales_rep', 'sales_rep_name', 'request_count',
        ]

    def get_address(self, obj):
        last_request = obj.requests.order_by('-created_at').first()
        return last_request.delivery_address if last_request else ''

    def get_city_display(self, obj):
        return dict(KAZAKHSTAN_CITIES).get(obj.city, obj.city)