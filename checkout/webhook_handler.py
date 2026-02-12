# checkout/webhook_handler.py

import json
import time
from decimal import Decimal

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
        """Send confirmation email safely (no webhook crash if email fails)."""
        try:
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
                [order.email],
            )
        except Exception:
            pass

    def handle_event(self, event):
        """Handle unknown/unexpected webhook events."""
        return HttpResponse(
            content=f"Unhandled webhook received: {event['type']}",
            status=200,
        )

    def handle_payment_intent_succeeded(self, event):
        intent = event["data"]["object"]
        pid = intent.get("id", "")

        metadata = intent.get("metadata") or {}
        bag_str = metadata.get("bag", "")
        save_info = (metadata.get("save_info") or "").lower()
        username = metadata.get("username", "")

        if not bag_str:
            return HttpResponse(
                content="payment_intent.succeeded received (no bag metadata).",
                status=200,
            )

        try:
            bag = json.loads(bag_str)
        except json.JSONDecodeError:
            return HttpResponse(
                content="payment_intent.succeeded received (invalid bag JSON).",
                status=200,
            )

        # -------------------------
        # Profile (optional)
        # -------------------------
        profile = None
        if username and username not in ("anonymous", "AnonymousUser"):
            try:
                profile = UserProfile.objects.get(user__username=username)
            except UserProfile.DoesNotExist:
                profile = None

        # -------------------------
        # Billing (shipping may be missing for digital)
        # -------------------------
        charges = (intent.get("charges") or {}).get("data", [])
        billing_details = (charges[0].get("billing_details") if charges else {}) or {}

        shipping = intent.get("shipping") or {}
        address = shipping.get("address") or {}

        # Prefer receipt_email, then billing email, then metadata username
        email = intent.get("receipt_email") or billing_details.get("email") or ""
        full_name = shipping.get("name") or billing_details.get("name") or ""

        # Amount comes in cents/pence
        grand_total = Decimal(intent.get("amount", 0)) / Decimal("100")

        # Normalise empty strings
        for k in ("line1", "line2", "city", "state", "postal_code", "country"):
            if address.get(k) == "":
                address[k] = None
        if shipping.get("phone") == "":
            shipping["phone"] = None

        # -------------------------
        # Update profile defaults (optional)
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
        # Attempt to find existing order
        # -------------------------
        order = None
        attempt = 1

        while attempt <= 5:
            try:
                order = Order.objects.get(
                    full_name__iexact=full_name,
                    email__iexact=email,
                    grand_total=grand_total,
                    original_bag=bag_str,
                    stripe_pid=pid,
                )
                break
            except Order.DoesNotExist:
                attempt += 1
                time.sleep(1)

        if order:
            if profile and not order.user_profile:
                order.user_profile = profile
                order.save(update_fields=["user_profile"])

            if hasattr(order, "email_sent"):
                if not order.email_sent:
                    self._send_confirmation_email(order)
                    order.email_sent = True
                    order.save(update_fields=["email_sent"])
            else:
                self._send_confirmation_email(order)

            return HttpResponse(
                content=f"Webhook verified: existing order {order.order_number}",
                status=200,
            )

        # -------------------------
        # Otherwise create order
        # -------------------------
        try:
            order = Order.objects.create(
                user_profile=profile,
                full_name=full_name,
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
                grand_total=grand_total,
            )

            # bag uses items_by_license
            for item_id, item_data in (bag or {}).items():
                product = Product.objects.get(id=int(item_id))

                items_by_license = (item_data or {}).get("items_by_license", {})
                for license_type, quantity in items_by_license.items():
                    OrderLineItem.objects.create(
                        order=order,
                        product=product,
                        quantity=int(quantity),
                        license_type=(license_type or "personal").lower(),
                    )

        except Exception as e:
            if order:
                order.delete()
            return HttpResponse(
                content=f"Webhook error creating order: {e}",
                status=500,
            )

        # Send confirmation once
        if hasattr(order, "email_sent"):
            if not order.email_sent:
                self._send_confirmation_email(order)
                order.email_sent = True
                order.save(update_fields=["email_sent"])
        else:
            self._send_confirmation_email(order)

        return HttpResponse(
            content=f"Webhook verified: created order {order.order_number}",
            status=200,
        )

    def handle_payment_intent_payment_failed(self, event):
        intent = event["data"]["object"]
        pid = intent.get("id", "")
        return HttpResponse(
            content=f"Webhook received: payment_intent.payment_failed | PI: {pid}",
            status=200,
        )
