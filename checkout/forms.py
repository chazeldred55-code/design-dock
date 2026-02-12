from django import forms
from .models import Order


class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = (
            "full_name",
            "email",
            "phone_number",
            "country",
            "postcode",
            "town_or_city",
            "street_address1",
            "street_address2",
            "county",
        )

    def __init__(self, *args, **kwargs):
        """
        Digital checkout UX:
        - Only require: full_name, email, phone_number
        - Make address fields optional (no shipping)
        - Keep Boutique Ado styling approach (placeholders, classes, no labels)
        """
        super().__init__(*args, **kwargs)

        # Make address fields optional for a digital store
        optional_fields = [
            "country",
            "postcode",
            "town_or_city",
            "street_address1",
            "street_address2",
            "county",
        ]
        for field in optional_fields:
            self.fields[field].required = False

        placeholders = {
            "full_name": "Full Name",
            "email": "Email Address",
            "phone_number": "Phone Number",
            "country": "Country",
            "postcode": "Postal Code",
            "town_or_city": "Town or City",
            "street_address1": "Street Address 1",
            "street_address2": "Street Address 2",
            "county": "County, State or Locality",
        }

        self.fields["full_name"].widget.attrs["autofocus"] = True

        for field in self.fields:
            # Country doesn't use placeholder in the original pattern (select),
            # but we still apply CSS class + remove label.
            if field != "country":
                placeholder = placeholders.get(field, "")
                if self.fields[field].required:
                    placeholder = f"{placeholder} *"
                self.fields[field].widget.attrs["placeholder"] = placeholder

            self.fields[field].widget.attrs["class"] = "stripe-style-input"
            self.fields[field].label = False
