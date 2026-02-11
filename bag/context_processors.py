from decimal import Decimal
from django.shortcuts import get_object_or_404
from products.models import Product


def bag_contents(request):
    """
    Makes bag contents available across all templates via context processors.

    Design store version:
    - Bag items are stored by license type (items_by_license)
    - Digital products => no delivery charge
    """
    bag_items = []
    total = Decimal("0.00")
    product_count = 0
    bag = request.session.get("bag", {})

    for item_id, item_data in bag.items():
        product = get_object_or_404(Product, pk=item_id)

        # Expected structure:
        # bag[item_id] = {"items_by_license": {"personal": 1, "commercial": 2}}
        items_by_license = item_data.get("items_by_license", {})

        for license_type, quantity in items_by_license.items():
            quantity = int(quantity)
            line_total = product.price * quantity

            total += line_total
            product_count += quantity

            bag_items.append({
                "item_id": item_id,
                "quantity": quantity,
                "product": product,
                "license_type": license_type,
                "line_total": line_total,
            })

    # Digital store: no delivery / shipping
    delivery = Decimal("0.00")
    free_delivery_delta = Decimal("0.00")
    free_delivery_threshold = Decimal("0.00")
    grand_total = total

    context = {
        "bag_items": bag_items,
        "total": total,
        "product_count": product_count,
        "delivery": delivery,
        "free_delivery_delta": free_delivery_delta,
        "free_delivery_threshold": free_delivery_threshold,
        "grand_total": grand_total,
    }

    return context
