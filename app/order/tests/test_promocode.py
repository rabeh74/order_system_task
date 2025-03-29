from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from order.models import PromoCode
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta

User = get_user_model()


class PromoCodeViewSetTestCase(APITestCase):
    def setUp(self):
        self.client = APIClient()
        
        # Create users
        self.staff_user = User.objects.create_superuser(email='staff@example.com', password='staffpass123')
        self.regular_user = User.objects.create_user(email='user@example.com', password='userpass123')
        
        # Create initial promo code
        self.promo_code = PromoCode.objects.create(
            coupon_code='SAVE10',
            coupon_name='Save $10',
            type='FIXED',
            fixed_amount=10.00,
            start_at=timezone.now() - timezone.timedelta(days=1),
            ended_at=timezone.now() + timezone.timedelta(days=30),
            is_active=True,
        )
        
        # URLs
        self.list_url = reverse('promo-code-list')
        self.detail_url = reverse('promo-code-detail', kwargs={'pk': self.promo_code.pk})

    def test_list_promo_codes_anyone(self):
        """Test that anyone can list promo codes without authentication"""
        self.client.force_authenticate(user=None)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['coupon_code'], 'SAVE10')

    def test_retrieve_promo_code_anyone(self):
        """Test that anyone can retrieve a promo code without authentication"""
        self.client.force_authenticate(user=None)
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['coupon_code'], 'SAVE10')

    def test_create_promo_code_staff(self):
        """Test that staff can create a promo code"""
        self.client.force_authenticate(user=self.staff_user)
        data = {
            'coupon_code': 'HALFOFF',
            'coupon_name': '50% Off',
            'type': 'PERCENTAGE',
            'discount_percentage': 50.00,
            'start_at': timezone.now().isoformat(),
            'ended_at': (timezone.now() + timezone.timedelta(days=15)).isoformat(),
            'is_active': True,
        }
        response = self.client.post(self.list_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(PromoCode.objects.count(), 2)
        self.assertEqual(response.data['coupon_code'], 'HALFOFF')

    def test_create_promo_code_non_staff(self):
        """Test that non-staff cannot create a promo code"""
        self.client.force_authenticate(user=self.regular_user)
        data = {
            'coupon_code': 'EXTRA20',
            'coupon_name': 'Extra $20',
            'type': 'FIXED',
            'fixed_amount': 20.00,
            'start_at': timezone.now().isoformat(),
            'ended_at': (timezone.now() + timezone.timedelta(days=10)).isoformat(),
            'is_active': True,
        }
        response = self.client.post(self.list_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_promo_code_staff(self):
        """Test that staff can update a promo code"""
        self.client.force_authenticate(user=self.staff_user)
        data = {
            'coupon_code': 'SAVE10',
            'coupon_name': 'Save $15',
            'type': 'FIXED',
            'fixed_amount': 15.00,
            'start_at': timezone.now().isoformat(),
            'ended_at': (timezone.now() + timezone.timedelta(days=30)).isoformat(),
            'is_active': True,
        }
        response = self.client.put(self.detail_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.promo_code.refresh_from_db()
        self.assertEqual(self.promo_code.coupon_name, 'Save $15')
        self.assertEqual(float(self.promo_code.fixed_amount), 15.00)

    def test_update_promo_code_non_staff(self):
        """Test that non-staff cannot update a promo code"""
        self.client.force_authenticate(user=self.regular_user)
        data = {
            'coupon_code': 'SAVE10',
            'coupon_name': 'Save $20',
            'type': 'FIXED',
            'fixed_amount': 20.00,
            'start_at': timezone.now().isoformat(),
            'ended_at': (timezone.now() + timezone.timedelta(days=30)).isoformat(),
            'is_active': True,
        }
        response = self.client.put(self.detail_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_promo_code_unauthenticated(self):
        """Test that unauthenticated users cannot create a promo code"""
        self.client.force_authenticate(user=None)
        data = {
            'coupon_code': 'EXTRA20',
            'coupon_name': 'Extra $20',
            'type': 'FIXED',
            'fixed_amount': 20.00,
            'start_at': timezone.now().isoformat(),
            'ended_at': (timezone.now() + timezone.timedelta(days=10)).isoformat(),
            'is_active': True,
        }
        response = self.client.post(self.list_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class PromoCodeFilterTests(APITestCase):
    def setUp(self):
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
        self.promo_code3 = PromoCode.objects.create(
            coupon_code="EXPIRED",
            coupon_name="Expired Code",
            type="PERCENTAGE",
            discount_percentage=15,
            fixed_amount=0,
            start_at=now - timedelta(days=30),
            ended_at=now - timedelta(days=15),
            is_active=False
        )
        
        self.admin_user = User.objects.create_superuser(
            email="test@example.com",
            password="securepassword123"
        )
        self.client.force_authenticate(user=self.admin_user)

    def test_promo_code_filter_by_coupon_code(self):
        url = reverse('promo-code-list') + '?coupon_code=DISCOUNT'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)  
        
        url = reverse('promo-code-list') + '?coupon_code=FIXED'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)  

    def test_promo_code_filter_by_coupon_name(self):
        url = reverse('promo-code-list') + '?coupon_name=discount'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)  
        
        url = reverse('promo-code-list') + '?coupon_name=off'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)  

    def test_promo_code_filter_by_type(self):
        url = reverse('promo-code-list') + '?type=PERCENTAGE'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2) 
        
        url = reverse('promo-code-list') + '?type=FIXED'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1) 

    def test_promo_code_filter_by_fixed_amount(self):
        url = reverse('promo-code-list') + '?fixed_amount__gte=10'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)  
        
        url = reverse('promo-code-list') + '?fixed_amount__lte=10'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2) 

    def test_promo_code_filter_by_dates(self):
        now = timezone.now()
        date_gte = (now - timedelta(days=7)).strftime('%Y-%m-%dT%H:%M:%S')
        date_lte = (now - timedelta(days=10)).strftime('%Y-%m-%dT%H:%M:%S')
        # Test start_at filters
        url = reverse('promo-code-list') + f'?start_at__gte={date_gte}'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1) 
        
        # Test ended_at filters
        url = reverse('promo-code-list') + f'?ended_at__lte={date_lte}'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)  

    def test_promo_code_filter_by_is_active(self):
        url = reverse('promo-code-list') + '?is_active=true'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)  
        
        url = reverse('promo-code-list') + '?is_active=false'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)  

    def test_promo_code_multiple_filters(self):
        now = timezone.now().strftime('%Y-%m-%dT%H:%M:%S')
        url = reverse('promo-code-list') + f'?type=PERCENTAGE&is_active=true&ended_at__gte={now}'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)  
