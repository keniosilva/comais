from datetime import date, datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from catalogo.models import Insumo
from contas.permissions import dono_required
from estoque.services import insumos_abaixo_do_minimo

from .forms import ItemFormSet, PedidoForm
from .models import Pedido
from .services import (
    ErroPedido,
    avancar_status,
    criar_pedido,
    entregas_do_dia,
    producao_do_dia,
    total_pedidos_do_dia,
)


@login_required
def menu(request):
    """Tela 1: menu inicial com a função prioritária em destaque."""
    return render(request, "pedidos/menu.html", {"em_falta": insumos_abaixo_do_minimo().count()})


@login_required
def novo_pedido(request):
    """Tela 2: cadastro de encomenda (RF04). A validação é repetida aqui no servidor."""
    if request.method == "POST":
        form = PedidoForm(request.POST)
        formset = ItemFormSet(request.POST, prefix="itens")
        if form.is_valid() and formset.is_valid():
            itens = [(f.cleaned_data["produto"], f.cleaned_data["qtd_cento"]) for f in formset if f.cleaned_data]
            dados = form.cleaned_data
            entrega = timezone.make_aware(datetime.combine(dados["data_entrega"], dados["hora_entrega"]))
            try:
                criar_pedido(
                    usuario=request.user,
                    cliente=dados["cliente"],
                    data_hora_entrega=entrega,
                    endereco_entrega=dados["endereco_entrega"],
                    itens=itens,
                )
            except ErroPedido as erro:
                form.add_error(None, str(erro))
            else:
                messages.success(request, "Pedido salvo. Produção e estoque atualizados.")
                return redirect(f"{reverse('painel')}?data={dados['data_entrega'].isoformat()}")
    else:
        form = PedidoForm()
        formset = ItemFormSet(prefix="itens")
    return render(request, "pedidos/novo_pedido.html", {"form": form, "formset": formset})


def _data_da_requisicao(request):
    try:
        return date.fromisoformat(request.GET.get("data", ""))
    except ValueError:
        return timezone.localdate()


@login_required
def painel(request):
    """Tela 3: produção do dia (RF05) e estoque com alerta de mínimo (RF08)."""
    data = _data_da_requisicao(request)
    contexto = {
        "data": data,
        "producao": producao_do_dia(data),
        "total_pedidos": total_pedidos_do_dia(data),
        "insumos": Insumo.objects.all(),
    }
    return render(request, "pedidos/painel.html", contexto)


@login_required
def entregas(request):
    """RF09: entregas do dia por horário, com status. Escritório consulta; dono atualiza."""
    data = _data_da_requisicao(request)
    return render(request, "pedidos/entregas.html", {"data": data, "pedidos": entregas_do_dia(data)})


@dono_required
@require_POST
def avancar(request, pedido_id):
    """RF09: avança o status do pedido (pendente -> produzido -> entregue). Restrito ao dono."""
    pedido = get_object_or_404(Pedido, pk=pedido_id)
    try:
        novo = avancar_status(pedido)
    except ErroPedido as erro:
        messages.error(request, str(erro))
    else:
        messages.success(request, f"Pedido de {novo.cliente.nome}: {novo.get_status_display().lower()}.")
    data = timezone.localtime(pedido.data_hora_entrega).date().isoformat()
    return redirect(f"{reverse('entregas')}?data={data}")
