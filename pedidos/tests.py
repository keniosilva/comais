from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from catalogo.models import Insumo, Produto, Receita
from estoque.models import MovimentoEstoque
from estoque.services import ErroEstoque, insumos_abaixo_do_minimo, registrar_compra

from .models import Cliente, ItemPedido, Pedido
from .services import ErroPedido, criar_pedido, producao_do_dia

Usuario = get_user_model()
SENHA_TESTE = "senha-de-teste-123"  # usada só nos testes automatizados, não é credencial real


class BaseTeste(TestCase):
    def setUp(self):
        self.dono = Usuario.objects.create_user("dono.teste", password=SENHA_TESTE, perfil="dono")
        self.escritorio = Usuario.objects.create_user("esc.teste", password=SENHA_TESTE, perfil="escritorio")
        self.farinha = Insumo.objects.create(nome="Farinha", unidade="kg", estoque_atual=Decimal("10"), estoque_minimo=Decimal("5"))
        self.coxinha = Produto.objects.create(nome="Coxinha", preco_cento=Decimal("180.00"))
        Receita.objects.create(produto=self.coxinha, insumo=self.farinha, qtd_por_cento=Decimal("2"))
        self.cliente = Cliente.objects.create(nome="Cliente Teste", telefone="0000")
        self.entrega = timezone.now() + timedelta(days=3)

    def pedido(self, qtd="3", produto=None):
        return criar_pedido(
            usuario=self.dono, cliente=self.cliente, data_hora_entrega=self.entrega,
            endereco_entrega="Rua Exemplo, 100", itens=[(produto or self.coxinha, Decimal(qtd))],
        )


class RF06BaixaAutomaticaTests(BaseTeste):
    def test_pedido_baixa_insumos_pela_receita(self):
        # 3 cento x 2 kg por cento = 6 kg
        pedido = self.pedido("3")
        self.farinha.refresh_from_db()
        self.assertEqual(self.farinha.estoque_atual, Decimal("4"))
        mov = MovimentoEstoque.objects.get()
        self.assertEqual(mov.quantidade, Decimal("-6"))
        self.assertEqual(mov.pedido, pedido)
        self.assertEqual(mov.tipo, MovimentoEstoque.Tipo.BAIXA_PRODUCAO)
        self.assertEqual(pedido.valor_total, Decimal("540.00"))

    def test_falha_no_meio_nao_grava_nada(self):
        sem_receita = Produto.objects.create(nome="Risole", preco_cento=Decimal("170"))
        with self.assertRaises(ErroPedido):
            criar_pedido(
                usuario=self.dono, cliente=self.cliente, data_hora_entrega=self.entrega, endereco_entrega="",
                itens=[(self.coxinha, Decimal("1")), (sem_receita, Decimal("1"))],
            )
        self.farinha.refresh_from_db()
        self.assertEqual(self.farinha.estoque_atual, Decimal("10"))  # estoque intacto
        self.assertEqual(Pedido.objects.count(), 0)
        self.assertEqual(ItemPedido.objects.count(), 0)
        self.assertEqual(MovimentoEstoque.objects.count(), 0)


