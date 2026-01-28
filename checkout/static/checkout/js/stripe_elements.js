/* global Stripe */

const stripePublicKey = JSON.parse(
  document.getElementById("id_stripe_public_key").textContent
);
const clientSecret = JSON.parse(
  document.getElementById("id_client_secret").textContent
);

const stripe = Stripe(stripePublicKey);
const elements = stripe.elements();

const card = elements.create("card");
card.mount("#card-element");

card.on("change", (event) => {
  const errorDiv = document.getElementById("card-errors");
  errorDiv.textContent = event.error ? event.error.message : "";
});

const form = document.getElementById("payment-form");

form.addEventListener("submit", async (e) => {
  e.preventDefault();

  const submitButton = document.getElementById("submit-button");
  if (submitButton) submitButton.disabled = true;

  const result = await stripe.confirmCardPayment(clientSecret, {
    payment_method: {
      card: card,
      billing_details: {
        name: form.full_name ? form.full_name.value.trim() : "",
        email: form.email ? form.email.value.trim() : "",
      },
    },
  });

  if (result.error) {
    document.getElementById("card-errors").textContent = result.error.message;
    if (submitButton) submitButton.disabled = false;
  } else if (result.paymentIntent.status === "succeeded") {
    form.submit();
  }
});
