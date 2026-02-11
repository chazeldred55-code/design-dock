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
        "Category",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="products",
    )

    sku = models.CharField(max_length=254, null=True, blank=True)
    name = models.CharField(max_length=254)
    description = models.TextField()

    price = models.DecimalField(max_digits=6, decimal_places=2)
    rating = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)

    image_url = models.URLField(max_length=1024, null=True, blank=True)
    image = models.ImageField(null=True, blank=True)

    # Digital store fields
    is_digital = models.BooleanField(default=True)
    file = models.FileField(upload_to="digital_products/", null=True, blank=True)
    download_url = models.URLField(max_length=1024, null=True, blank=True)

    # Replace sizes with license type
    license_type = models.CharField(
        max_length=20,
        choices=LICENSE_CHOICES,
        default="personal",
    )

    def __str__(self):
        return self.name
