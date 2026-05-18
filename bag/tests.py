from decimal import Decimal
from django.test import TestCase, Client
from products.models import Category, Product


class BagViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.category = Category.objects.create(name='templates')
        self.product = Product.objects.create(
            name='Test Product',
            category=self.category,
            price_personal=Decimal('10.00'),
        )

    def test_view_empty_bag(self):
        response = self.client.get('/bag/')
        self.assertEqual(response.status_code, 200)

    def test_add_to_bag(self):
        response = self.client.post(
            f'/bag/add/{self.product.id}/',
            {
                'quantity': 1,
                'redirect_url': '/products/',
                'license_type': 'personal'
            },
        )
        self.assertEqual(response.status_code, 302)
        bag = self.client.session.get('bag', {})
        self.assertIn(str(self.product.id), bag)