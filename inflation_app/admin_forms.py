from django import forms
from .models import Product

class ReplaceProductForm(forms.Form):
    target_product = forms.ModelChoiceField(
        queryset=Product.objects.all(),
        label="Replace with product",
        empty_label=None
    )
