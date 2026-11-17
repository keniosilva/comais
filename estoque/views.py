from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.decorators.http import require_POST

from catalogo.models import Insumo
from contas.permissions import dono_required

from .services import ErroEstoque, registrar_compra
from .forms import CompraForm


@dono_required
@require_POST
def compra(request, insumo_id):
    """RF07: registra a compra de um insumo. Restrito ao perfil dono."""
    insumo = get_object_or_404(Insumo, pk=insumo_id)
    form = CompraForm(request.POST)
    destino = f"{reverse('painel')}#estoque"
    if not form.is_valid():
        for erros in form.errors.values():
            for erro in erros:
                messages.error(request, f"{insumo.nome}: {erro}")
        return redirect(destino)
    try:
        registrar_compra(usuario=request.user, insumo=insumo, quantidade=form.cleaned_data["quantidade"])
    except ErroEstoque as erro:
        messages.error(request, f"{insumo.nome}: {erro}")
    else:
        messages.success(request, f"Compra registrada: {insumo.nome}, +{form.cleaned_data['quantidade'].normalize()} {insumo.unidade}.")
    return redirect(destino)
