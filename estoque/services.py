"""Regras de negócio do estoque (camada de serviços).

Todo acesso ao banco passa pelo ORM do Django (consultas parametrizadas).
"""
from decimal import Decimal

from django.db import transaction
from django.db.models import F

from catalogo.models import Insumo

from .models import MovimentoEstoque


class ErroEstoque(ValueError):
    """Erro de regra de negócio do estoque, com mensagem própria para o usuário."""


def _movimentar(*, usuario, insumo, tipo, delta, pedido=None):
    # Bloqueia a linha do insumo durante a transação para evitar saldo inconsistente em acessos simultâneos.
    insumo = Insumo.objects.select_for_update().get(pk=insumo.pk)
    insumo.estoque_atual += delta
    insumo.save(update_fields=["estoque_atual"])
    return MovimentoEstoque.objects.create(insumo=insumo, usuario=usuario, tipo=tipo, quantidade=delta, pedido=pedido)


@transaction.atomic
def registrar_compra(*, usuario, insumo, quantidade):
    """RF07: soma a quantidade comprada ao estoque e registra o movimento."""
    quantidade = Decimal(str(quantidade))
    if quantidade <= 0:
        raise ErroEstoque("Informe uma quantidade de compra maior que zero.")
    return _movimentar(usuario=usuario, insumo=insumo, tipo=MovimentoEstoque.Tipo.COMPRA, delta=quantidade)


@transaction.atomic
def baixar_insumo(*, usuario, insumo, quantidade, pedido):
    """RF06: reduz o estoque pelo consumo da produção. Deve ser chamada dentro da transação do pedido."""
    quantidade = Decimal(str(quantidade))
    if quantidade <= 0:
        raise ErroEstoque("A quantidade de baixa deve ser maior que zero.")
    return _movimentar(
        usuario=usuario,
        insumo=insumo,
        tipo=MovimentoEstoque.Tipo.BAIXA_PRODUCAO,
        delta=-quantidade,
        pedido=pedido,
    )


def insumos_abaixo_do_minimo():
    """RF08: insumos cujo saldo está abaixo do mínimo cadastrado."""
    return Insumo.objects.filter(estoque_atual__lt=F("estoque_minimo")).order_by("nome")
