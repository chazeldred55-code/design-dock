/* global Stripe */
console.log("stripe_elements.js LOADED");

(function () {
  // -------------------------
  // DOM
  // -------------------------
  const pkEl = document.getElementById("id_stripe_public_key"); // json_script
  const csEl = document.getElementById("id_client_secret");     // json_script

  const form = document.getElementById("payment-form");
  const cardMount = document.getElementById("card-element");
  const errorDiv = document.getElementById("card-errors");
  const submitButton = document.getElementById("submit-button");
  const overlay = document.getElementById("loading-overlay");

  const saveInfoCheckbox = document.getElementById("id-save-info");
  const cacheUrlEl = document.getElementById("id_cache_url"); // hidden input set in template

  if (!pkEl || !csEl || !form) {
    console.warn("Stripe setup missing: public key / client secret / form not found.");
    return;
  }

  if (!cardMount) {
    console.warn("Stripe setup missing: #card-element not found in template.");
    if (errorDiv) errorDiv.textContent = "Payment form error. Please refresh and try again.";
    return;
  }

  // -------------------------
  // Read JSON safely
  // -------------------------
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

  // -------------------------
  // Stripe Elements
  // -------------------------
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

  // -------------------------
  // Helpers
  // -------------------------
  function getFieldValue(id) {
    const el = document.getElementById(id);
    return el && el.value ? String(el.value).trim() : "";
  }

  function normalizeCountryToISO2(rawCountry) {
    const v = (rawCountry || "").trim();

    // Already ISO-2
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
    // Not all Stripe Elements support disabled; keep safe.
    try {
      card.update({ disabled: isProcessing });
    } catch (e) {
      // ignore
    }
    form.dataset.processing = isProcessing ? "1" : "0";
  }

  // Read CSRF token from cookie (Django default)
  function getCookie(name) {
    const cookieValue = document.cookie
      .split(";")
      .map((c) => c.trim())
      .find((c) => c.startsWith(name + "="));
    return cookieValue ? decodeURIComponent(cookieValue.split("=")[1]) : null;
  }

  async function cacheCheckoutData(clientSecretValue, saveInfo) {
    const url = cacheUrlEl ? cacheUrlEl.value : "/checkout/cache_checkout_data/";
    const csrftoken = getCookie("csrftoken");

    const body = new URLSearchParams();
    body.append("client_secret", clientSecretValue);
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
      // If your view returns useful text, bubble it up for debugging
      const text = await resp.text().catch(() => "");
      throw new Error(text || `Failed to cache checkout data (${resp.status})`);
    }
  }

  let processing = false;

  // -------------------------
  // Submit handler
  // -------------------------
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (processing) return;

    processing = true;
    setProcessing(true);
    showOverlay();
    if (errorDiv) errorDiv.textContent = "";

    // Country field in Boutique Ado is often ISO-2 already
    const rawCountry = getFieldValue("id_country");
    const countryCode = normalizeCountryToISO2(rawCountry);

    const billingDetails = {
      name: getFieldValue("id_full_name"),
      email: getFieldValue("id_email"),
      phone: getFieldValue("id_phone_number"),
      address: {
        line1: getFieldValue("id_street_address1"),
        line2: getFieldValue("id_street_address2"),
        city: getFieldValue("id_town_or_city"),
        state: getFieldValue("id_county"),
        country: countryCode,
      },
    };

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
      // 1) Cache the extra data onto the PaymentIntent (metadata, save_info, username, etc.)
      const saveInfo = !!(saveInfoCheckbox && saveInfoCheckbox.checked);
      await cacheCheckoutData(clientSecret, saveInfo);

      // 2) Confirm payment
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
        // Store pid for Django flow (optional but common)
        let pidInput = document.getElementById("id_stripe_pid");
        if (!pidInput) {
          pidInput = document.createElement("input");
          pidInput.type = "hidden";
          pidInput.name = "stripe_pid";
          pidInput.id = "id_stripe_pid";
          form.appendChild(pidInput);
        }
        pidInput.value = pi.id;

        // Leave overlay ON; submit to Django checkout view
        form.submit();
        return;
      }

      if (errorDiv) errorDiv.textContent = "Payment not completed. Please try again.";
      processing = false;
      setProcessing(false);
      hideOverlay();
    } catch (err) {
      console.warn("Checkout error:", err);

      // Course pattern often reloads to show messages from the view:
      // location.reload();
      // But we can show it inline (better UX). If you prefer course behavior, uncomment reload.
      if (errorDiv) {
        errorDiv.textContent =
          err && err.message
            ? err.message
            : "Sorry, there was an issue processing your payment. Please try again.";
      }

      // Uncomment to follow the course exactly (show Django messages):
      // location.reload();

      processing = false;
      setProcessing(false);
      hideOverlay();
    }
  });
})();
