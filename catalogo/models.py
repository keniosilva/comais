from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q


class Produto(models.Model):
    """Salgado vendido (coxinha, risole...). Preço por cento."""

    nome = models.CharField(max_length=100, unique=True)
    preco_cento = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ["nome"]
        constraints = [models.CheckConstraint(condition=Q(preco_cento__gt=0), name="produto_preco_maior_que_zero")]

    def __str__(self):
        return self.nome


class Insumo(models.Model):
    """Matéria-prima controlada em estoque. O saldo só muda por movimentos (app estoque)."""

    class Unidade(models.TextChoices):
        KG = "kg", "kg"
        G = "g", "g"
        L = "l", "l"
        UN = "un", "un"

    nome = models.CharField(max_length=100, unique=True)
    unidade = models.CharField(max_length=2, choices=Unidade.choices, default=Unidade.KG)
    estoque_atual = models.DecimalField(max_digits=12, decimal_places=3, default=Decimal("0"))
    estoque_minimo = models.DecimalField(
        max_digits=12, decimal_places=3, default=Decimal("0"), validators=[MinValueValidator(Decimal("0"))]
    )

    class Meta:
        ordering = ["nome"]
        constraints = [models.CheckConstraint(condition=Q(estoque_minimo__gte=0), name="insumo_minimo_nao_negativo")]

    @property
    def abaixo_do_minimo(self):
        return self.estoque_atual < self.estoque_minimo

    def __str__(self):
        return self.nome


class Receita(models.Model):
    """Quantidade de um insumo por cento de um produto. Base da baixa automática."""

    produto = models.ForeignKey(Produto, on_delete=models.CASCADE, related_name="receitas")
    insumo = models.ForeignKey(Insumo, on_delete=models.PROTECT, related_name="receitas")
    qtd_por_cento = models.DecimalField(
        "quantidade por cento", max_digits=12, decimal_places=3, validators=[MinValueValidator(Decimal("0.001"))]
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["produto", "insumo"], name="receita_produto_insumo_unico"),
            models.CheckConstraint(condition=Q(qtd_por_cento__gt=0), name="receita_qtd_maior_que_zero"),
        ]

    def __str__(self):
        return f"{self.produto}: {self.qtd_por_cento} {self.insumo.unidade} de {self.insumo}"
