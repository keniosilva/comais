from django.contrib import admin

from .models import Cliente, ItemPedido, Pedido


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ("nome", "telefone")
    search_fields = ("nome",)


class ItemInline(admin.TabularInline):
    model = ItemPedido
    extra = 0
    readonly_fields = ("produto", "qtd_cento", "preco_cento")
    can_delete = False


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ("id", "cliente", "data_hora_entrega", "status", "valor_total")
    list_filter = ("status",)
    inlines = [ItemInline]
    # Pedidos são criados pela tela de Novo pedido, que aplica as regras e a baixa de insumos.
    readonly_fields = ("cliente", "usuario", "data_hora_entrega", "endereco_entrega", "valor_total", "criado_em")

    def has_add_permission(self, request):
        return False
