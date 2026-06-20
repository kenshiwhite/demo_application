from rest_framework import serializers
from .models import Category, Product

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug']

class ProductSerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(
        source='supplier.company_name',
        read_only=True
    )
    category_name = serializers.CharField(
        source='category.name',
        read_only=True
    )

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'description', 'price',
            'unit', 'stock_quantity', 'is_available',
            'category', 'category_name',
            'supplier', 'supplier_name',
            'image',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['supplier', 'created_at', 'updated_at']