from django.urls import path

from . import views

urlpatterns = [
    path("", views.menu, name="menu"),
    path("pedidos/novo/", views.novo_pedido, name="novo_pedido"),
    path("pedidos/<int:pedido_id>/avancar/", views.avancar, name="avancar_status"),
    path("painel/", views.painel, name="painel"),
    path("entregas/", views.entregas, name="entregas"),
]
