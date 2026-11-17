from decimal import Decimal

from django import forms


class CompraForm(forms.Form):
    quantidade = forms.DecimalField(
        label="Quantidade comprada",
        max_digits=12,
        decimal_places=3,
        min_value=Decimal("0.001"),
        error_messages={
            "required": "Informe a quantidade comprada.",
            "invalid": "Informe um número válido.",
            "min_value": "Informe uma quantidade maior que zero.",
        },
    )
