import uuid
from decimal import Decimal

from django.db import models
from django.db.models import Sum
from django_countries.fields import CountryField

from products.models import Product


class Order(models.Model):
    order_number = models.CharField(max_length=32, null=False, editable=False)

    user_profile = models.ForeignKey(
        "profiles.UserProfile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
    )

    full_name = models.CharField(max_length=50, null=False, blank=False)
    email = models.EmailField(max_length=254, null=False, blank=False)
    phone_number = models.CharField(max_length=20, null=False, blank=False)

    # Keeping address fields for now to avoid breaking existing profiles/forms.
    country = CountryField(blank_label="Country *", null=False, blank=False)
    postcode = models.CharField(max_length=20, null=True, blank=True)
    town_or_city = models.CharField(max_length=40, null=False, blank=False)
    street_address1 = models.CharField(max_length=80, null=False, blank=False)
    street_address2 = models.CharField(max_length=80, null=True, blank=True)
    county = models.CharField(max_length=80, null=True, blank=True)

    stripe_pid = models.CharField(max_length=254, null=False, blank=False, default="")
    original_bag = models.TextField(null=False, blank=False, default="")

    email_sent = models.BooleanField(default=False)

    date = models.DateTimeField(auto_now_add=True)

    # Digital store: delivery always 0 (kept for compatibility)
    delivery_cost = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=False,
        default=Decimal("0.00"),
    )
    order_total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=False,
        default=Decimal("0.00"),
    )
    grand_total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=False,
        default=Decimal("0.00"),
    )

    def _generate_order_number(self):
        """Generate a random, unique order number using UUID."""
        return uuid.uuid4().hex.upper()

    def update_total(self):
        """Update totals from line items. Digital store => delivery always 0."""
        self.order_total = (
            self.lineitems.aggregate(Sum("lineitem_total"))["lineitem_total__sum"]
            or Decimal("0.00")
        )

        self.delivery_cost = Decimal("0.00")
        self.grand_total = self.order_total
        self.save(update_fields=["order_total", "delivery_cost", "grand_total"])

    def save(self, *args, **kwargs):
        """Set order number if not set."""
        if not self.order_number:
            self.order_number = self._generate_order_number()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.order_number


class OrderLineItem(models.Model):
    LICENSE_CHOICES = [
        ("personal", "Personal"),
        ("commercial", "Commercial"),
        ("extended", "Extended"),
    ]

    order = models.ForeignKey(
        Order,
        null=False,
        blank=False,
        on_delete=models.CASCADE,
        related_name="lineitems",
    )
    product = models.ForeignKey(
        Product,
        null=False,
        blank=False,
        on_delete=models.CASCADE,
    )

    license_type = models.CharField(
        max_length=20,
        choices=LICENSE_CHOICES,
        null=True,
        blank=True,
    )

    quantity = models.IntegerField(null=False, blank=False, default=0)

    lineitem_total = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=False,
        blank=False,
        editable=False,
    )

    def save(self, *args, **kwargs):
        """
        Set lineitem_total using per-license pricing, then update order totals.
        """
        license_type = self.license_type or "personal"
        unit_price = self.product.get_price_for_license(license_type)
        self.lineitem_total = unit_price * self.quantity

        super().save(*args, **kwargs)
        self.order.update_total()

    def __str__(self):
        license_label = f" ({self.license_type})" if self.license_type else ""
        return f"SKU {self.product.sku}{license_label} on order {self.order.order_number}"
