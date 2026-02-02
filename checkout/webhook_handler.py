import json

from django.http import HttpResponse

from products.models import Product
from .models import Order, OrderLineItem
from .utils import send_confirmation_email


class StripeWH_Handler:
    """Handle Stripe webhooks."""

    def __init__(self, request):
        self.request = request

    def handle_event(self, event):
        return HttpResponse(
            content=f"Unhandled webhook received: {event['type']}",
            status=200,
        )

    def handle_payment_intent_succeeded(self, event):
        intent = event["data"]["object"]
        pid = intent["id"]

        metadata = intent.get("metadata") or {}
        bag_str = metadata.get("bag")

        if not bag_str:
            return HttpResponse(
                content="payment_intent.succeeded but no bag metadata found.",
                status=200,
            )

        try:
            bag = json.loads(bag_str)
        except json.JSONDecodeError:
            return HttpResponse(
                content="payment_intent.succeeded but bag metadata invalid JSON.",
                status=200,
            )

        shipping = intent.get("shipping") or {}
        address = shipping.get("address") or {}

        email = intent.get("receipt_email") or ""
        if not email:
            charges = (intent.get("charges") or {}).get("data", [])
            if charges:
                billing_details = charges[0].get("billing_details") or {}
                email = billing_details.get("email") or ""

        defaults = {
            "full_name": shipping.get("name") or "",
            "email": email,
            "phone_number": shipping.get("phone") or "",
            "country": address.get("country") or "",
            "postcode": address.get("postal_code") or "",
            "town_or_city": address.get("city") or "",
            "street_address1": address.get("line1") or "",
            "street_address2": address.get("line2") or "",
            "county": address.get("state") or "",
            "original_bag": json.dumps(bag),
            "stripe_pid": pid,
        }

        # ✅ Idempotent: safe on Stripe retries
        order, created = Order.objects.get_or_create(
            stripe_pid=pid,
            defaults=defaults,
        )

        if created:
            for item_id, item_data in bag.items():
                try:
                    product_id = int(item_id)
                except (TypeError, ValueError):
                    continue

                try:
                    product = Product.objects.get(id=product_id)
                except Product.DoesNotExist:
                    continue

                if isinstance(item_data, int):
                    OrderLineItem.objects.create(
                        order=order,
                        product=product,
                        quantity=item_data,
                    )
                else:
                    for size, quantity in (item_data.get("items_by_size") or {}).items():
                        OrderLineItem.objects.create(
                            order=order,
                            product=product,
                            quantity=quantity,
                            product_size=size,
                        )

        # Email once
        if hasattr(order, "email_sent"):
            if not order.email_sent:
                send_confirmation_email(order)
                order.email_sent = True
                order.save(update_fields=["email_sent"])
        else:
            send_confirmation_email(order)

        return HttpResponse(
            content=f"Webhook processed payment_intent.succeeded | Order: {order.order_number} | created={created}",
            status=200,
        )

    def handle_payment_intent_payment_failed(self, event):
        intent = event["data"]["object"]
        pid = intent.get("id", "")
        return HttpResponse(
            content=f"Webhook received: payment_intent.payment_failed | PI: {pid}",
            status=200,
        )
