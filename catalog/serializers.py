# catalog/serializers.py
from rest_framework import serializers
from .models import Product, CATEGORY_CHOICES

class ProductSerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(
        source='supplier.company_name',
        read_only=True
    )
    supplier_profile_picture = serializers.ImageField(
        source='supplier.profile_picture',
        read_only=True
    )
    category_display = serializers.CharField(
        source='get_category_display',
        read_only=True
    )
    city_display = serializers.CharField(
        source='get_city_display',
        read_only=True
    )

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'description', 'price', 'cost_price',
            'unit', 'stock_quantity', 'min_order_quantity', 'is_available',
            'category', 'category_display',
            'city', 'city_display',
            'supplier', 'supplier_name', 'supplier_profile_picture',
            'image', 'created_at', 'updated_at'
        ]
        read_only_fields = ['supplier', 'created_at', 'updated_at']

    def to_representation(self, instance):
        # Cost price is margin-sensitive business data — only the product's
        # own supplier (or their sales reps) should ever see it in a
        # response. A client browsing the catalog must never receive
        # another business's cost basis. Writing it (create/update) is
        # unaffected — this only strips it from what gets read back.
        data = super().to_representation(instance)
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        business = None
        if user and user.is_authenticated:
            business = user if user.role == 'supplier' else user.business_supplier
        if not business or business != instance.supplier:
            data['cost_price'] = None
        return data

    def validate_city(self, value):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if not user or not user.is_authenticated:
            return value
        # A worker manages stock for whichever supplier business they belong
        # to; a supplier manages their own. Either way city must be one the
        # business actually services.
        business = user if user.role == 'supplier' else user.business_supplier
        if business and business.service_cities and value not in business.service_cities:
            raise serializers.ValidationError(
                'Этот город не входит в список городов обслуживания поставщика.'
            )
        return value

class CategoryChoicesSerializer(serializers.Serializer):
    value = serializers.CharField()
    label = serializers.CharField()