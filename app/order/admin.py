from django.contrib import admin
from .models import Product, PromoCode, Order, OrderItem

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'stock', 'created_at', 'updated_at')
    search_fields = ('name',)
    list_filter = ('created_at', 'updated_at')

@admin.register(PromoCode)
class PromoCodeAdmin(admin.ModelAdmin):
    list_display = ('coupon_name', 'coupon_code', 'type', 'start_at', 'ended_at', 'is_active')
    search_fields = ('coupon_name', 'coupon_code')
    list_filter = ('type', 'is_active', 'start_at', 'ended_at')

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'status', 'total_price', 'promo_code', 'discount', 'created_at')
    search_fields = ('user__email', 'id')
    list_filter = ('status', 'created_at', 'updated_at')

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'product', 'quantity', 'price')
    search_fields = ('order__id', 'product__name')
    list_filter = ('order__created_at',)

