from django.shortcuts import render, redirect, reverse
from django.contrib import messages
from django.conf import settings

import stripe

from .forms import OrderForm
from bag.context_processors import bag_contents  # <-- adjust if your function lives elsewhere


def checkout(request):
    """
    A view to return the checkout page (and create a Stripe PaymentIntent)
    """
    stripe.api_key = settings.STRIPE_SECRET_KEY

    bag = request.session.get("bag", {})

    if not bag:
        messages.error(request, "There's nothing in your bag at the moment")
        return redirect(reverse("products"))

    order_form = OrderForm()

    # Use the bag context helper to get totals
    current_bag = bag_contents(request)
    grand_total = current_bag["grand_total"]
    stripe_total = round(grand_total * 100)  # pounds -> pence

    try:
        intent = stripe.PaymentIntent.create(
            amount=stripe_total,
            currency=settings.STRIPE_CURRENCY,
        )
    except Exception:
        messages.error(
            request,
            "Sorry, there was an issue processing your payment. Please try again later."
        )
        intent = None

    template = "checkout/checkout.html"
    context = {
        "order_form": order_form,
        "stripe_public_key": settings.STRIPE_PUBLIC_KEY,
        "client_secret": intent.client_secret if intent else "",
    }

    return render(request, template, context)
