from django import forms
from .models import *


class UploadFileForm(forms.Form):
    file = forms.FileField()


class ReplaceProductForm(forms.Form):
    """
    A simple form that allows selecting a target product.
    The queryset is passed in from the view to ensure we exclude the source.
    """
    target_product = forms.ModelChoiceField(
        queryset=Product.objects.none(),
        label="Replace with product",
        empty_label=None,
        required=True,
    )

    def __init__(self, *args, **kwargs):
        queryset = kwargs.pop("queryset", Product.objects.none())
        super().__init__(*args, **kwargs)
        self.fields["target_product"].queryset = queryset


class ReplaceRegionForm(forms.Form):
    target_region = forms.ModelChoiceField(
        queryset=Region.objects.none(),
        label="Replace with region",
        empty_label=None,
    )

    def __init__(self, *args, **kwargs):
        queryset = kwargs.pop("queryset", Region.objects.none())
        super().__init__(*args, **kwargs)
        self.fields["target_region"].queryset = queryset


class ReplaceDistrictForm(forms.Form):
    target_district = forms.ModelChoiceField(
        queryset=District.objects.none(),
        label="Replace with district",
        empty_label=None,
    )

    def __init__(self, *args, **kwargs):
        queryset = kwargs.pop("queryset", District.objects.none())
        super().__init__(*args, **kwargs)
        self.fields["target_district"].queryset = queryset
