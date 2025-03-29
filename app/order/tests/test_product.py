from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from order.models import Product
from decimal import Decimal


User = get_user_model()

class ProductViewSetTestCase(APITestCase):
    def setUp(self):
        self.client = APIClient()
        
        # Create users
        self.staff_user = User.objects.create_superuser(email='staff@example.com', password='staffpass123')
        self.regular_user = User.objects.create_user(email='user@example.com', password='userpass123')
        
        # Create initial product
        self.product = Product.objects.create(name='Laptop', price=999.99, stock=10)
        
        # URLs
        self.list_url = reverse('product-list')
        self.detail_url = reverse('product-detail', kwargs={'pk': self.product.pk})

    def test_list_products_anyone(self):
        """Test that anyone can list products"""
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_retrieve_product_anyone(self):
        """Test that anyone can retrieve a product"""
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Laptop')

    def test_create_product_staff(self):
        """Test that staff can create a product"""
        self.client.force_authenticate(user=self.staff_user)
        data = {'name': 'Keyboard', 'price': 49.99, 'stock': 20}
        response = self.client.post(self.list_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Product.objects.count(), 2)
        self.assertEqual(response.data['name'], 'Keyboard')

    def test_create_product_non_staff(self):
        """Test that non-staff cannot create a product"""
        self.client.force_authenticate(user=self.regular_user)
        data = {'name': 'Monitor', 'price': 199.99, 'stock': 10}
        response = self.client.post(self.list_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_product_staff(self):
        """Test that staff can update a product"""
        self.client.force_authenticate(user=self.staff_user)
        data = {'name': 'Laptop Updated', 'price': 1099.99, 'stock': 15}
        response = self.client.put(self.detail_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.product.refresh_from_db()
        self.assertEqual(self.product.name, 'Laptop Updated')
        self.assertEqual(float(self.product.price), 1099.99)

    def test_update_product_non_staff(self):
        """Test that non-staff cannot update a product"""
        self.client.force_authenticate(user=self.regular_user)
        data = {'name': 'Laptop Updated', 'price': 1099.99, 'stock': 15}
        response = self.client.put(self.detail_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_list_products_with_only_stock(self):
        """Test that only products with stock are listed"""
        response = self.client.get(self.list_url)
        Product.objects.create(name='mobile', price=999.99, stock=0)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], 'Laptop')


class ProductFilterTests(APITestCase):
    def setUp(self):
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
        self.product4 = Product.objects.create(
            name="HDMI Cable",
            price=Decimal('14.99'),
            stock=150
        )
        
        # Create user and authenticate
        self.user = User.objects.create_user(
            email="test@example.com",
            password="securepassword123"
        )
        self.client.force_authenticate(user=self.user)

    def test_product_filter_by_name(self):
        url = reverse('product-list') + '?name=cable'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)  
        
        url = reverse('product-list') + '?name=headphones'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)     

    def test_product_filter_by_price(self):
        url = reverse('product-list') + '?price__gte=50'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)  
        
        url = reverse('product-list') + '?price__lte=20'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)  
        
        url = reverse('product-list') + '?price__gte=10&price__lte=50'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)  

    def test_product_filter_by_stock(self):
        url = reverse('product-list') + '?stock__gte=150'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)  
        
        url = reverse('product-list') + '?stock__lte=75'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)  
        
        url = reverse('product-list') + '?stock__gte=75&stock__lte=150'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)  

    def test_product_multiple_filters(self):
        url = reverse('product-list') + '?name=cable&price__lte=15'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2) 
        
        url = reverse('product-list') + '?name=cable&stock__gte=175'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)  

