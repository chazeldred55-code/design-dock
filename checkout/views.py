import json

from django.shortcuts import render, redirect, reverse, get_object_or_404
from django.contrib import messages
from django.conf import settings

from .forms import OrderForm
from .models import Order, OrderLineItem
from products.models import Product
from bag.context_processors import bag_contents

import stripe


def checkout(request):
    stripe_public_key = settings.STRIPE_PUBLIC_KEY
    stripe_secret_key = settings.STRIPE_SECRET_KEY

    if request.method == "POST":
        bag = request.session.get("bag", {})

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
            # Save order but don't commit yet (so we can attach Stripe fields)
            order = order_form.save(commit=False)

            # Stripe PaymentIntent id (set by JS before submitting form)
            pid = request.POST.get("stripe_pid")

            # Optional safety guard: if PID missing, treat as failed/invalid checkout
            if not pid:
                messages.error(request, "Payment could not be verified. Please try again.")
                return redirect(reverse("checkout"))

            order.stripe_pid = pid

            # Store original bag for later webhook verification/recovery
            order.original_bag = json.dumps(bag)

            order.save()

            for item_id, item_data in bag.items():
                try:
                    product = Product.objects.get(id=item_id)

                    if isinstance(item_data, int):
                        OrderLineItem.objects.create(
                            order=order,
                            product=product,
                            quantity=item_data,
                        )
                    else:
                        for size, quantity in item_data["items_by_size"].items():
                            OrderLineItem.objects.create(
                                order=order,
                                product=product,
                                quantity=quantity,
                                product_size=size,
                            )
                except Product.DoesNotExist:
                    messages.error(
                        request,
                        "One of the products in your bag wasn't found in our database. "
                        "Please call us for assistance!",
                    )
                    order.delete()
                    return redirect(reverse("view_bag"))

            request.session["save_info"] = "save-info" in request.POST
            return redirect(reverse("checkout_success", args=[order.order_number]))

        messages.error(
            request,
            "There was an error with your form. Please double check your information.",
        )
        return redirect(reverse("checkout"))

    # GET request
    bag = request.session.get("bag", {})
    if not bag:
        messages.error(request, "There's nothing in your bag at the moment")
        return redirect(reverse("products"))

    current_bag = bag_contents(request)
    grand_total = current_bag["grand_total"]
    stripe_total = round(grand_total * 100)

    stripe.api_key = stripe_secret_key
    intent = stripe.PaymentIntent.create(
        amount=stripe_total,
        currency=settings.STRIPE_CURRENCY,
    )

    order_form = OrderForm()

    # Correct indentation (the video shows this wrong)
    if not stripe_public_key:
        messages.warning(
            request,
            "Stripe public key is missing. Did you forget to set it in your environment?",
        )

    template = "checkout/checkout.html"
    context = {
        "order_form": order_form,
        "stripe_public_key": stripe_public_key,
        "client_secret": intent.client_secret,
    }
    return render(request, template, context)


def checkout_success(request, order_number):
    """
    Handle successful checkouts
    """
    save_info = request.session.get("save_info")
    order = get_object_or_404(Order, order_number=order_number)

    messages.success(
        request,
        f"Order successfully processed! Your order number is {order_number}. "
        f"A confirmation email will be sent to {order.email}.",
    )

    if "bag" in request.session:
        del request.session["bag"]

    template = "checkout/checkout_success.html"
    context = {
        "order": order,
        "save_info": save_info,
    }
    return render(request, template, context)
