from django.conf import settings
from django.db import models
from django.db.models import Q


class MovimentoEstoque(models.Model):
    """Histórico de compras e baixas. O saldo do insumo muda sempre por um movimento."""

    class Tipo(models.TextChoices):
        COMPRA = "compra", "Compra"
        BAIXA_PRODUCAO = "baixa_producao", "Baixa de produção"
        AJUSTE = "ajuste", "Ajuste"

    insumo = models.ForeignKey("catalogo.Insumo", on_delete=models.PROTECT, related_name="movimentos")
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="movimentos")
    tipo = models.CharField(max_length=20, choices=Tipo.choices)
    # Positiva entra no estoque (compra); negativa sai (baixa).
    quantidade = models.DecimalField(max_digits=12, decimal_places=3)
    pedido = models.ForeignKey("pedidos.Pedido", on_delete=models.PROTECT, null=True, blank=True, related_name="movimentos")
    data_hora = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-data_hora"]
        constraints = [models.CheckConstraint(condition=~Q(quantidade=0), name="movimento_quantidade_nao_zero")]
