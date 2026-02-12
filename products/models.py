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
    """
    Digital design product.

    Key point:
    - License is chosen per purchase (stored in bag + OrderLineItem),
      so Product should NOT store a fixed license_type.
    - Pricing can vary by license (personal/commercial/extended).
    """
    category = models.ForeignKey(
        "Category",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="products",
    )

    sku = models.CharField(max_length=254, null=True, blank=True)
    name = models.CharField(max_length=254)
    description = models.TextField()

    # Per-license pricing
    price_personal = models.DecimalField(max_digits=6, decimal_places=2)
    price_commercial = models.DecimalField(max_digits=6, decimal_places=2)
    price_extended = models.DecimalField(max_digits=6, decimal_places=2)

    rating = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)

    image_url = models.URLField(max_length=1024, null=True, blank=True)
    image = models.ImageField(null=True, blank=True)

    # Digital delivery fields
    is_digital = models.BooleanField(default=True)
    file = models.FileField(upload_to="digital_products/", null=True, blank=True)
    download_url = models.URLField(max_length=1024, null=True, blank=True)

    def __str__(self):
        return self.name

    def get_price_for_license(self, license_type: str):
        """
        Return the correct price based on the chosen license type.
        Defaults to personal if unknown.
        """
        license_type = (license_type or "personal").lower()

        if license_type == "commercial":
            return self.price_commercial
        if license_type == "extended":
            return self.price_extended
        return self.price_personal
