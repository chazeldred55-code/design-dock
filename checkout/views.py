import json
import stripe

from django.conf import settings
from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import render, redirect, reverse, get_object_or_404
from django.views.decorators.http import require_POST

from bag.context_processors import bag_contents
from .forms import OrderForm
from .models import Order


@require_POST
def cache_checkout_data(request):
    """
    Store metadata on the PaymentIntent so Stripe webhooks can create the Order.
    Called from stripe_elements.js BEFORE confirmCardPayment.
    """
    try:
        client_secret = request.POST.get("client_secret", "")
        pid = client_secret.split("_secret")[0]

        stripe.api_key = settings.STRIPE_SECRET_KEY

        stripe.PaymentIntent.modify(
            pid,
            metadata={
                "username": request.user.username if request.user.is_authenticated else "anonymous",
                "save_info": request.POST.get("save_info", ""),
                "bag": json.dumps(request.session.get("bag", {})),
            },
        )
        return HttpResponse(status=200)

    except Exception as e:
        return HttpResponse(content=str(e), status=400)


def checkout(request):
    """
    WEBHOOK-SOURCE-OF-TRUTH FLOW

    GET:
      - Render checkout + create PaymentIntent
    POST:
      - Do NOT create Order
      - Store save_info choice
      - Redirect to success page using pid
    """
    stripe.api_key = settings.STRIPE_SECRET_KEY

    bag = request.session.get("bag", {})
    if not bag:
        messages.error(request, "There's nothing in your bag at the moment")
        return redirect(reverse("products"))

    current_bag = bag_contents(request)
    grand_total = current_bag["grand_total"]
    stripe_total = round(grand_total * 100)

    if request.method == "POST":
        # Persist save_info choice so webhook-created order can later update profile (optional step)
        save_info = request.POST.get("save_info")
        request.session["save_info"] = True if save_info else False

        client_secret = request.POST.get("client_secret", "")
        if "_secret" not in client_secret:
            messages.error(request, "Payment reference missing. Please try again.")
            return redirect(reverse("checkout"))

        pid = client_secret.split("_secret")[0]

        # ✅ Redirect to success page by pid; webhook will create the order shortly
        return redirect(reverse("checkout_success", args=[pid]))

    # GET: show checkout + intent
    order_form = OrderForm()

    try:
        intent = stripe.PaymentIntent.create(
            amount=stripe_total,
            currency=settings.STRIPE_CURRENCY,
        )
    except Exception as e:
        print("STRIPE INTENT ERROR:", e)
        messages.error(request, "Sorry, our payment system is unavailable right now.")
        return redirect(reverse("view_bag"))

    context = {
        "order_form": order_form,
        "stripe_public_key": settings.STRIPE_PUBLIC_KEY,
        "client_secret": intent.client_secret,
    }
    return render(request, "checkout/checkout.html", context)


def checkout_success(request, pid):
    """
    Success page waits briefly for the webhook to create the Order.
    """
    # Poll for a short period to allow webhook creation
    # (Stripe/webhook can be slightly delayed)
    import time

    order = None
    for _ in range(10):  # up to ~10 seconds
        try:
            order = Order.objects.get(stripe_pid=pid)
            break
        except Order.DoesNotExist:
            time.sleep(1)

    if not order:
        messages.info(
            request,
            "Your payment was received. We're finalising your order—please refresh in a moment.",
        )
        # Render a lightweight “pending” success page; you can reuse checkout_success template
        return render(request, "checkout/checkout_success.html", {"order": None, "pid": pid})

    # Clear bag only once order exists
    request.session["bag"] = {}

    messages.success(request, f"Order successfully processed! Your order number is {order.order_number}.")
    return render(request, "checkout/checkout_success.html", {"order": order, "pid": pid})
