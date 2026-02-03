# checkout/webhook_handler.py

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
        """Handle unknown/unexpected webhook events."""
        return HttpResponse(
            content=f"Unhandled webhook received: {event['type']}",
            status=200,
        )

    def handle_payment_intent_succeeded(self, event):
        """
        Handle the payment_intent.succeeded webhook from Stripe.

        Strategy (course-aligned):
        - Read bag + save_info from PaymentIntent metadata.
        - Normalise Stripe shipping details ("" -> None).
        - Try up to 5 times over ~5 seconds to find an existing Order
          created by the normal checkout POST (avoids duplicates).
        - Match on customer details + grand_total + original_bag + stripe_pid.
        - If still not found, create the Order + lineitems from the bag metadata.
        - Send confirmation email once (guarded by Order.email_sent).
        """
        intent = event["data"]["object"]
        pid = intent.get("id", "")

        metadata = intent.get("metadata") or {}
        bag_str = metadata.get("bag", "")
        save_info = metadata.get("save_info", "")

        # If metadata isn't present (e.g. wiring / test events), return 200
        if not bag_str:
            return HttpResponse(
                content="payment_intent.succeeded received (no bag metadata).",
                status=200,
            )

        # Parse bag JSON
        try:
            bag = json.loads(bag_str)
        except json.JSONDecodeError:
            return HttpResponse(
                content="payment_intent.succeeded received (bag metadata invalid JSON).",
                status=200,
            )

        # Pull billing + shipping + totals from the PaymentIntent
        charges = (intent.get("charges") or {}).get("data", [])
        billing_details = (charges[0].get("billing_details") if charges else {}) or {}

        shipping = intent.get("shipping") or {}
        address = shipping.get("address") or {}

        # Stripe amount is in cents/pence; convert to pounds/dollars etc.
        grand_total = round((intent.get("amount") or 0) / 100, 2)

        # Email: try receipt_email first, then billing_details.email
        email = intent.get("receipt_email") or billing_details.get("email") or ""

        # Normalise Stripe blanks to None where appropriate
        # (Stripe often sends "" which isn't the same as NULL/None in DB)
        for k in ("line1", "line2", "city", "state", "postal_code", "country"):
            if address.get(k) == "":
                address[k] = None
        if shipping.get("phone") == "":
            shipping["phone"] = None

        # ---- Attempt to find an existing order (avoid duplicates) ----
        order_exists = False
        order = None
        attempt = 1

        while attempt <= 5:
            try:
                order = Order.objects.get(
                    full_name__iexact=(shipping.get("name") or ""),
                    email__iexact=email,
                    phone_number__iexact=(shipping.get("phone") or ""),
                    country__iexact=(address.get("country") or ""),
                    postcode__iexact=(address.get("postal_code") or ""),
                    town_or_city__iexact=(address.get("city") or ""),
                    street_address1__iexact=(address.get("line1") or ""),
                    street_address2__iexact=(address.get("line2") or ""),
                    county__iexact=(address.get("state") or ""),
                    grand_total=grand_total,
                    original_bag=bag_str,
                    stripe_pid=pid,
                )
                order_exists = True
                break
            except Order.DoesNotExist:
                attempt += 1
                time.sleep(1)

        # If found, we're done (order already created by checkout POST)
        if order_exists:
            # Send email once (guarded)
            if hasattr(order, "email_sent"):
                if not order.email_sent:
                    send_confirmation_email(order)
                    order.email_sent = True
                    order.save(update_fields=["email_sent"])
            else:
                send_confirmation_email(order)

            return HttpResponse(
                content=f"Webhook received: payment_intent.succeeded | VERIFIED order exists | Order: {order.order_number}",
                status=200,
            )

        # ---- Otherwise create the order here in the webhook ----
        created_in_webhook = True
        created_order = None

        try:
            created_order = Order.objects.create(
                full_name=shipping.get("name") or "",
                email=email,
                phone_number=shipping.get("phone") or "",
                country=address.get("country") or "",
                postcode=address.get("postal_code") or "",
                town_or_city=address.get("city") or "",
                street_address1=address.get("line1") or "",
                street_address2=address.get("line2") or "",
                county=address.get("state") or "",
                original_bag=bag_str,
                stripe_pid=pid,
            )

            # Create line items from the bag
            for item_id, item_data in bag.items():
                try:
                    product_id = int(item_id)
                except (TypeError, ValueError):
                    continue

                product = Product.objects.get(id=product_id)

                # No size variant: item_data is int quantity
                if isinstance(item_data, int):
                    OrderLineItem.objects.create(
                        order=created_order,
                        product=product,
                        quantity=item_data,
                    )
                else:
                    # Size variant: item_data["items_by_size"] is dict
                    items_by_size = (item_data.get("items_by_size") or {})
                    for size, quantity in items_by_size.items():
                        OrderLineItem.objects.create(
                            order=created_order,
                            product=product,
                            quantity=quantity,
                            product_size=size,
                        )

            # Totals are computed by OrderLineItem.save() -> order.update_total()
            # Optional sanity check: you can compare totals if you want
            # if float(created_order.grand_total) != float(grand_total):
            #     pass

        except Exception as e:
            # If anything went wrong, delete order if it was created and return 500
            if created_order:
                created_order.delete()
            return HttpResponse(
                content=f"Webhook received: payment_intent.succeeded | ERROR creating order: {e}",
                status=500,
            )

        # Send confirmation email once
        if hasattr(created_order, "email_sent"):
            if not created_order.email_sent:
                send_confirmation_email(created_order)
                created_order.email_sent = True
                created_order.save(update_fields=["email_sent"])
        else:
            send_confirmation_email(created_order)

        return HttpResponse(
            content=(
                "Webhook received: payment_intent.succeeded | "
                f"CREATED order in webhook handler | Order: {created_order.order_number} | "
                f"created_in_webhook={created_in_webhook} | save_info={save_info}"
            ),
            status=200,
        )

    def handle_payment_intent_payment_failed(self, event):
        """Handle the payment_intent.payment_failed webhook from Stripe."""
        intent = event["data"]["object"]
        pid = intent.get("id", "")
        return HttpResponse(
            content=f"Webhook received: payment_intent.payment_failed | PI: {pid}",
            status=200,
        )
