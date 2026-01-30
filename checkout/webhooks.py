import stripe

from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt

from .webhook_handler import StripeWH_Handler


@require_POST
@csrf_exempt
def webhook(request):
    """
    Listen for Stripe webhooks and route them to the correct handler.
    """
    stripe.api_key = settings.STRIPE_SECRET_KEY
    wh_secret = settings.STRIPE_WH_SECRET

    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")
    event = None

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
        # Generic exception handler (per transcript)
        return HttpResponse(content=str(e), status=400)

    # Instantiate handler
    handler = StripeWH_Handler(request)

    # Map event types to handler methods
    event_map = {
        "payment_intent.succeeded": handler.handle_payment_intent_succeeded,
        "payment_intent.payment_failed": handler.handle_payment_intent_payment_failed,
    }

    # Get the correct handler or fall back to generic handler
    event_type = event["type"]
    event_handler = event_map.get(event_type, handler.handle_event)

    return event_handler(event)
