from django import forms
from django.forms import inlineformset_factory

from looplink.campaigns.models import Campaign, Offer
from looplink.campaigns.services.offers import offer_parameter_errors


class CampaignForm(forms.ModelForm):
    class Meta:
        model = Campaign
        fields = ("name", "description", "starts_at", "ends_at", "version")
        widgets = {
            "name": forms.TextInput(attrs={"autocomplete": "off", "placeholder": "e.g. Weekend rewards"}),
            "description": forms.Textarea(
                attrs={"placeholder": "What should shoppers know about this campaign?", "rows": 4}
            ),
            "starts_at": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
            "ends_at": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
            "version": forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in ("starts_at", "ends_at"):
            self.fields[field_name].input_formats = ("%Y-%m-%dT%H:%M",)


class OfferForm(forms.ModelForm):
    type = forms.ChoiceField(
        choices=(("", "Choose an offer type"), *Offer.Type.choices),
        widget=forms.Select(attrs={"class": "offer-type-select"}),
    )
    percent = forms.DecimalField(decimal_places=2, max_digits=5, required=False)
    applies_to = forms.CharField(max_length=255, required=False)
    amount_off = forms.DecimalField(decimal_places=2, max_digits=10, required=False)
    min_basket = forms.DecimalField(decimal_places=2, max_digits=10, required=False)
    stickers = forms.IntegerField(min_value=1, required=False)
    per_amount = forms.DecimalField(decimal_places=2, max_digits=10, required=False)
    parameters = forms.JSONField(required=False, widget=forms.HiddenInput())
    position = forms.IntegerField(required=False, widget=forms.HiddenInput())

    class Meta:
        model = Offer
        fields = ("type", "position", "parameters")
        widgets = {"position": forms.HiddenInput()}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        parameters = self.instance.parameters or {}
        for field_name in ("percent", "applies_to", "amount_off", "min_basket", "stickers", "per_amount"):
            self.fields[field_name].initial = parameters.get(field_name)

        self.fields["percent"].widget.attrs["placeholder"] = "10"
        self.fields["applies_to"].widget.attrs["placeholder"] = "e.g. Selected snacks"
        self.fields["amount_off"].widget.attrs["placeholder"] = "5"
        self.fields["min_basket"].widget.attrs["placeholder"] = "30"
        self.fields["stickers"].widget.attrs["placeholder"] = "2"
        self.fields["per_amount"].widget.attrs["placeholder"] = "10"

    def clean(self):
        cleaned_data = super().clean()
        offer_type = cleaned_data.get("type")
        if not offer_type:
            return cleaned_data

        parameters = self._parameters_for_type(offer_type, cleaned_data)
        errors = offer_parameter_errors(offer_type, parameters)
        if errors:
            raise forms.ValidationError(errors)
        cleaned_data["parameters"] = parameters
        return cleaned_data

    def _parameters_for_type(self, offer_type, cleaned_data):
        if offer_type == Offer.Type.PRODUCT_PERCENT_DISCOUNT:
            return {
                "percent": float(cleaned_data.get("percent")) if cleaned_data.get("percent") is not None else None,
                "applies_to": cleaned_data.get("applies_to", "").strip(),
            }
        if offer_type == Offer.Type.CART_FIXED_DISCOUNT:
            return {
                "amount_off": float(cleaned_data.get("amount_off"))
                if cleaned_data.get("amount_off") is not None
                else None,
                "min_basket": float(cleaned_data.get("min_basket"))
                if cleaned_data.get("min_basket") is not None
                else None,
            }
        return {
            "stickers": cleaned_data.get("stickers"),
            "per_amount": float(cleaned_data.get("per_amount"))
            if cleaned_data.get("per_amount") is not None
            else None,
        }


OfferFormSet = inlineformset_factory(Campaign, Offer, form=OfferForm, extra=1, can_delete=True)
