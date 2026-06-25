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
    client_name = serializers.CharField(source='client.username', read_only=True)
    client_phone = serializers.CharField(source='client.phone', read_only=True)
    client_company = serializers.CharField(source='client.company_name', read_only=True)
    supplier_name = serializers.CharField(source='supplier.company_name', read_only=True)
    items = RequestItemSerializer(many=True, read_only=True)
    response = SupplierResponseSerializer(read_only=True)

    class Meta:
        model = ProductRequest
        fields = [
            'id', 'client', 'client_name', 'client_phone', 'client_company',
            'supplier', 'supplier_name',
            'items', 'note', 'status',
            'total_price',
            'delivery_address',
            'desired_delivery_date',
            'contact_phone',
            'response', 'created_at', 'updated_at'
        ]
        read_only_fields = ['client', 'supplier', 'status', 'created_at', 'updated_at']