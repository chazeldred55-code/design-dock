/* global Stripe */
console.log("stripe_elements.js LOADED");
window.__DD_STRIPE_HANDLER_LOADED__ = true;
console.log("✅ Stripe handler attached");

(function () {

  // -------------------------
  // DOM
  // -------------------------
  const pkEl = document.getElementById("id_stripe_public_key");
  const csEl = document.getElementById("id_client_secret");

  const form = document.getElementById("payment-form");
  const submitButton = document.getElementById("submit-button");
  const cardMount = document.getElementById("card-element");
  const errorDiv = document.getElementById("card-errors");
  const overlay = document.getElementById("loading-overlay");

  const saveInfoCheckbox = document.getElementById("id-save-info");
  const cacheUrlEl = document.getElementById("id_cache_url");
  const clientSecretInput = document.getElementById("id_client_secret_input");

  if (!pkEl || !csEl || !form || !submitButton || !cardMount) {
    console.warn("Stripe setup incomplete.");
    return;
  }

  // -------------------------
  // Block native form submit
  // -------------------------
  form.addEventListener("submit", function (e) {
    e.preventDefault();
    e.stopPropagation();
    console.warn("🚫 Native form submit blocked");
    return false;
  });

  // -------------------------
  // Parse Stripe config
  // -------------------------
  let stripePublicKey;
  let clientSecret;

  try {
    stripePublicKey = JSON.parse(pkEl.textContent);
    clientSecret = JSON.parse(csEl.textContent);
  } catch (err) {
    console.error("Stripe config parse error:", err);
    return;
  }

  if (!stripePublicKey || !clientSecret) {
    console.error("Missing Stripe public key or client secret.");
    return;
  }

  if (clientSecretInput) {
    clientSecretInput.value = clientSecret;
  }

  // -------------------------
  // Stripe Elements
  // -------------------------
  const stripe = Stripe(stripePublicKey);
  const elements = stripe.elements();

  const card = elements.create("card", {
    style: {
      base: {
        color: "#000",
        fontFamily: "inherit",
        fontSize: "16px",
        "::placeholder": { color: "#aab7c4" },
      },
      invalid: { color: "#dc3545" },
    },
  });

  card.mount("#card-element");

  card.on("change", function (event) {
    if (errorDiv) {
      errorDiv.textContent = event.error ? event.error.message : "";
    }
  });

  // -------------------------
  // Helpers
  // -------------------------
  function getFieldValue(id) {
    const el = document.getElementById(id);
    return el && el.value ? String(el.value).trim() : "";
  }

  function getCookie(name) {
    const cookieValue = document.cookie
      .split(";")
      .map((c) => c.trim())
      .find((c) => c.startsWith(name + "="));
    return cookieValue ? decodeURIComponent(cookieValue.split("=")[1]) : null;
  }

  function showOverlay() {
    if (overlay) overlay.classList.remove("d-none");
  }

  function hideOverlay() {
    if (overlay) overlay.classList.add("d-none");
  }

  function setProcessing(state) {
    submitButton.disabled = state;
    try {
      card.update({ disabled: state });
    } catch (_) {}
  }

  async function cacheCheckoutData(secret, saveInfo) {
    const url = cacheUrlEl ? cacheUrlEl.value : "/checkout/cache_checkout_data/";
    const csrftoken = getCookie("csrftoken");

    const body = new URLSearchParams();
    body.append("client_secret", secret);
    body.append("save_info", saveInfo ? "on" : "");

    const response = await fetch(url, {
      method: "POST",
      headers: {
        "X-CSRFToken": csrftoken || "",
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: body.toString(),
    });

    if (!response.ok) {
      throw new Error("Failed to cache checkout data.");
    }
  }

  // -------------------------
  // Main payment flow
  // -------------------------
  let processing = false;

  submitButton.addEventListener("click", async function (e) {
    e.preventDefault();
    e.stopPropagation();

    console.log("✅ Submit button click handler fired");

    if (processing) return;
    processing = true;

    setProcessing(true);
    showOverlay();

    if (errorDiv) errorDiv.textContent = "";

    try {
      const saveInfo = !!(saveInfoCheckbox && saveInfoCheckbox.checked);

      await cacheCheckoutData(clientSecret, saveInfo);

      const result = await stripe.confirmCardPayment(clientSecret, {
        payment_method: {
          card: card,
          billing_details: {
            name: getFieldValue("id_full_name"),
            email: getFieldValue("id_email"),
            phone: getFieldValue("id_phone_number"),
          },
        },
      });

      if (result.error) {
        if (errorDiv) errorDiv.textContent = result.error.message;
        processing = false;
        setProcessing(false);
        hideOverlay();
        return;
      }

      if (result.paymentIntent && result.paymentIntent.status === "succeeded") {
        console.log("✅ Stripe payment succeeded — submitting Django form");
        form.submit();
        return;
      }

      if (errorDiv) errorDiv.textContent = "Payment not completed.";
      processing = false;
      setProcessing(false);
      hideOverlay();

    } catch (err) {
      console.warn("Checkout error:", err);
      if (errorDiv) {
        errorDiv.textContent =
          err.message || "Payment failed. Please try again.";
      }
      processing = false;
      setProcessing(false);
      hideOverlay();
    }
  });

})();
