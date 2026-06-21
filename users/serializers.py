from rest_framework import serializers
from django.contrib.auth import get_user_model

User = get_user_model()

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ['email', 'username', 'password', 'role', 'company_name', 'phone']

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)

class SupplierSerializer(serializers.ModelSerializer):
    product_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'company_name', 'phone', 'product_count']

    def get_product_count(self, obj):
        return obj.products.filter(is_available=True).count()

class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'role',
            'company_name', 'phone',
            'is_email_verified',
            'date_joined',
        ]
        read_only_fields = ['id', 'username', 'role', 'is_email_verified', 'date_joined']

class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, min_length=8)