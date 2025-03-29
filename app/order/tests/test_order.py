from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from order.models import Order, OrderItem, Product, PromoCode
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta

User = get_user_model()

class OrderViewSetTestCase(APITestCase):
    def setUp(self):
        self.client = APIClient()
        
        # Create a user for authentication
        self.user = User.objects.create_user(email='test@example.com', password='testpass123')
        self.client.force_authenticate(user=self.user)
        
        # Create test data
        self.product1 = Product.objects.create(name='Laptop', price=100, stock=10)
        self.product2 = Product.objects.create(name='Mouse', price=30, stock=50)
        
        self.order = Order.objects.create(user=self.user, total_price=100.00, discount=0)
        self.order_item = OrderItem.objects.create(
                order=self.order,
                product=self.product1,
                quantity=5,
                price=self.product1.price * 5
            )
        self.promo_code = PromoCode.objects.create(
            coupon_code='SAVE10', coupon_name='Save $10', type='FIXED',
            fixed_amount=10.00, start_at=timezone.now(),
            ended_at=timezone.now() + timezone.timedelta(days=30),
            is_active=True
        )
        
        # URLs
        self.list_url = reverse('order-list')
        self.detail_url = reverse('order-detail', args=[self.order.id])

    def test_get_queryset_authenticated(self):
        """Test that get_queryset returns only the authenticated user's orders"""
        other_user = User.objects.create_user(email='other@example.com', password='otherpass123')
        Order.objects.create(user=other_user, total_price=100.00, discount=0)
        
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)  # Only the authenticated user's order
        self.assertEqual(response.data[0]['id'], self.order.id)

    def test_get_queryset_unauthenticated(self):
        """Test that unauthenticated users are denied access"""

        self.client.force_authenticate(user=None)  
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    
    def test_create_order_success(self):
        """Test successful order creation with items and promo code"""
        data = {
            'items': [
                {'product': self.product1.id, 'quantity': 2},
                {'product': self.product2.id, 'quantity': 1}
            ],
            'coupon_code': 'SAVE10'
        }
        response = self.client.post(self.list_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Order.objects.count(), 2) 
        order = Order.objects.get(id=response.data['id'])
        
        # Check price calculation
        expected_total_before_discount = (self.product1.price * 2) + (self.product2.price * 1)
        expected_discount = 10.00
        expected_total = expected_total_before_discount - expected_discount

        self.assertEqual(float(order.total_price), float(expected_total))
        self.assertEqual(float(order.discount), expected_discount)
        self.assertEqual(order.promo_code.coupon_code, 'SAVE10')
        self.assertEqual(order.items.count(), 2)
        self.assertEqual(order.status , "PENDING")
        
        

    def test_create_order_invalid_data(self):
        """Test order creation with invalid data (e.g., missing items)"""
        data = {'promo_code': 'SAVE10'}  # No items
        response = self.client.post(self.list_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('items', response.data)

    def test_create_order_invalid_promo_code(self):
        """Test order creation with an invalid promo code"""
        data = {
            'items': [{'product': self.product1.id, 'quantity': 1}],
            'coupon_code': 'INVALIDCODE'
        }
        response = self.client.post(self.list_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'Invalid promo code')

    def test_update_order_full(self):
        """Test full update of an order (replacing items and promo code)"""
        
        new_promo_code = PromoCode.objects.create(
            coupon_code='SAVE50%', coupon_name='Save 50%', type='PERCENTAGE',
            discount_percentage=50, start_at=timezone.now(),
            ended_at=timezone.now() + timezone.timedelta(days=30),
            is_active=True, max_discount_amount=50.00
        )

        data = {
            'items': [{'product': self.product2.id, 'quantity': 3}],
            'coupon_code': new_promo_code.coupon_code
        }

        response = self.client.put(self.detail_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        order = Order.objects.get(id=self.order.id)
        
        # Check updated items
        self.assertEqual(order.items.count(), 1)
        self.assertEqual(order.items.first().product, self.product2)
        self.assertEqual(order.items.first().quantity, 3)
        
        # Check price calculation
        expected_total_before_discount = self.product2.price * 3
        expected_discount = min(expected_total_before_discount * 0.5, new_promo_code.max_discount_amount)
        expected_total = expected_total_before_discount - expected_discount
        
        self.assertEqual(float(order.total_price), float(expected_total))
        self.assertEqual(float(order.discount), expected_discount)
        self.assertEqual(order.promo_code.coupon_code, 'SAVE50%')

    def test_update_order_partial_items(self):
        """Test partial update of items without changing promo code"""
        data = {
            'items': [{'product': self.product2.id, 'quantity': 2}]
        }
        response = self.client.put(self.detail_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        order = Order.objects.get(id=self.order.id)
        
        self.assertEqual(order.items.count(), 1)
        self.assertEqual(order.items.first().product, self.product2)
        self.assertEqual(order.items.first().quantity, 2)
        self.assertEqual(float(order.total_price), float(self.product2.price * 2))
        self.assertEqual(float(order.discount), 0) 
        self.assertIsNone(order.promo_code)

    def test_update_order_invalid_promo_code(self):
        """Test update with an invalid promo code"""
        data = {
            'items': [{'product': self.product1.id, 'quantity': 1}],
            'coupon_code': 'INVALIDCODE'
        }
        response = self.client.put(self.detail_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'Invalid promo code')

    def test_retrieve_order(self):
        """Test retrieving an order"""
        OrderItem.objects.create(
            order=self.order,
            product=self.product1,
            quantity=1,
            price=self.product1.price
        )

        self.order.save()

        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.order.id)
        self.assertEqual(len(response.data['items']), 2)
    
    def test_list_orders(self):
        """Test listing all orders for the user"""
        Order.objects.create(user=self.user, total_price=50.00, discount=0)  
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2) 

    def test_unauthorized_access(self):
        """Test that another user cannot access or update the order"""
        other_user = User.objects.create_user(email='other@example.com', password='otherpass123')
        self.client.force_authenticate(user=other_user)
        
        # Test retrieve
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        
        # Test update
        data = {'items': [{'product_id': self.product1.id, 'quantity': 1}]}
        response = self.client.put(self.detail_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_delete_order(self):
        """Test deleting an order"""
        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Order.objects.count(), 0)
    
    def test_check_stock(self):
        """Test stock check during order creation"""
        data = {
            'items': [
                {'product': self.product1.id, 'quantity': 5},
                {'product': self.product2.id, 'quantity': 10}
            ]
        }
        response = self.client.post(self.list_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.product1.refresh_from_db()
        self.product2.refresh_from_db()
        self.assertEqual(self.product1.stock, 5)
        self.assertEqual(self.product2.stock, 40)
    
    
    def test_update_order_stock_restoration(self):
        """Test that stock is restored when order items are updated"""
        initial_stock_product1 = self.product1.stock  # 10
        initial_stock_product2 = self.product2.stock  # 50
        
        data = {
            'items': [{'product': self.product2.id, 'quantity': 2}],
            'coupon_code': 'SAVE10'
        }
        response = self.client.put(self.detail_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.product1.refresh_from_db()
        self.product2.refresh_from_db()
        
        self.assertEqual(self.product1.stock, initial_stock_product1 + self.order_item.quantity)  
        self.assertEqual(self.product2.stock, initial_stock_product2 - 2) 
    
    def test_delete_order(self):
        """Test deleting an order"""
        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Order.objects.count(), 0)
        self.product1.refresh_from_db()
        self.assertEqual(self.product1.stock, 15)
    

class OrderFilterTests(APITestCase):
    def setUp(self):
        # Create users
        self.admin_user = User.objects.create_superuser(
            email="admin@example.com",
            password="securepassword123"
        )
        self.user = User.objects.create_user(
            email="test@example.com",
            password="securepassword123"
        )
        self.another_user = User.objects.create_user(
            email="another@example.com",
            password="securepassword123"
        )
        
        # Create promo codes
        now = timezone.now()
        self.promo_code1 = PromoCode.objects.create(
            coupon_code="DISCOUNT10",
            coupon_name="10% Discount",
            type="PERCENTAGE",
            discount_percentage=10,
            fixed_amount=0,
            start_at=now - timedelta(days=10),
            ended_at=now + timedelta(days=10),
            is_active=True
        )
        self.promo_code2 = PromoCode.objects.create(
            coupon_code="FIXED20",
            coupon_name="$20 Off",
            type="FIXED",
            fixed_amount=Decimal('20.00'),
            start_at=now - timedelta(days=5),
            ended_at=now + timedelta(days=5),
            is_active=True
        )
        
        # Create orders
        self.order1 = Order.objects.create(
            user=self.user,
            total_price=Decimal('150.00'),
            discount=Decimal('15.00'),
            promo_code=self.promo_code1
        )
        self.order2 = Order.objects.create(
            user=self.user,
            total_price=Decimal('200.00'),
            discount=Decimal('20.00'),
            promo_code=self.promo_code2
        )
        self.order3 = Order.objects.create(
            user=self.another_user,
            total_price=Decimal('75.00'),
            discount=Decimal('1.00'),
        )
        
        # Create products
        self.product1 = Product.objects.create(
            name="Premium Headphones",
            price=Decimal('99.99'),
            stock=50
        )
        self.product2 = Product.objects.create(
            name="Bluetooth Speaker",
            price=Decimal('49.99'),
            stock=100
        )
        self.product3 = Product.objects.create(
            name="USB-C Cable",
            price=Decimal('9.99'),
            stock=200
        )
        
        # Authenticate
        self.client.force_authenticate(user=self.admin_user)

    def test_order_filter_by_total_price(self):
        # Test gte filter
        url = reverse('order-list') + '?total_price__gte=100'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)  
        
        # Test lte filter
        url = reverse('order-list') + '?total_price__lte=100'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)  
        
        # Test range filter
        url = reverse('order-list') + '?total_price__gte=100&total_price__lte=175'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)  

    def test_order_filter_by_discount(self):
        # Test gte filter
        
        url = reverse('order-list') + '?discount__gte=15'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)  
        
        # Test lte filter
        url = reverse('order-list') + '?discount__lte=10'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)  

    def test_order_filter_by_created_at(self):
        now = timezone.now()
        date_gte = (now - timedelta(days=2.5)).strftime('%Y-%m-%dT%H:%M:%S')
        date_lte = (now - timedelta(days=2.5)).strftime('%Y-%m-%dT%H:%M:%S')
        self.order1.created_at = now - timedelta(days=3)
        self.order1.save()
        # Test gte filter
        url = reverse('order-list') + f'?created_at__gte={date_gte}'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)  
        
        # Test lte filter
        url = reverse('order-list') + f'?created_at__lte={date_lte}'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)  

    def test_order_filter_by_promo_code(self):
        url = reverse('order-list') + '?promo_code=DISCOUNT10'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)  
        self.assertEqual(response.data[0]['id'], self.order1.id)

    def test_order_filter_by_user_email(self):
        url = reverse('order-list') + '?user_email=test@example'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)  
        
        url = reverse('order-list') + '?user_email=another'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)  

    def test_order_filter_by_user(self):
        url = reverse('order-list') + f'?user={self.user.id}'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)  

    def test_order_multiple_filters(self):
        url = reverse('order-list') + f'?total_price__gte=100&discount__gte=15&user={self.user.id}'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)  
