from django_filters import rest_framework as filters
from django_filters import OrderingFilter
from .models import Order, PromoCode, Product
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

class OrderFilter(filters.FilterSet):
    """
    FilterSet for Order model that allows filtering by:
    - total price (exact, range)
    - discount (exact, range)
    - creation date (range)
    - promo code (exact match)
    - user (ID)
    - status (exact match)
    """
    total_price = filters.RangeFilter()
    discount = filters.RangeFilter()
    created_at = filters.DateTimeFromToRangeFilter()
    promo_code = filters.CharFilter(field_name="promo_code__coupon_code", lookup_expr='iexact')
    user_email = filters.CharFilter(field_name="user__email", lookup_expr='icontains')
    
    ordering = OrderingFilter(
        fields=(
            ('total_price', 'total_price'),
            ('created_at', 'created_at'),
            ('discount', 'discount'),
        )
    )

    class Meta:
        model = Order
        fields = {
            'user': ['exact'],
            'status': ['exact'],
            'total_price': ['exact', 'gte', 'lte'],
            'discount': ['exact', 'gte', 'lte'],
            'created_at': ['exact', 'gte', 'lte'],
        }


class PromoCodeFilter(filters.FilterSet):
    """
    FilterSet for PromoCode model that allows filtering by:
    - coupon code/name (contains)
    - type (exact match)
    - fixed amount (range)
    - discount percentage (range)
    - date ranges (start/end dates)
    - active status
    """
    coupon_code = filters.CharFilter(lookup_expr='icontains')
    coupon_name = filters.CharFilter(lookup_expr='icontains')
    fixed_amount = filters.RangeFilter()
    discount_percentage = filters.RangeFilter()
    start_at = filters.DateTimeFromToRangeFilter()
    ended_at = filters.DateTimeFromToRangeFilter()
    
    ordering = OrderingFilter(
        fields=(
            ('fixed_amount', 'fixed_amount'),
            ('discount_percentage', 'discount_percentage'),
            ('start_at', 'start_date'),
            ('ended_at', 'end_date'),
        )
    )

    class Meta:
        model = PromoCode
        fields = {
            'coupon_code': ['exact', 'icontains'],
            'coupon_name': ['exact', 'icontains'],
            'type': ['exact'],
            'fixed_amount': ['exact', 'gte', 'lte'],
            'discount_percentage': ['exact', 'gte', 'lte'],
            'start_at': ['exact', 'gte', 'lte'],
            'ended_at': ['exact', 'gte', 'lte'],
            'is_active': ['exact'],
        }


class ProductFilter(filters.FilterSet):
    """
    FilterSet for Product model that allows filtering by:
    - name (contains)
    - price (range)
    - stock (range)
    """
    name = filters.CharFilter(lookup_expr='icontains')
    price = filters.RangeFilter()
    stock = filters.RangeFilter()
    
    ordering = OrderingFilter(
        fields=(
            ('name', 'name'),
            ('price', 'price'),
            ('stock', 'stock'),
        )
    )

    class Meta:
        model = Product
        fields = {
            'name': ['exact', 'icontains'],
            'price': ['exact', 'gte', 'lte'],
            'stock': ['exact', 'gte', 'lte'],
        }