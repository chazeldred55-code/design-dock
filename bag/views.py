from django.shortcuts import render, redirect, get_object_or_404, reverse
from django.contrib import messages
from django.http import HttpResponse
from products.models import Product


def view_bag(request):
    """Render the bag contents page."""
    return render(request, "bag/bag.html")


def add_to_bag(request, item_id):
    """Add a quantity of the specified product + license type to the shopping bag."""
    product = get_object_or_404(Product, pk=item_id)
    quantity = int(request.POST.get("quantity", 1))
    redirect_url = request.POST.get("redirect_url", reverse("products"))

    # For Design Dock: license type replaces "size"
    license_type = request.POST.get("license_type", "personal")

    bag = request.session.get("bag", {})

    if item_id in bag:
        if license_type in bag[item_id]["items_by_license"]:
            bag[item_id]["items_by_license"][license_type] += quantity
            messages.success(
                request,
                f"Updated {product.name} ({license_type.title()} license) quantity to "
                f"{bag[item_id]['items_by_license'][license_type]}."
            )
        else:
            bag[item_id]["items_by_license"][license_type] = quantity
            messages.success(
                request,
                f"Added {product.name} ({license_type.title()} license) to your bag."
            )
    else:
        bag[item_id] = {"items_by_license": {license_type: quantity}}
        messages.success(
            request,
            f"Added {product.name} ({license_type.title()} license) to your bag."
        )

    request.session["bag"] = bag
    return redirect(redirect_url)


def adjust_bag(request, item_id):
    """Adjust the quantity of the specified product/license to the specified amount."""
    product = get_object_or_404(Product, pk=item_id)
    quantity = int(request.POST.get("quantity", 1))
    license_type = request.POST.get("license_type", "personal")

    bag = request.session.get("bag", {})

    if item_id not in bag or "items_by_license" not in bag[item_id]:
        messages.error(request, "That item isn't in your bag.")
        return redirect(reverse("view_bag"))

    if quantity > 0:
        bag[item_id]["items_by_license"][license_type] = quantity
        messages.success(
            request,
            f"Updated {product.name} ({license_type.title()} license) quantity to {quantity}."
        )
    else:
        bag[item_id]["items_by_license"].pop(license_type, None)
        messages.success(
            request,
            f"Removed {product.name} ({license_type.title()} license) from your bag."
        )

        if not bag[item_id]["items_by_license"]:
            bag.pop(item_id, None)

    request.session["bag"] = bag
    return redirect(reverse("view_bag"))


def remove_from_bag(request, item_id):
    """
    Remove an item/license from the bag.
    Designed to be called via AJAX and return HTTP 200 on success.
    """
    product = get_object_or_404(Product, pk=item_id)
    bag = request.session.get("bag", {})
    license_type = request.POST.get("license_type", "personal")

    try:
        if item_id in bag and "items_by_license" in bag[item_id]:
            bag[item_id]["items_by_license"].pop(license_type, None)

            if not bag[item_id]["items_by_license"]:
                bag.pop(item_id, None)

            messages.success(
                request,
                f"Removed {product.name} ({license_type.title()} license) from your bag."
            )

        request.session["bag"] = bag
        return HttpResponse(status=200)

    except Exception:
        return HttpResponse(status=500)
