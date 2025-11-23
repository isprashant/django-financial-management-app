from decimal import Decimal

from django import forms

from .models import InvestmentScheme


class InvestmentForm(forms.Form):
    amount = forms.DecimalField(
        max_digits=14,
        decimal_places=2,
        label="Amount to invest",
    )

    def __init__(self, *args, scheme: InvestmentScheme | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.scheme = scheme

        if scheme:
            self.fields["amount"].min_value = scheme.min_amount
            self.fields["amount"].max_value = scheme.max_amount

    def clean_amount(self) -> Decimal:
        amount = self.cleaned_data["amount"]
        scheme = self.scheme

        if scheme:
            if amount < scheme.min_amount:
                raise forms.ValidationError(
                    f"Minimum investment for this scheme is {scheme.min_amount}."
                )
            if amount > scheme.max_amount:
                raise forms.ValidationError(
                    f"Maximum investment for this scheme is {scheme.max_amount}."
                )

        return amount
