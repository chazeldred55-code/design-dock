/* global Stripe */
console.log("stripe_elements.js LOADED");

(function () {
  // --- DOM ---
  const pkEl = document.getElementById("id_stripe_public_key");
  const csEl = document.getElementById("id_client_secret");
  const form = document.getElementById("payment-form");
  const cardMount = document.getElementById("card-element");
  const errorDiv = document.getElementById("card-errors");
  const submitButton = document.getElementById("submit-button");
  const overlay = document.getElementById("loading-overlay");

  // Optional: save-info checkbox + redirect input (these IDs match Boutique Ado conventions)
  const saveInfoCheckbox = document.getElementById("id-save-info");
  const redirectUrlEl = document.getElementById("id_redirect_url"); // if you have it

  if (!pkEl || !csEl || !form) {
    console.warn("Stripe setup missing: key/secret/form not found.");
    return;
  }

  if (!cardMount) {
    console.warn("Stripe setup missing: #card-element not found in template.");
    if (errorDiv) errorDiv.textContent = "Payment form error. Please refresh and try again.";
    return;
  }

  // --- Read JSON from json_script ---
  let stripePublicKey;
  let clientSecret;

  try {
    stripePublicKey = JSON.parse(pkEl.textContent);
    clientSecret = JSON.parse(csEl.textContent);
  } catch (e) {
    console.warn("Stripe key/secret JSON parse failed. Check json_script blocks.", e);
    if (errorDiv) errorDiv.textContent = "Payment form error. Please refresh and try again.";
    return;
  }

  if (!stripePublicKey || !clientSecret) {
    console.warn("Stripe keys/client secret empty. Check view context + env vars.");
    if (errorDiv) errorDiv.textContent = "Payment configuration missing. Check Stripe keys.";
    return;
  }

  // --- Stripe Elements ---
  const stripe = Stripe(stripePublicKey);
  const elements = stripe.elements();

  const style = {
    base: {
      color: "#000",
      fontFamily: "inherit",
      fontSize: "16px",
      "::placeholder": { color: "#aab7c4" },
    },
    invalid: { color: "#dc3545" },
  };

  const card = elements.create("card", { style });
  card.mount("#card-element");

  card.on("change", (event) => {
    if (!errorDiv) return;
    errorDiv.textContent = event.error ? event.error.message : "";
  });

  // --- helpers ---
  function getFieldValue(id) {
    const el = document.getElementById(id);
    return el && el.value ? String(el.value).trim() : "";
  }

  function normalizeCountryToISO2(rawCountry) {
    const v = (rawCountry || "").trim();

    // If already ISO-2
    if (/^[A-Za-z]{2}$/.test(v)) return v.toUpperCase();

    // Common label -> ISO-2 mappings
    const map = {
      "United Kingdom": "GB",
      UK: "GB",
      "Great Britain": "GB",
      England: "GB",
      Scotland: "GB",
      Wales: "GB",
      "Northern Ireland": "GB",
    };

    return map[v] || v;
  }

  function showOverlay() {
    if (!overlay) return;
    overlay.classList.remove("d-none");
    overlay.setAttribute("aria-hidden", "false");
  }

  function hideOverlay() {
    if (!overlay) return;
    overlay.classList.add("d-none");
    overlay.setAttribute("aria-hidden", "true");
  }

  function setProcessing(isProcessing) {
    if (submitButton) {
      submitButton.disabled = isProcessing;
      submitButton.classList.toggle("disabled", isProcessing);
    }
    card.update({ disabled: isProcessing });
    form.dataset.processing = isProcessing ? "1" : "0";
  }

  // CSRF cookie reader (works even if token isn’t inside the form)
  function getCookie(name) {
    const cookieValue = document.cookie
      .split(";")
      .map((c) => c.trim())
      .find((c) => c.startsWith(name + "="));
    return cookieValue ? decodeURIComponent(cookieValue.split("=")[1]) : null;
  }

  async function cacheCheckoutData(cs, saveInfo) {
    // Your Django URL should match urls.py, e.g. path('cache_checkout_data/', ...)
    const url = "/checkout/cache_checkout_data/";
    const csrftoken = getCookie("csrftoken");

    // Send form-encoded data (simplest for Django request.POST)
    const body = new URLSearchParams();
    body.append("client_secret", cs);
    body.append("save_info", saveInfo ? "on" : "");

    const resp = await fetch(url, {
      method: "POST",
      headers: {
        "X-CSRFToken": csrftoken || "",
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: body.toString(),
    });

    if (!resp.ok) {
      const text = await resp.text().catch(() => "");
      throw new Error(text || "Failed to cache checkout data");
    }
  }

  let processing = false;

  // --- submit handler ---
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (processing) return;

    processing = true;
    setProcessing(true);
    showOverlay();
    if (errorDiv) errorDiv.textContent = "";

    const rawCountry = getFieldValue("id_country");
    const countryCode = normalizeCountryToISO2(rawCountry);

    // Billing (Stripe may override postal_code from card; harmless but optional)
    const billingDetails = {
      name: getFieldValue("id_full_name"),
      email: getFieldValue("id_email"),
      phone: getFieldValue("id_phone_number"),
      address: {
        line1: getFieldValue("id_street_address1"),
        line2: getFieldValue("id_street_address2"),
        city: getFieldValue("id_town_or_city"),
        state: getFieldValue("id_county"),
        // postal_code: getFieldValue("id_postcode"), // optional; course often omits
        country: countryCode,
      },
    };

    // Shipping (include postcode here)
    const shippingDetails = {
      name: getFieldValue("id_full_name"),
      phone: getFieldValue("id_phone_number"),
      address: {
        line1: getFieldValue("id_street_address1"),
        line2: getFieldValue("id_street_address2"),
        city: getFieldValue("id_town_or_city"),
        state: getFieldValue("id_county"),
        postal_code: getFieldValue("id_postcode"),
        country: countryCode,
      },
    };

    try {
      // 1) Cache metadata onto PaymentIntent (server-side)
      const saveInfo = !!(saveInfoCheckbox && saveInfoCheckbox.checked);
      await cacheCheckoutData(clientSecret, saveInfo);

      // 2) Confirm payment with billing + shipping
      const result = await stripe.confirmCardPayment(clientSecret, {
        payment_method: {
          card: card,
          billing_details: billingDetails,
        },
        shipping: shippingDetails,
      });

      if (result.error) {
        if (errorDiv) errorDiv.textContent = result.error.message || "Payment failed. Please try again.";
        processing = false;
        setProcessing(false);
        hideOverlay();
        return;
      }

      const pi = result.paymentIntent;

      if (pi && pi.status === "succeeded") {
        // Optional: keep pid field for your existing Django flow (fine to keep)
        let pidInput = document.getElementById("id_stripe_pid");
        if (!pidInput) {
          pidInput = document.createElement("input");
          pidInput.type = "hidden";
          pidInput.name = "stripe_pid";
          pidInput.id = "id_stripe_pid";
          form.appendChild(pidInput);
        }
        pidInput.value = pi.id;

        // Optional: redirect_url hidden input if you use it server-side
        if (redirectUrlEl) {
          // leave as-is if you already set it in the template
        }

        // Leave overlay ON; form submission begins your Django checkout POST
        form.submit();
        return;
      }

      if (errorDiv) errorDiv.textContent = "Payment not completed. Please try again.";
      processing = false;
      setProcessing(false);
      hideOverlay();
    } catch (err) {
      console.warn("Checkout error:", err);
      if (errorDiv) {
        errorDiv.textContent =
          "Sorry, there was an issue processing your payment. Please try again.";
      }
      processing = false;
      setProcessing(false);
      hideOverlay();
    }
  });
})();
