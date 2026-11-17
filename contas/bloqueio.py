"""Bloqueio temporário após tentativas de login inválidas (RNF01).

Regra: 5 falhas seguidas para o mesmo login bloqueiam novas tentativas por 15 minutos.
Um login correto zera a contagem. O controle é por login (não por IP), então fica
protegido mesmo atrás de proxy; o custo é que um terceiro pode bloquear um login por 15 min.
"""
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from .models import ControleLogin

MAX_FALHAS = 5
DURACAO_BLOQUEIO = timedelta(minutes=15)


def normalizar(username):
    return (username or "").strip().lower()[:150]


def esta_bloqueado(username):
    username = normalizar(username)
    if not username:
        return False
    controle = ControleLogin.objects.filter(username=username).first()
    return bool(controle and controle.bloqueado_ate and controle.bloqueado_ate > timezone.now())


@transaction.atomic
def registrar_falha(username):
    username = normalizar(username)
    if not username:
        return
    controle, _ = ControleLogin.objects.select_for_update().get_or_create(username=username)
    # Bloqueio já expirado: recomeça a contagem.
    if controle.bloqueado_ate and controle.bloqueado_ate <= timezone.now():
        controle.falhas = 0
        controle.bloqueado_ate = None
    controle.falhas += 1
    if controle.falhas >= MAX_FALHAS:
        controle.bloqueado_ate = timezone.now() + DURACAO_BLOQUEIO
    controle.save()


def limpar(username):
    ControleLogin.objects.filter(username=normalizar(username)).delete()
