from rest_framework import serializers
from .models import ProductRequest, SupplierResponse

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
    client_name = serializers.CharField(
        source='client.username',
        read_only=True
    )
    product_name = serializers.CharField(
        source='product.name',
        read_only=True
    )
    response = SupplierResponseSerializer(read_only=True)

    class Meta:
        model = ProductRequest
        fields = [
            'id', 'product', 'product_name',
            'client', 'client_name',
            'quantity', 'note', 'status',
            'total_price',                  # ← add this
            'response', 'created_at', 'updated_at'
        ]
        read_only_fields = ['client', 'status', 'created_at', 'updated_at']