from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from checkout.models import Order
from .forms import UserProfileForm
from .models import UserProfile


@login_required
def profile(request):
    profile = UserProfile.objects.get(user=request.user)

    if request.method == "POST":
        form = UserProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully")
            form = UserProfileForm(instance=profile)
        else:
            messages.error(request, "Update failed. Please ensure the form is valid.")
    else:
        form = UserProfileForm(instance=profile)

    orders = profile.orders.all().order_by("-date")

    context = {
        "form": form,
        "orders": orders,
        "profile": profile,
    }
    return render(request, "profiles/profile.html", context)


@login_required
def order_history(request, order_number):
    order = Order.objects.get(order_number=order_number)

    messages.info(
        request,
        (
            f"This is a past confirmation for order number {order_number}. "
            "A confirmation email was sent on the order date."
        ),
    )

    context = {
        "order": order,
        "from_profile": True,
    }

    return render(request, "checkout/checkout_success.html", context)
