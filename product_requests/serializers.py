# product_requests/serializers.py
from rest_framework import serializers
from .models import ProductRequest, RequestItem, SupplierResponse, RequestPhotoReport

class RequestItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_image = serializers.ImageField(source='product.image', read_only=True)
    product_unit = serializers.CharField(source='product.unit', read_only=True)

    class Meta:
        model = RequestItem
        fields = [
            'id', 'product', 'product_name',
            'product_image', 'product_unit',
            'quantity', 'price_at_request', 'total'
        ]

class SupplierResponseSerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(
        source='supplier.company_name',
        read_only=True
    )
    supplier_profile_picture = serializers.ImageField(
        source='supplier.profile_picture',
        read_only=True
    )

    class Meta:
        model = SupplierResponse
        fields = [
            'id', 'message', 'offered_price',
            'supplier', 'supplier_name', 'supplier_profile_picture', 'created_at'
        ]
        read_only_fields = ['supplier', 'created_at']

class RequestPhotoReportSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.CharField(source='uploaded_by.username', read_only=True)

    class Meta:
        model = RequestPhotoReport
        fields = ['id', 'request', 'image', 'caption', 'uploaded_by', 'uploaded_by_name', 'created_at']
        read_only_fields = ['request', 'uploaded_by', 'created_at']

class ProductRequestSerializer(serializers.ModelSerializer):
    client_name = serializers.SerializerMethodField()
    client_phone = serializers.SerializerMethodField()
    client_company = serializers.SerializerMethodField()
    client_profile_picture = serializers.SerializerMethodField()
    supplier_name = serializers.CharField(source='supplier.company_name', read_only=True)
    supplier_profile_picture = serializers.ImageField(source='supplier.profile_picture', read_only=True)
    sales_rep_name = serializers.CharField(source='sales_rep.username', read_only=True)
    items = RequestItemSerializer(many=True, read_only=True)
    response = SupplierResponseSerializer(read_only=True)
    photo_reports = RequestPhotoReportSerializer(many=True, read_only=True)

    def get_client_name(self, obj):
        return obj.client.username if obj.client else obj.business_client.name

    def get_client_phone(self, obj):
        return obj.client.phone if obj.client else obj.business_client.phone

    def get_client_company(self, obj):
        return obj.client.company_name if obj.client else obj.business_client.company_name

    def get_client_profile_picture(self, obj):
        # Only real User accounts (obj.client) have a profile picture;
        # a business_client is a CRM contact with no login/account.
        if not (obj.client and obj.client.profile_picture):
            return None
        request = self.context.get('request')
        url = obj.client.profile_picture.url
        return request.build_absolute_uri(url) if request else url

    class Meta:
        model = ProductRequest
        fields = [
            'id', 'client', 'business_client', 'client_name', 'client_phone',
            'client_company', 'client_profile_picture',
            'supplier', 'supplier_name', 'supplier_profile_picture',
            'sales_rep', 'sales_rep_name',
            'items', 'note', 'status',
            'total_price',
            'delivery_address',
            'delivery_latitude', 'delivery_longitude',
            'desired_delivery_date',
            'contact_phone',
            'cancelled_by', 'cancel_reason', 'cancelled_at',
            'response', 'photo_reports', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'client', 'business_client', 'supplier', 'sales_rep', 'status',
            'cancelled_by', 'cancel_reason', 'cancelled_at',
            'created_at', 'updated_at'
        ]