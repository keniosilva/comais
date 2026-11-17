"""Cria dados FICTÍCIOS para demonstração e testes manuais.

Uso: python manage.py seed_demo --senha "uma-senha-local"
"""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from catalogo.models import Insumo, Produto, Receita
from estoque.services import registrar_compra
from pedidos.models import Cliente


class Command(BaseCommand):
    help = "Cria usuários, produtos, insumos, receitas e um cliente fictícios."

    def add_arguments(self, parser):
        parser.add_argument("--senha", required=True, help="Senha dos usuários de demonstração (não é gravada em texto).")

    def handle(self, *args, **opts):
        Usuario = get_user_model()
        for login, perfil in (("dono.demo", "dono"), ("escritorio.demo", "escritorio")):
            u, criado = Usuario.objects.get_or_create(username=login, defaults={"perfil": perfil})
            if criado:
                u.set_password(opts["senha"])  # grava apenas o hash
                u.save()
        dono = Usuario.objects.get(username="dono.demo")

        coxinha, _ = Produto.objects.get_or_create(nome="Coxinha", defaults={"preco_cento": Decimal("180.00")})
        risole, _ = Produto.objects.get_or_create(nome="Risole", defaults={"preco_cento": Decimal("170.00")})

        farinha, _ = Insumo.objects.get_or_create(nome="Farinha de trigo", defaults={"unidade": "kg", "estoque_minimo": Decimal("10")})
        frango, _ = Insumo.objects.get_or_create(nome="Frango", defaults={"unidade": "kg", "estoque_minimo": Decimal("8")})
        queijo, _ = Insumo.objects.get_or_create(nome="Queijo", defaults={"unidade": "kg", "estoque_minimo": Decimal("5")})

        receitas = [
            (coxinha, farinha, "2.000"), (coxinha, frango, "1.500"),
            (risole, farinha, "1.800"), (risole, queijo, "1.000"),
        ]
        for produto, insumo, qtd in receitas:
            Receita.objects.get_or_create(produto=produto, insumo=insumo, defaults={"qtd_por_cento": Decimal(qtd)})

        Cliente.objects.get_or_create(nome="Cliente Demo 1", defaults={"telefone": "(00) 00000-0000", "endereco": "Rua Exemplo, 100"})

        # Estoque inicial só se ainda estiver zerado (via compra, para manter o histórico).
        for insumo, qtd in ((farinha, "40"), (frango, "30"), (queijo, "12")):
            insumo.refresh_from_db()
            if insumo.estoque_atual == 0:
                registrar_compra(usuario=dono, insumo=insumo, quantidade=Decimal(qtd))

        self.stdout.write(self.style.SUCCESS("Dados de demonstração criados."))
