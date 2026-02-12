from decimal import Decimal
from django.db import models


class Category(models.Model):
    name = models.CharField(max_length=254)
    friendly_name = models.CharField(max_length=254, null=True, blank=True)

    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name

    def get_friendly_name(self):
        return self.friendly_name or self.name


class Product(models.Model):
    LICENSE_CHOICES = [
        ("personal", "Personal"),
        ("commercial", "Commercial"),
        ("extended", "Extended"),
    ]

    category = models.ForeignKey(
        Category,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="products",
    )

    sku = models.CharField(max_length=254, null=True, blank=True)
    name = models.CharField(max_length=254)
    description = models.TextField(blank=True)

    # -----------------------------
    # License-Based Pricing
    # -----------------------------
    price_personal = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal("10.00"),
    )

    price_commercial = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal("25.00"),
    )

    price_extended = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal("75.00"),
    )

    rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        null=True,
        blank=True,
    )

    # -----------------------------
    # Media
    # -----------------------------
    image_url = models.URLField(max_length=1024, null=True, blank=True)
    image = models.ImageField(upload_to="product_images/", null=True, blank=True)

    # -----------------------------
    # Digital Product Fields
    # -----------------------------
    is_digital = models.BooleanField(default=True)
    file = models.FileField(upload_to="digital_products/", null=True, blank=True)
    download_url = models.URLField(max_length=1024, null=True, blank=True)

    # -----------------------------
    # Utility Methods
    # -----------------------------
    def get_price_for_license(self, license_type: str):
        """
        Return the correct unit price for a given license type.
        Defaults to personal if missing or invalid.
        """
        lt = (license_type or "personal").lower()

        if lt == "commercial":
            return self.price_commercial
        if lt == "extended":
            return self.price_extended

        return self.price_personal

    def __str__(self):
        return self.name
