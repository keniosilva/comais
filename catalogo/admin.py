from django.contrib import admin

from .models import Insumo, Produto, Receita


class ReceitaInline(admin.TabularInline):
    model = Receita
    extra = 1


@admin.register(Produto)
class ProdutoAdmin(admin.ModelAdmin):
    list_display = ("nome", "preco_cento", "ativo")
    list_filter = ("ativo",)
    search_fields = ("nome",)
    inlines = [ReceitaInline]


@admin.register(Insumo)
class InsumoAdmin(admin.ModelAdmin):
    list_display = ("nome", "unidade", "estoque_atual", "estoque_minimo")
    search_fields = ("nome",)
    # O saldo muda apenas por movimentos de estoque (compra ou baixa), nunca por edição direta.
    readonly_fields = ("estoque_atual",)
