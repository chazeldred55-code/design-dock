from django.test import TestCase
from django.urls import reverse
from .models import Product, Category
from decimal import Decimal


class ProductTests(TestCase):

    def setUp(self):
        self.category = Category.objects.create(name="Test Category")

    def test_product_creation(self):
        product = Product.objects.create(
            name="Test Product",
            category=self.category,
            price_personal=Decimal("10.00"),
            price_commercial=Decimal("20.00"),
            price_extended=Decimal("30.00"),
        )
        self.assertEqual(product.name, "Test Product")
        self.assertEqual(product.price_personal, Decimal("10.00"))

    def test_products_page_loads(self):
        response = self.client.get(reverse('products'))
        self.assertEqual(response.status_code, 200)