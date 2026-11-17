from django import forms
from django.contrib.auth.forms import AuthenticationForm

from . import bloqueio

MSG_LOGIN_INVALIDO = "Login ou senha incorretos."
MSG_BLOQUEADO = "Muitas tentativas. Aguarde 15 minutos e tente novamente."


class FormLogin(AuthenticationForm):
    """Login com mensagem genérica (não revela se o erro foi no login ou na senha) e bloqueio por tentativas."""

    error_messages = {
        **AuthenticationForm.error_messages,
        "invalid_login": MSG_LOGIN_INVALIDO,
    }

    def clean(self):
        username = bloqueio.normalizar(self.data.get(self.username_field.name, ""))
        if bloqueio.esta_bloqueado(username):
            raise forms.ValidationError(MSG_BLOQUEADO, code="bloqueado")
        try:
            dados = super().clean()
        except forms.ValidationError:
            bloqueio.registrar_falha(username)
            raise
        bloqueio.limpar(username)
        return dados
