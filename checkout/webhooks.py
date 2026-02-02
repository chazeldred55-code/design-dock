import stripe

from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

from .webhook_handler import StripeWH_Handler


@csrf_exempt
def webhook(request):
    """
    Receive Stripe webhooks and route them to the correct handler.
    """
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")
    wh_secret = getattr(settings, "STRIPE_WH_SECRET", "")

    # Allow wiring/testing if secret not yet set
    if not wh_secret:
        return HttpResponse(status=200)

    try:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=sig_header,
            secret=wh_secret,
        )
    except ValueError:
        # Invalid payload
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError:
        # Invalid signature
        return HttpResponse(status=400)
    except Exception as e:
        return HttpResponse(content=str(e), status=400)

    handler = StripeWH_Handler(request)

    event_map = {
        "payment_intent.succeeded": handler.handle_payment_intent_succeeded,
        "payment_intent.payment_failed": handler.handle_payment_intent_payment_failed,
    }

    event_type = event["type"]
    event_handler = event_map.get(event_type, handler.handle_event)

    return event_handler(event)
