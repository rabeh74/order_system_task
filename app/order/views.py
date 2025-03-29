from rest_framework import viewsets, status , permissions
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Order, Product, PromoCode
from .filters import OrderFilter, PromoCodeFilter, ProductFilter
from .serializers import OrderSerializer, ProductSerializer, PromoCodeSerializer
from .permissions import IsAdminOrReadOnly , IsAdminOrOwner
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from .tasks import send_order_confirmation_email


class ProductViewSet(viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    permission_classes = [IsAdminOrReadOnly]
    queryset = Product.objects.filter(stock__gt=0)
    filter_backends = [DjangoFilterBackend]
    filterset_class = ProductFilter
    
class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated , IsAdminOrOwner]
    filter_backends = [DjangoFilterBackend]
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
    
    def destroy(self, request, *args, **kwargs):
        """Delete an order using the serializer's delete method"""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        serializer.delete(instance)  # This should trigger the serializer's delete method
        return Response(status=status.HTTP_204_NO_CONTENT)


class PromoCodeViewSet(viewsets.ModelViewSet):
    serializer_class = PromoCodeSerializer
    filter_backends = [DjangoFilterBackend]
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
