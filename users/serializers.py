# users/serializers.py
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
            'assigned_sales_rep'
        ]
        read_only_fields = [
            'id', 'username', 'role',
            'is_email_verified', 'is_phone_verified', 'date_joined',
            'business_supplier', 'assigned_sales_rep'
        ]

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

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'phone', 'company_name', 'description',
            'city', 'date_joined', 'assigned_sales_rep', 'assigned_sales_rep_name',
            'request_count'
        ]
        read_only_fields = fields


class BusinessClientSerializer(serializers.ModelSerializer):
    sales_rep_name = serializers.CharField(source='sales_rep.username', read_only=True)
    request_count = serializers.IntegerField(read_only=True, required=False)

    class Meta:
        model = BusinessClient
        fields = ['id', 'name', 'company_name', 'phone', 'email', 'address',
                  'latitude', 'longitude', 'notes', 'sales_rep', 'sales_rep_name',
                  'request_count', 'created_at']
        read_only_fields = ['id', 'sales_rep', 'sales_rep_name', 'request_count', 'created_at']