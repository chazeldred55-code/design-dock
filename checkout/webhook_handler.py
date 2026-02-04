# checkout/webhook_handler.py

import json
import time

from django.conf import settings
from django.core.mail import send_mail
from django.http import HttpResponse
from django.template.loader import render_to_string

from products.models import Product
from profiles.models import UserProfile

from .models import Order, OrderLineItem


class StripeWH_Handler:
    """Handle Stripe webhooks."""

    def __init__(self, request):
        self.request = request

    def _send_confirmation_email(self, order):
        """
        Send the user a confirmation email.
        Uses text templates in checkout/templates/checkout/.
        """
        cust_email = order.email

        subject = render_to_string(
            "checkout/confirmation_email_subject.txt",
            {"order": order},
        ).strip()

        body = render_to_string(
            "checkout/confirmation_email_body.txt",
            {
                "order": order,
                "contact_email": settings.DEFAULT_FROM_EMAIL,
            },
        )

        send_mail(
            subject,
            body,
            settings.DEFAULT_FROM_EMAIL,
            [cust_email],
        )

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
        - Read bag + save_info + username from PaymentIntent metadata.
        - Normalise Stripe shipping details ("" -> None).
        - Resolve UserProfile (optional for anonymous checkout).
        - If save_info is true, update profile default delivery info.
        - Try up to 5 times over ~5 seconds to find an existing Order
          created by the normal checkout POST (avoids duplicates).
        - Match on customer details + grand_total + original_bag + stripe_pid.
        - If still not found, create the Order + lineitems from the bag metadata.
        - Attach user_profile to the order when available.
        - Send confirmation email once (guarded by Order.email_sent if present).
        """
        intent = event["data"]["object"]
        pid = intent.get("id", "")

        # -------------------------
        # Metadata (bag, save_info, username)
        # -------------------------
        metadata = intent.get("metadata") or {}
        bag_str = metadata.get("bag", "")
        save_info = metadata.get("save_info", "")
        username = metadata.get("username", "")

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

        # -------------------------
        # Profile (optional)
        # -------------------------
        profile = None
        if username and username != "AnonymousUser":
            try:
                profile = UserProfile.objects.get(user__username=username)
            except UserProfile.DoesNotExist:
                profile = None

        # -------------------------
        # Pull billing + shipping + totals from the PaymentIntent
        # -------------------------
        charges = (intent.get("charges") or {}).get("data", [])
        billing_details = (charges[0].get("billing_details") if charges else {}) or {}

        shipping = intent.get("shipping") or {}
        address = shipping.get("address") or {}

        # Stripe amount is in cents/pence; convert to pounds/dollars etc.
        grand_total = round((intent.get("amount") or 0) / 100, 2)

        # Email: try receipt_email first, then billing_details.email
        email = intent.get("receipt_email") or billing_details.get("email") or ""

        # Normalise Stripe blanks to None where appropriate
        for k in ("line1", "line2", "city", "state", "postal_code", "country"):
            if address.get(k) == "":
                address[k] = None
        if shipping.get("phone") == "":
            shipping["phone"] = None

        # -------------------------
        # Update profile defaults (if requested)
        # -------------------------
        if profile and save_info == "true":
            profile.default_phone_number = shipping.get("phone")
            profile.default_country = address.get("country")
            profile.default_postcode = address.get("postal_code")
            profile.default_town_or_city = address.get("city")
            profile.default_street_address1 = address.get("line1")
            profile.default_street_address2 = address.get("line2")
            profile.default_county = address.get("state")
            profile.save()

        # -------------------------
        # Attempt to find an existing order (avoid duplicates)
        # -------------------------
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

        if order_exists:
            # Safety net: attach profile if missing
            if profile and getattr(order, "user_profile_id", None) is None:
                order.user_profile = profile
                order.save(update_fields=["user_profile"])

            # Send email once (guarded)
            if hasattr(order, "email_sent"):
                if not order.email_sent:
                    self._send_confirmation_email(order)
                    order.email_sent = True
                    order.save(update_fields=["email_sent"])
            else:
                self._send_confirmation_email(order)

            return HttpResponse(
                content=(
                    "Webhook received: payment_intent.succeeded | "
                    f"VERIFIED order exists | Order: {order.order_number}"
                ),
                status=200,
            )

        # -------------------------
        # Otherwise create the order here in the webhook
        # -------------------------
        created_order = None

        try:
            created_order = Order.objects.create(
                user_profile=profile,
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

        except Exception as e:
            if created_order:
                created_order.delete()
            return HttpResponse(
                content=(
                    "Webhook received: payment_intent.succeeded | "
                    f"ERROR creating order: {e}"
                ),
                status=500,
            )

        # Send confirmation email once (guarded)
        if hasattr(created_order, "email_sent"):
            if not created_order.email_sent:
                self._send_confirmation_email(created_order)
                created_order.email_sent = True
                created_order.save(update_fields=["email_sent"])
        else:
            self._send_confirmation_email(created_order)

        return HttpResponse(
            content=(
                "Webhook received: payment_intent.succeeded | "
                f"CREATED order in webhook handler | Order: {created_order.order_number} | "
                f"save_info={save_info}"
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
