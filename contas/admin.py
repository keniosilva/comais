from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (("Perfil na Comais", {"fields": ("perfil",)}),)
    add_fieldsets = UserAdmin.add_fieldsets + (("Perfil na Comais", {"fields": ("perfil",)}),)
    list_display = ("username", "first_name", "perfil", "is_active")
