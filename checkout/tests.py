from decimal import Decimal
from django.test import TestCase
from products.models import Category, Product
from .models import Order, OrderLineItem


class OrderModelTest(TestCase):
    def test_order_number_generated(self):
        order = Order.objects.create(
            full_name='Test User',
            email='test@example.com',
            phone_number='0123456789',
            country='GB',
            town_or_city='London',
            street_address1='123 Test St',
        )
        self.assertIsNotNone(order.order_number)
        self.assertEqual(len(order.order_number), 32)

    def test_order_string_representation(self):
        order = Order.objects.create(
            full_name='Test User',
            email='test@example.com',
            phone_number='0123456789',
            country='GB',
            town_or_city='London',
            street_address1='123 Test St',
        )
        self.assertEqual(str(order), order.order_number)


class OrderLineItemTest(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name='templates')
        self.product = Product.objects.create(
            name='Test Product',
            category=self.category,
            price_personal=Decimal('10.00'),
            price_commercial=Decimal('25.00'),
            price_extended=Decimal('75.00'),
        )
        self.order = Order.objects.create(
            full_name='Test User',
            email='test@example.com',
            phone_number='0123456789',
            country='GB',
            town_or_city='London',
            street_address1='123 Test St',
        )

    def test_lineitem_total_personal(self):
        item = OrderLineItem.objects.create(
            order=self.order,
            product=self.product,
            license_type='personal',
            quantity=2,
        )
        self.assertEqual(item.lineitem_total, Decimal('20.00'))

    def test_order_total_updates(self):
        OrderLineItem.objects.create(
            order=self.order,
            product=self.product,
            license_type='personal',
            quantity=3,
        )
        self.order.refresh_from_db()
        self.assertEqual(self.order.grand_total, Decimal('30.00'))