class RF04RegrasDoPedidoTests(BaseTeste):
    def test_quantidade_zero_ou_negativa_e_recusada(self):
        for qtd in ("0", "-1"):
            with self.assertRaises(ErroPedido):
                self.pedido(qtd)

    def test_data_passada_e_recusada(self):
        with self.assertRaises(ErroPedido):
            criar_pedido(usuario=self.dono, cliente=self.cliente, data_hora_entrega=timezone.now() - timedelta(hours=1),
                         endereco_entrega="", itens=[(self.coxinha, Decimal("1"))])

    def test_sem_itens_e_recusado(self):
        with self.assertRaises(ErroPedido):
            criar_pedido(usuario=self.dono, cliente=self.cliente, data_hora_entrega=self.entrega,
                         endereco_entrega="", itens=[])

    def test_produto_sem_receita_e_recusado(self):
        sem_receita = Produto.objects.create(nome="Risole", preco_cento=Decimal("170"))
        with self.assertRaises(ErroPedido):
            self.pedido("1", produto=sem_receita)

    def test_produto_repetido_e_recusado(self):
        with self.assertRaises(ErroPedido):
            criar_pedido(usuario=self.dono, cliente=self.cliente, data_hora_entrega=self.entrega, endereco_entrega="",
                         itens=[(self.coxinha, Decimal("1")), (self.coxinha, Decimal("2"))])

    def test_preco_e_copiado_para_o_item(self):
        pedido = self.pedido("1")
        self.coxinha.preco_cento = Decimal("999")
        self.coxinha.save()
        self.assertEqual(pedido.itens.get().preco_cento, Decimal("180.00"))

    def test_receita_unica_por_produto_e_insumo(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Receita.objects.create(produto=self.coxinha, insumo=self.farinha, qtd_por_cento=Decimal("1"))


class RF05ProducaoDoDiaTests(BaseTeste):
    def test_soma_pedidos_da_mesma_data_e_ignora_cancelados(self):
        self.farinha.estoque_atual = Decimal("100")
        self.farinha.save()
        p1 = self.pedido("3")
        self.pedido("2")
        cancelado = self.pedido("4")
        cancelado.status = Pedido.Status.CANCELADO
        cancelado.save()
        linhas = list(producao_do_dia(timezone.localtime(p1.data_hora_entrega).date()))
        self.assertEqual(len(linhas), 1)
        self.assertEqual(linhas[0]["produto__nome"], "Coxinha")
        self.assertEqual(linhas[0]["total"], Decimal("5"))  # 3 + 2, sem os 4 do cancelado


class RF07RF08EstoqueTests(BaseTeste):
    def test_compra_soma_ao_estoque_e_registra_movimento(self):
        registrar_compra(usuario=self.dono, insumo=self.farinha, quantidade=Decimal("25"))
        self.farinha.refresh_from_db()
        self.assertEqual(self.farinha.estoque_atual, Decimal("35"))
        mov = MovimentoEstoque.objects.get()
        self.assertEqual((mov.tipo, mov.usuario), (MovimentoEstoque.Tipo.COMPRA, self.dono))

    def test_compra_zero_e_recusada(self):
        with self.assertRaises(ErroEstoque):
            registrar_compra(usuario=self.dono, insumo=self.farinha, quantidade=Decimal("0"))

    def test_alerta_aparece_apos_baixa_e_sai_apos_compra(self):
        self.assertNotIn(self.farinha, insumos_abaixo_do_minimo())
        self.pedido("3")  # 10 - 6 = 4 (< mínimo 5)
        self.assertIn(self.farinha, insumos_abaixo_do_minimo())
        registrar_compra(usuario=self.dono, insumo=self.farinha, quantidade=Decimal("20"))
        self.assertNotIn(self.farinha, insumos_abaixo_do_minimo())


class AcessoEViewsTests(BaseTeste):
    def test_sem_login_redireciona_para_login(self):
        for nome in ("menu", "novo_pedido", "painel"):
            resp = self.client.get(reverse(nome))
            self.assertEqual(resp.status_code, 302)
            self.assertIn(reverse("login"), resp["Location"])

    def test_compra_restrita_ao_dono(self):
        url = reverse("compra", args=[self.farinha.pk])
        self.client.force_login(self.escritorio)
        self.assertEqual(self.client.post(url, {"quantidade": "5"}).status_code, 403)
        self.farinha.refresh_from_db()
        self.assertEqual(self.farinha.estoque_atual, Decimal("10"))
        self.client.force_login(self.dono)
        self.assertEqual(self.client.post(url, {"quantidade": "5"}).status_code, 302)
        self.farinha.refresh_from_db()
        self.assertEqual(self.farinha.estoque_atual, Decimal("15"))

    def test_botao_de_compra_nao_aparece_para_escritorio(self):
        self.client.force_login(self.escritorio)
        self.assertNotContains(self.client.get(reverse("painel")), "Registrar compra")
        self.client.force_login(self.dono)
        self.assertContains(self.client.get(reverse("painel")), "Registrar compra")

    def test_fluxo_completo_pela_tela(self):
        self.client.force_login(self.dono)
        quando = timezone.localtime(self.entrega)
        resp = self.client.post(reverse("novo_pedido"), {
            "cliente": self.cliente.pk,
            "data_entrega": quando.date().isoformat(), "hora_entrega": "14:00", "endereco_entrega": "Rua Exemplo, 100",
            "itens-TOTAL_FORMS": "3", "itens-INITIAL_FORMS": "0", "itens-MIN_NUM_FORMS": "0", "itens-MAX_NUM_FORMS": "1000",
            "itens-0-produto": self.coxinha.pk, "itens-0-qtd_cento": "3",
        }, follow=True)
        self.assertContains(resp, "Pedido salvo")
        self.assertContains(resp, "3 cento")
        self.assertEqual(Pedido.objects.count(), 1)

    def test_quantidade_invalida_mostra_erro_e_nao_grava(self):
        self.client.force_login(self.dono)
        quando = timezone.localtime(self.entrega)
        resp = self.client.post(reverse("novo_pedido"), {
            "cliente": self.cliente.pk,
            "data_entrega": quando.date().isoformat(), "hora_entrega": "14:00",
            "itens-TOTAL_FORMS": "3", "itens-INITIAL_FORMS": "0", "itens-MIN_NUM_FORMS": "0", "itens-MAX_NUM_FORMS": "1000",
            "itens-0-produto": self.coxinha.pk, "itens-0-qtd_cento": "0",
        })
        self.assertContains(resp, "Informe a quantidade em cento, com número maior que zero.")
        self.assertEqual(Pedido.objects.count(), 0)

    def test_texto_com_html_e_exibido_como_texto(self):
        self.cliente.nome = "<script>alert(1)</script>"
        self.cliente.save()
        self.client.force_login(self.dono)
        resp = self.client.get(reverse("novo_pedido"))
        self.assertNotContains(resp, "<script>alert(1)</script>")
        self.assertContains(resp, "&lt;script&gt;alert(1)&lt;/script&gt;")

    def test_senha_nao_fica_em_texto_simples(self):
        self.assertTrue(self.dono.password.startswith("pbkdf2_sha256$"))
        self.assertNotIn(SENHA_TESTE, self.dono.password)

    def test_logout_encerra_sessao(self):
        self.client.force_login(self.dono)
        self.client.post(reverse("logout"))
        self.assertEqual(self.client.get(reverse("menu")).status_code, 302)
