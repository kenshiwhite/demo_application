from django.test import TestCase
from rest_framework.test import APIClient

from catalog.models import Product
from product_requests.models import ProductRequest
from users.models import BusinessClient, User


class ProductRequestCreationTests(TestCase):
    def setUp(self):
        self.supplier = User.objects.create_user(
            username='supplier',
            password='password',
            role=User.Role.SUPPLIER,
            is_phone_verified=True,
        )
        self.business_client = BusinessClient.objects.create(
            supplier=self.supplier,
            name='CRM Client',
            address='Almaty',
        )
        self.product = Product.objects.create(
            supplier=self.supplier,
            name='Product',
            price='100.00',
            unit='pcs',
            stock_quantity=5,
        )
        self.client = APIClient()
        self.client.force_authenticate(self.supplier)

    def test_supplier_can_create_request_for_business_client(self):
        response = self.client.post(
            '/api/requests/',
            {
                'business_client_id': self.business_client.id,
                'items': [{'product_id': self.product.id, 'quantity': 2}],
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        request = ProductRequest.objects.get()
        self.assertIsNone(request.client)
        self.assertEqual(request.business_client, self.business_client)
        self.assertEqual(request.supplier, self.supplier)
