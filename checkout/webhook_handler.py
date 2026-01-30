import json
import time

from django.http import HttpResponse

from products.models import Product
from .models import Order, OrderLineItem
from .utils import send_confirmation_email


class StripeWH_Handler:
    """Handle Stripe webhooks."""

    def __init__(self, request):
        self.request = request

    def handle_event(self, event):
        """Handle any webhook event we don't explicitly care about."""
        return HttpResponse(
            content=f"Unhandled webhook received: {event['type']}",
            status=200,
        )

    def handle_payment_intent_succeeded(self, event):
        """Handle successful payment intents."""
        intent = event["data"]["object"]
        pid = intent["id"]

        metadata = intent.get("metadata", {}) or {}
        bag_str = metadata.get("bag")

        # Give the normal checkout flow a chance to create the order first
        attempt = 1
        while attempt <= 5:
            try:
                order = Order.objects.get(stripe_pid=pid)

                # If the order exists, ensure we only send the email once
                if hasattr(order, "email_sent") and not order.email_sent:
                    send_confirmation_email(order)
                    order.email_sent = True
                    order.save(update_fields=["email_sent"])

                return HttpResponse(
                    content=(
                        "Webhook received: payment_intent.succeeded | "
                        f"Order exists: {order.order_number}"
                    ),
                    status=200,
                )
            except Order.DoesNotExist:
                attempt += 1
                time.sleep(1)

        # If no order exists, create one from webhook data
        if not bag_str:
            return HttpResponse(
                content="payment_intent.succeeded received but no bag metadata found.",
                status=200,
            )

        try:
            bag = json.loads(bag_str)
        except json.JSONDecodeError:
            return HttpResponse(
                content="payment_intent.succeeded received but bag metadata was invalid JSON.",
                status=200,
            )

        shipping = intent.get("shipping") or {}
        address = shipping.get("address") or {}

        # Best-effort email extraction (PaymentIntent may not always contain this)
        email = ""
        charges = (intent.get("charges") or {}).get("data", [])
        if charges:
            billing_details = charges[0].get("billing_details") or {}
            email = billing_details.get("email", "") or ""

        defaults = {
            "full_name": shipping.get("name", "") or "",
            "email": email,
            "phone_number": shipping.get("phone", "") or "",
            "country": address.get("country", "") or "",
            "postcode": address.get("postal_code", "") or "",
            "town_or_city": address.get("city", "") or "",
            "street_address1": address.get("line1", "") or "",
            "street_address2": address.get("line2", "") or "",
            "county": address.get("state", "") or "",
            "original_bag": json.dumps(bag),
        }

        # Idempotency: if Stripe retries the webhook, don't create a duplicate order
        order, created = Order.objects.get_or_create(
            stripe_pid=pid,
            defaults=defaults,
        )

        if created:
            # Create line items
            for item_id, item_data in bag.items():
                try:
                    product = Product.objects.get(id=item_id)
                except Product.DoesNotExist:
                    # Don't make Stripe retry forever because of bad data
                    continue

                if isinstance(item_data, int):
                    OrderLineItem.objects.create(
                        order=order,
                        product=product,
                        quantity=item_data,
                    )
                else:
                    for size, quantity in item_data.get("items_by_size", {}).items():
                        OrderLineItem.objects.create(
                            order=order,
                            product=product,
                            quantity=quantity,
                            product_size=size,
                        )

        # Send confirmation email ONCE
        if hasattr(order, "email_sent"):
            if not order.email_sent:
                send_confirmation_email(order)
                order.email_sent = True
                order.save(update_fields=["email_sent"])
        else:
            # Fallback if you don't actually have the field yet
            send_confirmation_email(order)

        return HttpResponse(
            content=(
                f"Webhook processed payment_intent.succeeded | "
                f"Order: {order.order_number} | created={created}"
            ),
            status=200,
        )

    def handle_payment_intent_payment_failed(self, event):
        """Handle failed payment intents."""
        intent = event["data"]["object"]
        pid = intent.get("id", "")

        return HttpResponse(
            content=f"Webhook received: payment_intent.payment_failed | PI: {pid}",
            status=200,
        )
