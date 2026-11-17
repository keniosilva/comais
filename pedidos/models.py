from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q


class Cliente(models.Model):
    nome = models.CharField(max_length=120)
    telefone = models.CharField(max_length=20)
    endereco = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class Pedido(models.Model):
    class Status(models.TextChoices):
        PENDENTE = "pendente", "Pendente"
        PRODUZIDO = "produzido", "Produzido"
        ENTREGUE = "entregue", "Entregue"
        CANCELADO = "cancelado", "Cancelado"

    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name="pedidos")
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="pedidos")
    data_hora_entrega = models.DateTimeField()
    endereco_entrega = models.CharField(max_length=255, blank=True)
    observacao = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDENTE)
    valor_total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["data_hora_entrega"]
        # Acelera a lista de produção e de entregas, que filtram por intervalo de entrega e status.
        indexes = [models.Index(fields=["data_hora_entrega", "status"], name="pedido_entrega_status_idx")]

    def __str__(self):
        return f"Pedido {self.pk} - {self.cliente}"


class ItemPedido(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name="itens")
    produto = models.ForeignKey("catalogo.Produto", on_delete=models.PROTECT, related_name="itens_pedido")
    qtd_cento = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    # Preço copiado no momento do pedido, para não distorcer o histórico se o preço mudar depois.
    preco_cento = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["pedido", "produto"], name="item_pedido_produto_unico"),
            models.CheckConstraint(condition=Q(qtd_cento__gt=0), name="item_qtd_maior_que_zero"),
        ]

    @property
    def subtotal(self):
        return self.qtd_cento * self.preco_cento
