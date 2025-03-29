from django_filters import rest_framework as filters
from .models import Order, PromoCode, Product
from django.contrib.auth import get_user_model

User = get_user_model()

class OrderFilter(filters.FilterSet):
    total_price__gte = filters.NumberFilter(field_name="total_price", lookup_expr='gte')
    total_price__lte = filters.NumberFilter(field_name="total_price", lookup_expr='lte')
    discount__gte = filters.NumberFilter(field_name="discount", lookup_expr='gte')
    discount__lte = filters.NumberFilter(field_name="discount", lookup_expr='lte')
    created_at__gte = filters.DateTimeFilter(field_name="created_at", lookup_expr='gte')
    created_at__lte = filters.DateTimeFilter(field_name="created_at", lookup_expr='lte')
    promo_code = filters.CharFilter(field_name="promo_code__coupon_code", lookup_expr='exact')
    user_email = filters.CharFilter(field_name="user__email", lookup_expr='icontains')

    class Meta:
        model = Order
        fields = ['user', 'total_price', 'discount', 'created_at', 'promo_code']

class PromoCodeFilter(filters.FilterSet):
    coupon_code = filters.CharFilter(lookup_expr='icontains')
    coupon_name = filters.CharFilter(lookup_expr='icontains')
    type = filters.CharFilter(lookup_expr='exact')
    fixed_amount__gte = filters.NumberFilter(field_name="fixed_amount", lookup_expr='gte')
    fixed_amount__lte = filters.NumberFilter(field_name="fixed_amount", lookup_expr='lte')
    start_at__gte = filters.DateTimeFilter(field_name="start_at", lookup_expr='gte')
    start_at__lte = filters.DateTimeFilter(field_name="start_at", lookup_expr='lte')
    ended_at__gte = filters.DateTimeFilter(field_name="ended_at", lookup_expr='gte')
    ended_at__lte = filters.DateTimeFilter(field_name="ended_at", lookup_expr='lte')
    is_active = filters.BooleanFilter()

    class Meta:
        model = PromoCode
        fields = ['coupon_code', 'coupon_name', 'type', 'fixed_amount', 'start_at', 'ended_at', 'is_active']

class ProductFilter(filters.FilterSet):
    name = filters.CharFilter(lookup_expr='icontains')
    price__gte = filters.NumberFilter(field_name="price", lookup_expr='gte')
    price__lte = filters.NumberFilter(field_name="price", lookup_expr='lte')
    stock__gte = filters.NumberFilter(field_name="stock", lookup_expr='gte')
    stock__lte = filters.NumberFilter(field_name="stock", lookup_expr='lte')

    class Meta:
        model = Product
        fields = ['name', 'price', 'stock']

