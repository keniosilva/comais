from datetime import datetime, time, timedelta
from decimal import Decimal

from django.utils import timezone

from .services import criar_pedido, entregas_do_dia, intervalo_do_dia, producao_do_dia, total_pedidos_do_dia
from .tests import BaseTeste


class IntervaloDoDiaTests(BaseTeste):
    """Consultas por dia usam intervalo [início, fim), sem depender do fuso configurado no MySQL."""

    def setUp(self):
        super().setUp()
        self.farinha.estoque_atual = Decimal("100")
        self.farinha.save()
        self.dia = (timezone.localtime() + timedelta(days=3)).date()
        self.seguinte = self.dia + timedelta(days=1)

    def pedido_em(self, dia, hora, minuto=0):
        entrega = timezone.make_aware(datetime.combine(dia, time(hora, minuto)))
        return criar_pedido(
            usuario=self.dono, cliente=self.cliente, data_hora_entrega=entrega,
            endereco_entrega="", itens=[(self.coxinha, Decimal("1"))],
        )

    def test_intervalo_cobre_exatamente_24_horas(self):
        inicio, fim = intervalo_do_dia(self.dia)
        self.assertEqual(fim - inicio, timedelta(days=1))
        self.assertEqual(timezone.localtime(inicio).time(), time(0, 0))

    def test_limites_do_dia_ficam_no_dia_certo(self):
        ultimo_minuto = self.pedido_em(self.dia, 23, 59)
        meia_noite = self.pedido_em(self.seguinte, 0, 0)
        self.assertEqual(list(entregas_do_dia(self.dia)), [ultimo_minuto])
        self.assertEqual(list(entregas_do_dia(self.seguinte)), [meia_noite])

    def test_producao_e_total_respeitam_o_intervalo(self):
        self.pedido_em(self.dia, 23, 59)
        self.pedido_em(self.seguinte, 0, 0)
        self.assertEqual(total_pedidos_do_dia(self.dia), 1)
        self.assertEqual(total_pedidos_do_dia(self.seguinte), 1)
        self.assertEqual(list(producao_do_dia(self.dia))[0]["total"], Decimal("1"))

    def test_dia_sem_pedidos_retorna_vazio(self):
        self.pedido_em(self.dia, 10)
        self.assertEqual(total_pedidos_do_dia(self.seguinte + timedelta(days=5)), 0)
        self.assertEqual(list(producao_do_dia(self.seguinte + timedelta(days=5))), [])
