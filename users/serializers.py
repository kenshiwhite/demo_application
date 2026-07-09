from rest_framework import serializers
from django.contrib.auth import get_user_model
from users.models import KAZAKHSTAN_CITIES

User = get_user_model()

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = [
            'email', 'username', 'password',
            'role', 'company_name', 'phone', 'city'
        ]

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)

class SupplierSerializer(serializers.ModelSerializer):
    product_count = serializers.SerializerMethodField()
    city_display = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'username', 'company_name',
            'phone', 'description', 'product_count',
            'city', 'city_display'
        ]

    def get_product_count(self, obj):
        return obj.products.filter(is_available=True).count()

    def get_city_display(self, obj):
        return dict(KAZAKHSTAN_CITIES).get(obj.city, obj.city)

class ProfileSerializer(serializers.ModelSerializer):
    city_display = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'role',
            'company_name', 'phone', 'description',
            'is_email_verified', 'date_joined',
            'city', 'city_display'
        ]
        read_only_fields = [
            'id', 'username', 'role',
            'is_email_verified', 'date_joined'
        ]

    def get_city_display(self, obj):
        return dict(KAZAKHSTAN_CITIES).get(obj.city, obj.city)

class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, min_length=8)