"""Regras de negócio de pedidos e produção (camada de serviços)."""
from datetime import datetime, time, timedelta
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


def intervalo_do_dia(data):
    """Início (inclusive) e fim (exclusivo) do dia no fuso do sistema.

    Usado no lugar de `__date`: o lookup `__date` no MySQL depende das tabelas de fuso
    horário do servidor e impede o uso do índice; o intervalo funciona em qualquer hospedagem.
    """
    inicio = timezone.make_aware(datetime.combine(data, time.min))
    return inicio, inicio + timedelta(days=1)


def producao_do_dia(data):
    """RF05: soma, por salgado, as encomendas pendentes com entrega na data informada."""
    inicio, fim = intervalo_do_dia(data)
    return (
        ItemPedido.objects.filter(
            pedido__status=Pedido.Status.PENDENTE,
            pedido__data_hora_entrega__gte=inicio,
            pedido__data_hora_entrega__lt=fim,
        )
        .values("produto__nome")
        .annotate(total=Sum("qtd_cento"))
        .order_by("produto__nome")
    )


def total_pedidos_do_dia(data):
    inicio, fim = intervalo_do_dia(data)
    return Pedido.objects.filter(
        status=Pedido.Status.PENDENTE, data_hora_entrega__gte=inicio, data_hora_entrega__lt=fim
    ).count()


# RF09: o status só avança na sequência pendente -> produzido -> entregue.
SEQUENCIA_STATUS = {
    Pedido.Status.PENDENTE: Pedido.Status.PRODUZIDO,
    Pedido.Status.PRODUZIDO: Pedido.Status.ENTREGUE,
}


def entregas_do_dia(data):
    """RF09: pedidos da data, ordenados por horário de entrega. Cancelados não aparecem."""
    inicio, fim = intervalo_do_dia(data)
    return (
        Pedido.objects.filter(data_hora_entrega__gte=inicio, data_hora_entrega__lt=fim)
        .exclude(status=Pedido.Status.CANCELADO)
        .select_related("cliente")
        .order_by("data_hora_entrega")
    )


@transaction.atomic
def avancar_status(pedido):
    """RF09: avança o pedido para o próximo status da sequência."""
    pedido = Pedido.objects.select_for_update().get(pk=pedido.pk)
    novo = SEQUENCIA_STATUS.get(pedido.status)
    if novo is None:
        raise ErroPedido("Este pedido já foi entregue ou foi cancelado e não pode mudar de status.")
    pedido.status = novo
    pedido.save(update_fields=["status"])
    return pedido
