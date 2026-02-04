# products/widgets.py

from django.forms.widgets import ClearableFileInput
from django.utils.translation import gettext_lazy as _


class CustomClearableFileInput(ClearableFileInput):
    """
    Custom widget for product image uploads.
    Overrides the default ClearableFileInput text and template for nicer UI.
    """

    clear_checkbox_label = _("Remove")
    initial_text = _("Current Image")
    input_text = _("Change Image")
    template_name = (
        "products/custom_widget_templates/custom_clearable_file_input.html"
    )
