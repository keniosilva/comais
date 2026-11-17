"""Regras de negócio de pedidos e produção (camada de serviços)."""
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from catalogo.models import Receita
from estoque.services import baixar_insumo

from .models import ItemPedido, Pedido


class ErroPedido(ValueError):
    """Erro de regra de negócio do pedido, com mensagem própria para o usuário."""


@transaction.atomic
def criar_pedido(*, usuario, cliente, data_hora_entrega, endereco_entrega, itens):
    """RF04 + RF06: grava o pedido, os itens e a baixa de insumos na MESMA transação.

    `itens` é uma lista de tuplas (produto, qtd_cento). Se qualquer etapa falhar,
    nada é gravado (o estoque nunca fica atualizado sem o pedido correspondente).
    """
    if not itens:
        raise ErroPedido("Informe pelo menos um produto no pedido.")
    if data_hora_entrega <= timezone.now():
        raise ErroPedido("A data e a hora de entrega devem estar no futuro.")

    vistos = set()
    for produto, qtd_cento in itens:
        if not produto.ativo:
            raise ErroPedido(f"O produto {produto.nome} está inativo.")
        if produto.pk in vistos:
            raise ErroPedido(f"O produto {produto.nome} aparece mais de uma vez. Some as quantidades em uma linha.")
        vistos.add(produto.pk)
        if qtd_cento <= 0:
            raise ErroPedido("Informe a quantidade em cento, com número maior que zero.")

    pedido = Pedido.objects.create(
        cliente=cliente,
        usuario=usuario,
        data_hora_entrega=data_hora_entrega,
        endereco_entrega=endereco_entrega or cliente.endereco,
    )

    total = Decimal("0")
    for produto, qtd_cento in itens:
        receitas = list(Receita.objects.filter(produto=produto).select_related("insumo"))
        if not receitas:
            raise ErroPedido(f"O produto {produto.nome} não tem receita cadastrada.")
        item = ItemPedido.objects.create(
            pedido=pedido, produto=produto, qtd_cento=qtd_cento, preco_cento=produto.preco_cento
        )
        total += item.subtotal
        for receita in receitas:
            baixar_insumo(
                usuario=usuario,
                insumo=receita.insumo,
                quantidade=qtd_cento * receita.qtd_por_cento,
                pedido=pedido,
            )

    pedido.valor_total = total
    pedido.save(update_fields=["valor_total"])
    return pedido


def producao_do_dia(data):
    """RF05: soma, por salgado, as encomendas pendentes com entrega na data informada."""
    return (
        ItemPedido.objects.filter(pedido__status=Pedido.Status.PENDENTE, pedido__data_hora_entrega__date=data)
        .values("produto__nome")
        .annotate(total=Sum("qtd_cento"))
        .order_by("produto__nome")
    )


def total_pedidos_do_dia(data):
    return Pedido.objects.filter(status=Pedido.Status.PENDENTE, data_hora_entrega__date=data).count()
