from decimal import Decimal
from django.conf import settings
from django.shortcuts import get_object_or_404
from products.models import Product


def bag_contents(request):
    bag_items = []
    total = Decimal("0.00")
    product_count = 0
    bag = request.session.get("bag", {})

    for item_id, item_data in bag.items():
        product = get_object_or_404(Product, pk=item_id)

        # No sizes: item_data is an int quantity
        if isinstance(item_data, int):
            quantity = item_data
            line_total = quantity * product.price

            total += line_total
            product_count += quantity

            bag_items.append({
                "item_id": item_id,
                "quantity": quantity,
                "product": product,
                "line_total": line_total,
            })

        # Sizes: item_data is a dict of items_by_size
        else:
            for size, quantity in item_data["items_by_size"].items():
                line_total = quantity * product.price

                total += line_total
                product_count += quantity

                bag_items.append({
                    "item_id": item_id,
                    "quantity": quantity,
                    "product": product,
                    "size": size,
                    "line_total": line_total,
                })

    if total < settings.FREE_DELIVERY_THRESHOLD:
        delivery = total * Decimal(settings.STANDARD_DELIVERY_PERCENTAGE / 100)
        free_delivery_delta = settings.FREE_DELIVERY_THRESHOLD - total
    else:
        delivery = Decimal("0.00")
        free_delivery_delta = Decimal("0.00")

    grand_total = total + delivery

    return {
        "bag_items": bag_items,
        "total": total,
        "product_count": product_count,
        "delivery": delivery,
        "free_delivery_delta": free_delivery_delta,
        "free_delivery_threshold": settings.FREE_DELIVERY_THRESHOLD,
        "grand_total": grand_total,
    }
