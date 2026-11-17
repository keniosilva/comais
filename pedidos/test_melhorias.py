"""Melhorias da 2ª rodada de validação: cliente novo na tela do pedido, aviso de estoque,
observação do pedido e total ao vivo."""
from datetime import timedelta
from decimal import Decimal

from django.urls import reverse
from django.utils import timezone

from .models import Cliente, Pedido
from .services import insumos_sem_saldo
from .tests import SENHA_TESTE, BaseTeste


class MelhoriasPedidoTests(BaseTeste):
    def setUp(self):
        super().setUp()
        self.client.login(username="esc.teste", password=SENHA_TESTE)
        amanha = timezone.localtime() + timedelta(days=3)
        self.base = {
            "data_entrega": amanha.date().isoformat(), "hora_entrega": "10:00", "endereco_entrega": "Rua Nova, 5",
            "itens-TOTAL_FORMS": "1", "itens-INITIAL_FORMS": "0", "itens-MIN_NUM_FORMS": "0", "itens-MAX_NUM_FORMS": "1000",
            "itens-0-produto": str(self.coxinha.pk), "itens-0-qtd_cento": "2",
        }

    def enviar(self, seguir=False, **extra):
        return self.client.post(reverse("novo_pedido"), {**self.base, **extra}, follow=seguir)

    def test_cliente_novo_e_criado_junto_com_o_pedido(self):
        resp = self.enviar(novo_cliente_nome="  Maria Festas ", novo_cliente_telefone="83 99999-0000", observacao="sem pimenta")
        self.assertEqual(resp.status_code, 302)
        cliente = Cliente.objects.get(nome="Maria Festas")
        pedido = Pedido.objects.get(cliente=cliente)
        self.assertEqual(pedido.observacao, "sem pimenta")
        self.assertEqual(cliente.endereco, "Rua Nova, 5")

    def test_sem_cliente_nenhum_pede_para_escolher(self):
        resp = self.enviar()
        self.assertContains(resp, "Escolha o cliente ou informe o nome de um cliente novo.")
        self.assertEqual(Pedido.objects.count(), 0)

    def test_cliente_novo_exige_telefone(self):
        resp = self.enviar(novo_cliente_nome="Maria")
        self.assertContains(resp, "Informe o telefone do cliente novo.")
        self.assertEqual(Cliente.objects.filter(nome="Maria").count(), 0)

    def test_escolher_e_cadastrar_ao_mesmo_tempo_e_recusado(self):
        resp = self.enviar(cliente=str(self.cliente.pk), novo_cliente_nome="Maria", novo_cliente_telefone="1")
        self.assertContains(resp, "não os dois")
        self.assertEqual(Pedido.objects.count(), 0)

    def test_falha_no_pedido_nao_deixa_cliente_novo_gravado(self):
        # quantidade acima do que o produto aceita não passa; já a data no passado cai no serviço
        ontem = (timezone.localtime() - timedelta(days=1)).date().isoformat()
        resp = self.enviar(novo_cliente_nome="Fantasma", novo_cliente_telefone="1", data_entrega=ontem)
        self.assertContains(resp, "devem estar no futuro")
        self.assertFalse(Cliente.objects.filter(nome="Fantasma").exists())

    def test_aviso_quando_o_estoque_fica_negativo(self):
        # estoque 10 kg; 6 cento x 2 kg = 12 kg
        resp = self.enviar(cliente=str(self.cliente.pk), seguir=True, **{"itens-0-qtd_cento": "6"})
        self.assertContains(resp, "Estoque insuficiente para este pedido: Farinha")

    def test_sem_aviso_quando_o_estoque_basta(self):
        resp = self.enviar(seguir=True, cliente=str(self.cliente.pk))
        self.assertNotContains(resp, "Estoque insuficiente")

    def test_insumos_sem_saldo_so_lista_os_do_pedido(self):
        pedido = self.pedido("6")  # 12 kg de 10
        self.assertEqual([i.nome for i in insumos_sem_saldo(pedido)], ["Farinha"])

    def test_observacao_aparece_na_lista_de_entregas(self):
        self.enviar(cliente=str(self.cliente.pk), observacao="sem pimenta")
        dia = Pedido.objects.get().data_hora_entrega.astimezone().date().isoformat()
        resp = self.client.get(reverse("entregas") + f"?data={dia}")
        self.assertContains(resp, "sem pimenta")

    def test_tela_traz_precos_para_o_total_ao_vivo(self):
        resp = self.client.get(reverse("novo_pedido"))
        self.assertContains(resp, 'id="precos"')
        self.assertContains(resp, "180.00")
        self.assertContains(resp, 'id="total"')
