from django.contrib import admin
from .models import Product, Category


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("friendly_name", "name")
    ordering = ("friendly_name", "name")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "sku",
        "category",
        "price_personal",
        "price_commercial",
        "price_extended",
        "is_digital",
    )

    list_display_links = ("name",)

    list_filter = ("category", "is_digital")
    search_fields = ("name", "sku", "description")
    ordering = ("name",)