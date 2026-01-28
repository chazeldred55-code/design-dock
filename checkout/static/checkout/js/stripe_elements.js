/* global Stripe */

(function () {
  // --- Safe guards ---
  const pkEl = document.getElementById("id_stripe_public_key");
  const csEl = document.getElementById("id_client_secret");
  const form = document.getElementById("payment-form");
  const cardMount = document.getElementById("card-element");
  const errorDiv = document.getElementById("card-errors");
  const submitButton = document.getElementById("submit-button");

  if (!pkEl || !csEl || !form) {
    console.warn("Stripe setup missing: key/secret/form not found.");
    return;
  }

  if (!cardMount) {
    console.warn("Stripe setup missing: #card-element not found in template.");
    if (errorDiv) errorDiv.textContent = "Payment form error. Please refresh and try again.";
    return;
  }

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

  // --- Stripe Elements setup ---
  const stripe = Stripe(stripePublicKey);
  const elements = stripe.elements();

  const style = {
    base: {
      color: "#000",
      fontFamily: "inherit",
      fontSize: "16px",
      "::placeholder": { color: "#aab7c4" },
    },
    invalid: {
      color: "#dc3545",
    },
  };

  const card = elements.create("card", { style });
  card.mount("#card-element");

  card.on("change", (event) => {
    if (!errorDiv) return;
    errorDiv.textContent = event.error ? event.error.message : "";
  });

  // Helpers
  function getFieldValue(id) {
    const el = document.getElementById(id);
    if (!el) return "";

    // Handles input/select/textarea
    if (el.tagName === "SELECT") {
      return (el.value || "").trim();
    }
    return (el.value || "").trim();
  }

  function setProcessing(isProcessing) {
    if (submitButton) {
      submitButton.disabled = isProcessing;
      submitButton.classList.toggle("disabled", isProcessing);
    }
    form.dataset.processing = isProcessing ? "1" : "0";
  }

  let processing = false;

  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    if (processing) return; // prevent double submits
    processing = true;
    setProcessing(true);
    if (errorDiv) errorDiv.textContent = "";

    const billingDetails = {
      name: getFieldValue("id_full_name"),
      email: getFieldValue("id_email"),
      phone: getFieldValue("id_phone_number"),
      address: {
        line1: getFieldValue("id_street_address1"),
        line2: getFieldValue("id_street_address2"),
        city: getFieldValue("id_town_or_city"),
        state: getFieldValue("id_county"),
        postal_code: getFieldValue("id_postcode"),
        // Must be 2-letter ISO (e.g. GB). Django CountryField normally provides that.
        country: getFieldValue("id_country"),
      },
    };

    try {
      const result = await stripe.confirmCardPayment(clientSecret, {
        payment_method: {
          card: card,
          billing_details: billingDetails,
        },
      });

      if (result.error) {
        if (errorDiv) errorDiv.textContent = result.error.message || "Payment failed. Please try again.";
        processing = false;
        setProcessing(false);
        return;
      }

      const pi = result.paymentIntent;

      if (pi && pi.status === "succeeded") {
        // Add PID hidden input (so Django can store it on the Order)
        let pidInput = document.getElementById("id_stripe_pid");
        if (!pidInput) {
          pidInput = document.createElement("input");
          pidInput.type = "hidden";
          pidInput.name = "stripe_pid";
          pidInput.id = "id_stripe_pid";
          form.appendChild(pidInput);
        }
        pidInput.value = pi.id;

        form.submit();
        return;
      }

      // Any other status:
      if (errorDiv) errorDiv.textContent = "Payment not completed. Please try again.";
      processing = false;
      setProcessing(false);
    } catch (err) {
      console.warn("Stripe confirmCardPayment threw:", err);
      if (errorDiv) errorDiv.textContent = "Payment failed. Please try again.";
      processing = false;
      setProcessing(false);
    }
  });
})();
