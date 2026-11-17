from decimal import Decimal

from django import forms
from django.forms import formset_factory

from catalogo.models import Produto

from .models import Cliente

MSG_QTD = "Informe a quantidade em cento, com número maior que zero."


class PedidoForm(forms.Form):
    cliente = forms.ModelChoiceField(
        queryset=Cliente.objects.all(),
        label="Cliente",
        error_messages={"required": "Escolha o cliente."},
    )
    data_entrega = forms.DateField(
        label="Data da entrega",
        widget=forms.DateInput(attrs={"type": "date"}),
        error_messages={"required": "Informe a data da entrega.", "invalid": "Informe uma data válida."},
    )
    hora_entrega = forms.TimeField(
        label="Hora",
        widget=forms.TimeInput(attrs={"type": "time"}),
        error_messages={"required": "Informe a hora da entrega.", "invalid": "Informe uma hora válida."},
    )
    endereco_entrega = forms.CharField(label="Endereço de entrega", max_length=255, required=False)


class ItemForm(forms.Form):
    produto = forms.ModelChoiceField(
        queryset=Produto.objects.filter(ativo=True),
        label="Produto",
        error_messages={"required": "Escolha o produto."},
    )
    qtd_cento = forms.DecimalField(
        label="Quantidade (em cento)",
        max_digits=10,
        decimal_places=2,
        min_value=Decimal("0.01"),
        widget=forms.NumberInput(attrs={"step": "0.01", "placeholder": "Ex.: 3", "inputmode": "decimal"}),
        error_messages={
            "required": MSG_QTD,
            "invalid": MSG_QTD,
            "min_value": MSG_QTD,
            "max_digits": MSG_QTD,
            "max_decimal_places": "Use no máximo duas casas decimais.",
        },
    )


# Linhas extras vazias são ignoradas; o serviço exige ao menos um item.
ItemFormSet = formset_factory(ItemForm, extra=3)
