from rest_framework import serializers
from .models import ProductRequest, RequestItem, SupplierResponse

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

    class Meta:
        model = SupplierResponse
        fields = [
            'id', 'message', 'offered_price',
            'supplier', 'supplier_name', 'created_at'
        ]
        read_only_fields = ['supplier', 'created_at']

class ProductRequestSerializer(serializers.ModelSerializer):
    client_name = serializers.SerializerMethodField()
    client_phone = serializers.SerializerMethodField()
    client_company = serializers.SerializerMethodField()
    supplier_name = serializers.CharField(source='supplier.company_name', read_only=True)
    sales_rep_name = serializers.CharField(source='sales_rep.username', read_only=True)
    items = RequestItemSerializer(many=True, read_only=True)
    response = SupplierResponseSerializer(read_only=True)

    def get_client_name(self, obj):
        return obj.client.username if obj.client else obj.business_client.name

    def get_client_phone(self, obj):
        return obj.client.phone if obj.client else obj.business_client.phone

    def get_client_company(self, obj):
        return obj.client.company_name if obj.client else obj.business_client.company_name

    class Meta:
        model = ProductRequest
        fields = [
            'id', 'client', 'business_client', 'client_name', 'client_phone', 'client_company',
            'supplier', 'supplier_name',
            'sales_rep', 'sales_rep_name',
            'items', 'note', 'status',
            'total_price',
            'delivery_address',
            'delivery_latitude', 'delivery_longitude',
            'desired_delivery_date',
            'contact_phone',
            'cancelled_by', 'cancel_reason', 'cancelled_at',
            'response', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'client', 'business_client', 'supplier', 'sales_rep', 'status',
            'cancelled_by', 'cancel_reason', 'cancelled_at',
            'created_at', 'updated_at'
        ]
