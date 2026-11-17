from datetime import datetime, time, timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Pedido
from .services import ErroPedido, avancar_status, criar_pedido, entregas_do_dia, producao_do_dia
from .tests import BaseTeste


class EntregasTests(BaseTeste):
    """RF09: lista de entregas do dia e status do pedido."""

    def setUp(self):
        super().setUp()
        self.farinha.estoque_atual = Decimal("100")
        self.farinha.save()
        self.dia = (timezone.localtime() + timedelta(days=2)).date()

    def pedido_as(self, hora):
        entrega = timezone.make_aware(datetime.combine(self.dia, time(hora, 0)))
        return criar_pedido(
            usuario=self.dono, cliente=self.cliente, data_hora_entrega=entrega,
            endereco_entrega="Rua Exemplo, 100", itens=[(self.coxinha, Decimal("1"))],
        )

    def test_lista_ordenada_por_horario_e_sem_cancelados(self):
        tarde = self.pedido_as(15)
        manha = self.pedido_as(9)
        cancelado = self.pedido_as(12)
        cancelado.status = Pedido.Status.CANCELADO
        cancelado.save()
        self.assertEqual(list(entregas_do_dia(self.dia)), [manha, tarde])

    def test_status_segue_a_sequencia_e_para_na_entrega(self):
        pedido = self.pedido_as(9)
        self.assertEqual(avancar_status(pedido).status, Pedido.Status.PRODUZIDO)
        self.assertEqual(avancar_status(pedido).status, Pedido.Status.ENTREGUE)
        with self.assertRaises(ErroPedido):
            avancar_status(pedido)

    def test_cancelado_nao_avanca(self):
        pedido = self.pedido_as(9)
        pedido.status = Pedido.Status.CANCELADO
        pedido.save()
        with self.assertRaises(ErroPedido):
            avancar_status(pedido)

    def test_pedido_produzido_sai_da_lista_de_producao(self):
        pedido = self.pedido_as(9)
        self.assertEqual(len(list(producao_do_dia(self.dia))), 1)
        avancar_status(pedido)
        self.assertEqual(len(list(producao_do_dia(self.dia))), 0)

    def test_sem_login_redireciona(self):
        resp = self.client.get(reverse("entregas"))
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse("login"), resp["Location"])

    def test_escritorio_ve_a_lista_mas_nao_altera_status(self):
        pedido = self.pedido_as(9)
        self.client.force_login(self.escritorio)
        resp = self.client.get(reverse("entregas"), {"data": self.dia.isoformat()})
        self.assertContains(resp, "Pendente")
        self.assertNotContains(resp, "Marcar como produzido")
        self.assertEqual(self.client.post(reverse("avancar_status", args=[pedido.pk])).status_code, 403)
        pedido.refresh_from_db()
        self.assertEqual(pedido.status, Pedido.Status.PENDENTE)

    def test_dono_atualiza_status_pela_tela(self):
        pedido = self.pedido_as(9)
        self.client.force_login(self.dono)
        resp = self.client.get(reverse("entregas"), {"data": self.dia.isoformat()})
        self.assertContains(resp, "Marcar como produzido")
        resp = self.client.post(reverse("avancar_status", args=[pedido.pk]), follow=True)
        self.assertContains(resp, "produzido")
        pedido.refresh_from_db()
        self.assertEqual(pedido.status, Pedido.Status.PRODUZIDO)

    def test_status_so_muda_por_post(self):
        pedido = self.pedido_as(9)
        self.client.force_login(self.dono)
        self.assertEqual(self.client.get(reverse("avancar_status", args=[pedido.pk])).status_code, 405)
