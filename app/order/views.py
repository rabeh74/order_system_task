from rest_framework import viewsets, status , permissions
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Order, Product, PromoCode
from .filters import OrderFilter, PromoCodeFilter, ProductFilter
from .serializers import OrderSerializer, ProductSerializer, PromoCodeSerializer
from .permissions import IsAdminOrReadOnly , IsAdminOrOwner
from django.utils import timezone
from .tasks import send_order_confirmation_email
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework.throttling import ScopedRateThrottle

class ProductViewSet(viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'products'  
    queryset = Product.objects.filter(stock__gt=0)
    permission_classes = [IsAdminOrReadOnly]
    filterset_class = ProductFilter

    @extend_schema(
        parameters=[
            OpenApiParameter(name='name', description="Filter products by **name (case insensitive)**", required=False, type=str),
            OpenApiParameter(name='price__gte', description="Filter products with a price **greater than or equal** to this value", required=False, type=float),
            OpenApiParameter(name='price__lte', description="Filter products with a price **less than or equal** to this value", required=False, type=float),
            OpenApiParameter(name='stock__gte', description="Filter products with stock **greater than or equal** to this value", required=False, type=int),
            OpenApiParameter(name='stock__lte', description="Filter products with stock **less than or equal** to this value", required=False, type=int),
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
    
class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated , IsAdminOrOwner]
    filterset_class = OrderFilter

    def get_queryset(self):
        if self.request.user.is_staff or self.request.user.is_superuser:
            return Order.objects.all()
        return Order.objects.filter(user=self.request.user)
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        order = serializer.save(user=request.user)
        
        send_order_confirmation_email.delay(
            order_id=order.id,
            user_email =request.user.email,
            user_first_name=request.user.first_name,
            items_data=[
                {'product_name': item.product.name, 'quantity': item.quantity}
                for item in order.items.all()
            ],
            total_price=order.total_price,
            discount=order.discount
        )
        
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        """Update an existing order (e.g., items or promo code)"""
        order = self.get_object()
        serializer = self.get_serializer(order, data=request.data, partial=False, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user)

        send_order_confirmation_email.delay(
            order_id=order.id,
            user_email =request.user.email,
            user_first_name=request.user.first_name,
            items_data=[
                {'product_name': item.product.name, 'quantity': item.quantity}
                for item in order.items.all()
            ],
            total_price=order.total_price,
            discount=order.discount
        )
        
        return Response(serializer.data)
    
    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='total_price__gte', description="Filter orders with a total price **greater than or equal** to this value", required=False, type=float
            ),
            OpenApiParameter(
                name='total_price__lte', description="Filter orders with a total price **less than or equal** to this value", required=False, type=float
            ),
            OpenApiParameter(
                name='discount__gte', description="Filter orders with a discount **greater than or equal** to this value", required=False, type=float
            ),
            OpenApiParameter(
                name='discount__lte', description="Filter orders with a discount **less than or equal** to this value", required=False, type=float
            ),
            OpenApiParameter(
                name='created_at__gte', description="Filter orders created **after** this datetime (format: YYYY-MM-DDTHH:MM:SSZ)", required=False, type=str
            ),
            OpenApiParameter(
                name='created_at__lte', description="Filter orders created **before** this datetime (format: YYYY-MM-DDTHH:MM:SSZ)", required=False, type=str
            ),
            OpenApiParameter(
                name='promo_code', description="Filter orders by **exact promo code**", required=False, type=str
            ),
            OpenApiParameter(
                name='user_email', description="Filter orders by **user's email (case insensitive)**", required=False, type=str
            ),
        ]
    )
    def list(self, request, *args, **kwargs):
        """List all orders (for staff and superuser)"""
        return super().list(request, *args, **kwargs)
    
    def destroy(self, request, *args, **kwargs):
        """Delete an order using the serializer's delete method"""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        serializer.delete(instance)  # This should trigger the serializer's delete method
        return Response(status=status.HTTP_204_NO_CONTENT)


class PromoCodeViewSet(viewsets.ModelViewSet):
    serializer_class = PromoCodeSerializer
    permission_classes = [IsAdminOrReadOnly]
    filterset_class = PromoCodeFilter

    def get_queryset(self):
        if self.request.user.is_staff or self.request.user.is_superuser:
            return PromoCode.objects.all()
        return PromoCode.objects.filter(
            is_active=True,
            start_at__lte=timezone.now(),
            ended_at__gte=timezone.now()
        )
    
    @extend_schema(
        parameters=[
            OpenApiParameter(name='coupon_code', description="Filter promo codes by **coupon code (contains search)**", required=False, type=str),
            OpenApiParameter(name='coupon_name', description="Filter promo codes by **coupon name (contains search)**", required=False, type=str),
            OpenApiParameter(name='type', description="Filter promo codes by **exact type**", required=False, type=str),
            OpenApiParameter(name='fixed_amount__gte', description="Filter promo codes where fixed amount is **greater than or equal** to this value", required=False, type=float),
            OpenApiParameter(name='fixed_amount__lte', description="Filter promo codes where fixed amount is **less than or equal** to this value", required=False, type=float),
            OpenApiParameter(name='start_at__gte', description="Filter promo codes with a start date **after this date** (format: YYYY-MM-DDTHH:MM:SSZ)", required=False, type=str),
            OpenApiParameter(name='start_at__lte', description="Filter promo codes with a start date **before this date** (format: YYYY-MM-DDTHH:MM:SSZ)", required=False, type=str),
            OpenApiParameter(name='is_active', description="Filter active promo codes (**true/false**)", required=False, type=bool),
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
