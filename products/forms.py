from django import forms
from .widgets import CustomClearableFileInput
from .models import Product, Category


class ProductForm(forms.ModelForm):
    """
    Form for creating and updating products.
    Uses a custom widget for the image field to improve the UI.
    """

    image = forms.ImageField(
        label="Image",
        required=False,
        widget=CustomClearableFileInput,
    )

    class Meta:
        model = Product
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        """
        Add category-friendly names to the dropdown.
        """
        super().__init__(*args, **kwargs)

        categories = Category.objects.all()
        friendly_names = [(c.id, c.get_friendly_name()) for c in categories]

        self.fields["category"].choices = friendly_names

        for field_name, field in self.fields.items():
            field.widget.attrs["class"] = "border-black rounded-0"
