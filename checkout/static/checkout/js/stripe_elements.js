/* global Stripe */

(function () {
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

  function getFieldValue(id) {
    const el = document.getElementById(id);
    if (!el) return "";
    return (el.value || "").trim();
  }

  function setProcessing(isProcessing) {
    if (submitButton) {
      submitButton.disabled = isProcessing;
      submitButton.classList.toggle("disabled", isProcessing);
    }
    // Transcript: disable the card element too
    card.update({ disabled: isProcessing });

    form.dataset.processing = isProcessing ? "1" : "0";
  }

  let processing = false;

  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    // Optional: enforce browser validation before Stripe call
    if (!form.checkValidity()) {
      form.reportValidity();
      return;
    }

    if (processing) return;
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
        country: getFieldValue("id_country"), // should be ISO-2 like "GB"
      },
    };

    try {
      const result = await stripe.confirmCardPayment(
        clientSecret,
        {
          payment_method: {
            card,
            billing_details: billingDetails,
          },
        },
        // Robust option if you later move action handling server-side:
        // { handleActions: false }
      );

      if (result.error) {
        if (errorDiv) errorDiv.textContent = result.error.message || "Payment failed. Please try again.";
        processing = false;
        setProcessing(false);
        return;
      }

      const pi = result.paymentIntent;

      if (pi && pi.status === "succeeded") {
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

      if (errorDiv) errorDiv.textContent = `Payment status: ${pi ? pi.status : "unknown"}. Please try again.`;
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
