import json
from decimal import Decimal

import stripe
from django.conf import settings
from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render, reverse
from django.views.decorators.http import require_POST

from bag.context_processors import bag_contents
from products.models import Product
from profiles.forms import UserProfileForm
from profiles.models import UserProfile

from .forms import OrderForm
from .models import Order, OrderLineItem


@require_POST
def cache_checkout_data(request):
    """
    Store metadata on the PaymentIntent so Stripe webhooks can read it.
    Called from stripe_elements.js BEFORE confirmCardPayment.
    """
    try:
        client_secret = request.POST.get("client_secret", "")
        if "_secret" not in client_secret:
            return HttpResponse(content="Missing client_secret", status=400)

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
        messages.error(
            request,
            "Sorry, your payment cannot be processed right now. Please try again later.",
        )
        return HttpResponse(content=str(e), status=400)


def checkout(request):
    """
    GET:
      - Render checkout page + create PaymentIntent
    POST:
      - Create Order + line items, then redirect to checkout_success (order_number)

    Design store updates:
      - Bag uses items_by_license
      - OrderLineItem stores license_type
      - Digital store: delivery is 0
    """
    stripe.api_key = settings.STRIPE_SECRET_KEY

    bag = request.session.get("bag", {})
    if not bag:
        messages.error(request, "There's nothing in your bag at the moment")
        return redirect(reverse("products"))

    current_bag = bag_contents(request)
    grand_total = Decimal(str(current_bag["grand_total"]))
    stripe_total = int((grand_total * 100).quantize(Decimal("1")))

    if request.method == "POST":
        form_data = {
            "full_name": request.POST.get("full_name"),
            "email": request.POST.get("email"),
            "phone_number": request.POST.get("phone_number"),
            "country": request.POST.get("country"),
            "postcode": request.POST.get("postcode"),
            "town_or_city": request.POST.get("town_or_city"),
            "street_address1": request.POST.get("street_address1"),
            "street_address2": request.POST.get("street_address2"),
            "county": request.POST.get("county"),
        }

        order_form = OrderForm(form_data)

        if order_form.is_valid():
            order = order_form.save(commit=False)

            client_secret = request.POST.get("client_secret", "")
            if "_secret" not in client_secret:
                messages.error(request, "Payment reference missing. Please try again.")
                return redirect(reverse("checkout"))

            pid = client_secret.split("_secret")[0]
            order.stripe_pid = pid
            order.original_bag = json.dumps(bag)
            order.save()

            # Create line items from items_by_license
            for item_id, item_data in bag.items():
                product = get_object_or_404(Product, pk=item_id)

                items_by_license = (item_data or {}).get("items_by_license", {})
                for license_type, quantity in items_by_license.items():
                    OrderLineItem.objects.create(
                        order=order,
                        product=product,
                        quantity=int(quantity),
                        license_type=(license_type or "personal").lower(),
                    )

            save_info = request.POST.get("save_info")
            request.session["save_info"] = True if save_info else False

            return redirect(reverse("checkout_success", args=[order.order_number]))

        messages.error(
            request,
            "There was an error with your form. Please double check your information.",
        )

    # GET (or POST invalid): prefill form for logged-in users
    if request.user.is_authenticated:
        profile = get_object_or_404(UserProfile, user=request.user)
        order_form = OrderForm(initial={
            "full_name": request.user.get_full_name(),
            "email": request.user.email,
            "phone_number": profile.default_phone_number,
            "country": profile.default_country,
            "postcode": profile.default_postcode,
            "town_or_city": profile.default_town_or_city,
            "street_address1": profile.default_street_address1,
            "street_address2": profile.default_street_address2,
            "county": profile.default_county,
        })
    else:
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


def checkout_success(request, order_number):
    """
    Success page shown after the Order is created.
    Clears the bag and shows order info.
    """
    save_info = request.session.get("save_info")
    order = get_object_or_404(Order, order_number=order_number)

    if request.user.is_authenticated:
        profile = get_object_or_404(UserProfile, user=request.user)
        if not order.user_profile:
            order.user_profile = profile
            order.save(update_fields=["user_profile"])

        if save_info:
            profile_data = {
                "default_phone_number": order.phone_number,
                "default_country": order.country,
                "default_postcode": order.postcode,
                "default_town_or_city": order.town_or_city,
                "default_street_address1": order.street_address1,
                "default_street_address2": order.street_address2,
                "default_county": order.county,
            }

            user_profile_form = UserProfileForm(profile_data, instance=profile)
            if user_profile_form.is_valid():
                user_profile_form.save()

    request.session.pop("bag", None)

    messages.success(
        request,
        f"Order successfully processed! Your order number is {order_number}. "
        f"A confirmation email will be sent to {order.email}.",
    )

    return render(request, "checkout/checkout_success.html", {"order": order})
