from django.contrib.auth.models import AbstractUser
from django.db import models


class Usuario(AbstractUser):
    """Usuário do sistema. A senha é guardada como hash (PBKDF2 do Django)."""

    class Perfil(models.TextChoices):
        DONO = "dono", "Dono"
        ESCRITORIO = "escritorio", "Escritório"

    perfil = models.CharField(max_length=20, choices=Perfil.choices, default=Perfil.ESCRITORIO)

    @property
    def eh_dono(self):
        return self.perfil == self.Perfil.DONO


class ControleLogin(models.Model):
    """Contagem de falhas de login por nome de usuário digitado (RNF01).

    Guarda só o login informado, em minúsculas, e nunca a senha. Existe tanto para
    usuários reais quanto inexistentes, para não revelar quais logins estão cadastrados.
    """

    username = models.CharField(max_length=150, unique=True)
    falhas = models.PositiveSmallIntegerField(default=0)
    bloqueado_ate = models.DateTimeField(null=True, blank=True)
