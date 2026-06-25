from rest_framework import serializers
from .models import Product, CATEGORY_CHOICES

class ProductSerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(
        source='supplier.company_name',
        read_only=True
    )
    category_display = serializers.CharField(
        source='get_category_display',
        read_only=True
    )

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'description', 'price',
            'unit', 'stock_quantity', 'is_available',
            'category', 'category_display',
            'supplier', 'supplier_name',
            'image', 'created_at', 'updated_at'
        ]
        read_only_fields = ['supplier', 'created_at', 'updated_at']

class CategoryChoicesSerializer(serializers.Serializer):
    value = serializers.CharField()
    label = serializers.CharField()