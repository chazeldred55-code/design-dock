from django.shortcuts import render, redirect, reverse
from django.contrib import messages
from django.conf import settings

import stripe

from .forms import OrderForm
from bag.context_processors import bag_contents


# Stripe keys (pulled from settings once)
STRIPE_PUBLIC_KEY = settings.STRIPE_PUBLIC_KEY
STRIPE_SECRET_KEY = settings.STRIPE_SECRET_KEY


def checkout(request):
    """
    Display the checkout page and create a Stripe PaymentIntent
    """
    # --------------------
    # Bag check
    # --------------------
    bag = request.session.get("bag", {})
    if not bag:
        messages.error(request, "There's nothing in your bag at the moment")
        return redirect(reverse("products"))

    # --------------------
    # Bag totals (use bag context processor)
    # --------------------
    current_bag = bag_contents(request)
    grand_total = current_bag["grand_total"]
    stripe_total = round(grand_total * 100)  # GBP -> pence (int)

    # --------------------
    # Stripe setup + PaymentIntent
    # --------------------
    client_secret = ""
    if not STRIPE_PUBLIC_KEY:
        messages.warning(
            request,
            "Stripe public key is missing. Did you forget to set it in your environment?"
        )

    try:
        stripe.api_key = STRIPE_SECRET_KEY

        intent = stripe.PaymentIntent.create(
            amount=stripe_total,
            currency=settings.STRIPE_CURRENCY,
        )
        client_secret = intent.client_secret

    except Exception:
        messages.error(
            request,
            "Sorry, there was an issue processing your payment. Please try again."
        )

    # --------------------
    # Handle form
    # --------------------
    if request.method == "POST":
        order_form = OrderForm(request.POST)
        if order_form.is_valid():
            # Order saving comes later (after webhook)
            messages.success(request, "Order form submitted successfully.")
        else:
            messages.error(request, "Please check the form and try again.")
    else:
        order_form = OrderForm()

    # --------------------
    # Context
    # --------------------
    context = {
        "order_form": order_form,
        "stripe_public_key": STRIPE_PUBLIC_KEY,
        "client_secret": client_secret,

        # Bag context for template
        "bag_items": current_bag["bag_items"],
        "total": current_bag["total"],
        "delivery": current_bag["delivery"],
        "grand_total": current_bag["grand_total"],
        "product_count": current_bag["product_count"],
        "free_delivery_delta": current_bag.get("free_delivery_delta", 0),
        "free_delivery_threshold": current_bag.get("free_delivery_threshold", 0),
    }

    return render(request, "checkout/checkout.html", context)
