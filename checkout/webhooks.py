import stripe

from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

from .webhook_handler import StripeWH_Handler


@csrf_exempt
def webhook(request):
    """
    Receive Stripe webhooks and route them to the correct handler.
    Enforces signature verification (no silent bypass).
    """
    stripe.api_key = settings.STRIPE_SECRET_KEY

    payload = request.body  # raw bytes (required for signature verification)
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")

    # Use the canonical setting (mapped in settings.py for backwards compatibility)
    wh_secret = getattr(settings, "STRIPE_WEBHOOK_SECRET", "") or getattr(settings, "STRIPE_WH_SECRET", "")

    if not wh_secret:
        # Fail loudly so you don't accidentally accept unverified webhooks
        return HttpResponse("STRIPE_WEBHOOK_SECRET is not set", status=500)

    try:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=sig_header,
            secret=wh_secret,
        )
    except ValueError:
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError:
        return HttpResponse(status=400)
    except Exception as e:
        return HttpResponse(content=str(e), status=400)

    handler = StripeWH_Handler(request)

    event_map = {
        "payment_intent.succeeded": handler.handle_payment_intent_succeeded,
        "payment_intent.payment_failed": handler.handle_payment_intent_payment_failed,
        # Add this if you intend to test with: stripe trigger checkout.session.completed
        "checkout.session.completed": getattr(handler, "handle_checkout_session_completed", handler.handle_event),
    }

    event_type = event["type"]
    event_handler = event_map.get(event_type, handler.handle_event)

    return event_handler(event)
