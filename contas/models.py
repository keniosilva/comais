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
