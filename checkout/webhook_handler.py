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
        # Transcript step: print the intent coming from Stripe
        intent = event["data"]["object"]
        pid = intent.get("id", "")
        print("✅ payment_intent.succeeded intent:", intent)

        metadata = intent.get("metadata") or {}
        bag_str = metadata.get("bag")

        # If metadata isn't present (or you’re mid-wiring), still return 200
        if not bag_str:
            return HttpResponse(
                content="payment_intent.succeeded received (no bag metadata).",
                status=200,
            )

        try:
            bag = json.loads(bag_str)
        except json.JSONDecodeError:
            return HttpResponse(
                content="payment_intent.succeeded received (bag metadata invalid JSON).",
                status=200,
            )

        # --- Preferred flow with your updated views.py ---
        # Your checkout POST already creates the order and sets order.stripe_pid = pid
        try:
            order = Order.objects.get(stripe_pid=pid)
            created = False
        except Order.DoesNotExist:
            order = None
            created = True

        # Optional safety net:
        # If the order doesn't exist (e.g., user closes tab after payment), create it here.
        if order is None:
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

            order = Order.objects.create(**defaults)

            # Build line items (only if we created the order here)
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

        # Email handling
        # If you have an email_sent boolean field, use it; otherwise just send once here.
        if hasattr(order, "email_sent"):
            if not order.email_sent:
                send_confirmation_email(order)
                order.email_sent = True
                order.save(update_fields=["email_sent"])
        else:
            # If you don't have email_sent, sending here may duplicate emails
            # if you already send on checkout_success. Prefer one place only.
            send_confirmation_email(order)

        return HttpResponse(
            content=f"Webhook processed payment_intent.succeeded | Order: {order.order_number} | created_in_webhook={created}",
            status=200,
        )

    def handle_payment_intent_payment_failed(self, event):
        intent = event["data"]["object"]
        pid = intent.get("id", "")
        print("❌ payment_intent.payment_failed intent:", intent)
        return HttpResponse(
            content=f"Webhook received: payment_intent.payment_failed | PI: {pid}",
            status=200,
        )
