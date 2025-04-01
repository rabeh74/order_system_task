
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Order, Product, PromoCode
from .filters import OrderFilter, PromoCodeFilter, ProductFilter
from .serializers import OrderSerializer, ProductSerializer, PromoCodeSerializer
from .permissions import IsAdminOrReadOnly, IsAdminOrOwner
from django.utils import timezone
from .tasks import send_order_confirmation_email
from drf_spectacular.utils import (
    extend_schema,
    OpenApiParameter,
    OpenApiExample,
    OpenApiTypes
)
from rest_framework.throttling import ScopedRateThrottle
from django.core.cache import cache
from .pagination import ProductPagination


class ProductViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows products to be viewed or edited.
    
    - Regular users can only view available products (stock > 0)
    - Admin users can perform all CRUD operations
    - Product listings are cached for 15 minutes
    """
    serializer_class = ProductSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'products'
    queryset = Product.objects.filter(stock__gt=0)
    permission_classes = [IsAdminOrReadOnly]
    filterset_class = ProductFilter
    pagination_class = ProductPagination

    @extend_schema(
        summary="List all available products",
        description="Returns a paginated list of available products with optional filtering. "
                   "Results are cached for 15 minutes.",
        parameters=[
            OpenApiParameter(
                name='name',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Filter products by name (case insensitive contains search)",
                examples=[
                    OpenApiExample(
                        'Example 1',
                        value='laptop'
                    ),
                    OpenApiExample(
                        'Example 2',
                        value='phone'
                    )
                ]
            ),
            OpenApiParameter(
                name='price__gte',
                type=OpenApiTypes.FLOAT,
                location=OpenApiParameter.QUERY,
                description="Minimum price filter (inclusive)",
                examples=[
                    OpenApiExample(
                        'Minimum $100',
                        value=100.00
                    )
                ]
            ),
            OpenApiParameter(
                name='price__lte',
                type=OpenApiTypes.FLOAT,
                location=OpenApiParameter.QUERY,
                description="Maximum price filter (inclusive)",
                examples=[
                    OpenApiExample(
                        'Maximum $500',
                        value=500.00
                    )
                ]
            ),
            OpenApiParameter(
                name='stock__gte',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Minimum stock quantity filter (inclusive)",
                examples=[
                    OpenApiExample(
                        'At least 5 in stock',
                        value=5
                    )
                ]
            ),
            OpenApiParameter(
                name='stock__lte',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Maximum stock quantity filter (inclusive)",
                examples=[
                    OpenApiExample(
                        'At most 20 in stock',
                        value=20
                    )
                ]
            )
        ],
        examples=[
            OpenApiExample(
                'Successful Response',
                value={
                    "count": 2,
                    "next": None,
                    "previous": None,
                    "results": [
                        {
                            "id": 1,
                            "name": "Laptop",
                            "price": "999.99",
                            "stock": 10
                        },
                        {
                            "id": 2,
                            "name": "Phone",
                            "price": "699.99",
                            "stock": 15
                        }
                    ]
                },
                response_only=True
            )
        ]
    )
    def list(self, request, *args, **kwargs):
        cache_key = f"products_list_{request.GET.urlencode()}"
        data = cache.get(cache_key)
        if not data:
            response = super().list(request, *args, **kwargs)
            cache.set(cache_key, response.data, timeout=60*15)
            return response
        return Response(data)


class OrderViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows orders to be viewed or edited.
    
    - Users can only see their own orders
    - Admin users can see all orders
    - Orders include items, pricing, and optional promo codes
    """
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated, IsAdminOrOwner]
    filterset_class = OrderFilter

    def get_queryset(self):
        base_queryset = Order.objects.all()
        
        if not self._is_admin_user():
            base_queryset = base_queryset.filter(user=self.request.user)
            
        return base_queryset.select_related('user', 'promo_code') \
                          .prefetch_related('items', 'items__product') \
                          .order_by('-created_at')

    @extend_schema(
        summary="Create a new order",
        description="Creates a new order with items and applies promo code if valid.",
        request=OrderSerializer,
        responses={
            201: OpenApiExample(
                'Order Created',
                value={
                    "id": 1,
                    "user": 1,
                    "items": [
                        {
                            "product": 1,
                            "quantity": 2,
                            "price": "199.98"
                        }
                    ],
                    "total_price": "199.98",
                    "discount": "0.00",
                    "created_at": "2023-01-01T12:00:00Z"
                }
            ),
            400: OpenApiExample(
                'Validation Error',
                value={
                    "error": "Invalid product quantity - not enough stock"
                }
            )
        }
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        order = serializer.save(user=request.user)
        
        self._send_order_confirmation(order)
        
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    @extend_schema(
        summary="List all orders",
        description="Returns orders filtered by the current user's permissions "
                   "(admin sees all, regular users see only their own).",
        parameters=[
            OpenApiParameter(
                name='total_price__gte',
                type=OpenApiTypes.FLOAT,
                description="Filter orders with total price ≥ this value",
                examples=[
                    OpenApiExample('Over $100', value=100.00),
                    OpenApiExample('Over $500', value=500.00)
                ]
            ),
            OpenApiParameter(
                name='total_price__lte',
                type=OpenApiTypes.FLOAT,
                description="Filter orders with total price ≤ this value",
                examples=[
                    OpenApiExample('Under $1000', value=1000.00),
                    OpenApiExample('Under $2000', value=2000.00)
                ]
            ),
            OpenApiParameter(
                name='discount__gte',
                type=OpenApiTypes.FLOAT,
                description="Filter orders with discount ≥ this value",
                examples=[
                    OpenApiExample('Discount ≥ $10', value=10.00),
                    OpenApiExample('Discount ≥ $50', value=50.00)
                ]
            ),
            OpenApiParameter(
                name='discount__lte',
                type=OpenApiTypes.FLOAT,
                description="Filter orders with discount ≤ this value",
                examples=[
                    OpenApiExample('Discount ≤ $20', value=20.00),
                    OpenApiExample('Discount ≤ $100', value=100.00)
                ]
            ),
            OpenApiParameter(
                name='created_at__gte',
                type=OpenApiTypes.DATETIME,
                description="Filter orders created after this datetime (ISO 8601 format)",
                examples=[
                    OpenApiExample(
                        'After Jan 1 2023',
                        value='2023-01-01T00:00:00Z'
                    )
                ]
            ),
            OpenApiParameter(
                name='created_at__lte',
                type=OpenApiTypes.DATETIME,
                description="Filter orders created before this datetime (ISO 8601 format)",
                examples=[
                    OpenApiExample(
                        'Before Dec 31 2023',
                        value='2023-12-31T23:59:59Z'
                    )
                ]
            ),
            OpenApiParameter(
                name='promo_code',
                type=OpenApiTypes.STR,
                description="Filter by exact promo code used"
            ),
            OpenApiParameter(
                name='user_email',
                type=OpenApiTypes.STR,
                description="Filter by user email (admin only)",
                examples=[
                    OpenApiExample(
                        'User email',
                        value='customer@example.com'
                    )
                ]
            )
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        """Delete an order using the serializer's delete method"""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        serializer.delete(instance)  
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    def _send_order_confirmation(self, order):
        """Triggers async email confirmation with order details."""
        send_order_confirmation_email.delay(
            order_id=order.id,
            user_email=order.user.email,
            user_first_name=order.user.first_name,
            items_data=self._format_order_items(order),
            total_price=order.total_price,
            discount=order.discount
        )
    
    def _is_admin_user(self):
        """Helper to check if user has admin privileges."""
        return self.request.user.is_staff or self.request.user.is_superuser
    
    def _format_order_items(self, order):
        """Formats order items for email presentation."""
        return [{
            'product_name': item.product.name,
            'quantity': item.quantity
        } for item in order.items.all()]



class PromoCodeViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows promo codes to be viewed or edited.
    
    - Regular users can only view active promo codes
    - Admin users can perform all CRUD operations
    """
    serializer_class = PromoCodeSerializer
    permission_classes = [IsAdminOrReadOnly]
    filterset_class = PromoCodeFilter

    def get_queryset(self):
        """Returns active promocodes for regular users, all for admins."""
        base_queryset = PromoCode.objects.all()
        
        if not self._is_admin_user():
            base_queryset = self._filter_active_promocodes(base_queryset)
            
        return base_queryset.order_by('-start_at')

    @extend_schema(
        summary="List promo codes",
        description="Returns active promo codes for regular users, all for admins",
        parameters=[
            OpenApiParameter(
                name='coupon_code',
                type=OpenApiTypes.STR,
                description="Filter by coupon code (contains search)",
                examples=[
                    OpenApiExample('SUMMER', value='SUMMER'),
                    OpenApiExample('WINTER', value='WINTER')
                ]
            ),
            OpenApiParameter(
                name='is_active',
                type=OpenApiTypes.BOOL,
                description="Filter by active status (admin only)",
                examples=[
                    OpenApiExample('Active only', value=True),
                    OpenApiExample('Inactive only', value=False)
                ]
            )
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def _is_admin_user(self):
        """Helper to check admin status."""
        return self.request.user.is_staff or self.request.user.is_superuser

    def _filter_active_promocodes(self, queryset):
        """Filters queryset to only currently valid promocodes."""
        now = timezone.now()
        return queryset.filter(
            is_active=True,
            start_at__lte=now,
            ended_at__gte=now
        )