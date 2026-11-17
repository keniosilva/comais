from django.urls import path

from . import views

urlpatterns = [
    path("<int:insumo_id>/compra/", views.compra, name="compra"),
]
