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
        required=False,
        empty_label="Escolha o cliente",
    )
    # Cadastro rápido: permite criar o cliente na própria tela do pedido.
    novo_cliente_nome = forms.CharField(label="Nome do cliente novo", max_length=120, required=False)
    novo_cliente_telefone = forms.CharField(label="Telefone do cliente novo", max_length=20, required=False)
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
    observacao = forms.CharField(
        label="Observação (opcional)", max_length=255, required=False,
        widget=forms.TextInput(attrs={"placeholder": "Ex.: sem pimenta"}),
    )

    def clean(self):
        dados = super().clean()
        cliente = dados.get("cliente")
        nome = (dados.get("novo_cliente_nome") or "").strip()
        telefone = (dados.get("novo_cliente_telefone") or "").strip()
        if cliente and (nome or telefone):
            self.add_error("cliente", "Escolha um cliente da lista ou cadastre um novo, não os dois.")
        elif not cliente and not nome:
            self.add_error("cliente", "Escolha o cliente ou informe o nome de um cliente novo.")
        elif not cliente and not telefone:
            self.add_error("novo_cliente_telefone", "Informe o telefone do cliente novo.")
        dados["novo_cliente_nome"], dados["novo_cliente_telefone"] = nome, telefone
        return dados


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
