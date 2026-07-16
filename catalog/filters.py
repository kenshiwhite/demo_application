# catalog/filters.py
import django_filters
from .models import Product


class ProductFilter(django_filters.FilterSet):
    # Comma-separated list of category codes, e.g. ?category=food_beverages,electronics
    category = django_filters.CharFilter(method='filter_category')
    min_price = django_filters.NumberFilter(field_name='price', lookup_expr='gte')
    max_price = django_filters.NumberFilter(field_name='price', lookup_expr='lte')

    class Meta:
        model = Product
        fields = ['is_available', 'supplier']

    def filter_category(self, queryset, name, value):
        categories = [c.strip() for c in value.split(',') if c.strip()]
        if not categories:
            return queryset
        return queryset.filter(category__in=categories)