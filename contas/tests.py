from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .bloqueio import MAX_FALHAS
from .forms import MSG_BLOQUEADO, MSG_LOGIN_INVALIDO
from .models import ControleLogin

Usuario = get_user_model()
SENHA_CERTA = "senha-de-teste-123"  # usada só nos testes automatizados, não é credencial real


class BloqueioDeLoginTests(TestCase):
    """RNF01: 5 falhas seguidas bloqueiam o login por 15 minutos."""

    def setUp(self):
        Usuario.objects.create_user("dono.teste", password=SENHA_CERTA, perfil="dono")
        self.url = reverse("login")

    def tentar(self, senha, login="dono.teste"):
        return self.client.post(self.url, {"username": login, "password": senha})

    def test_login_valido_entra(self):
        self.assertEqual(self.tentar(SENHA_CERTA).status_code, 302)

    def test_login_invalido_mostra_mensagem_generica(self):
        resp = self.tentar("errada")
        self.assertContains(resp, MSG_LOGIN_INVALIDO)
        resp = self.tentar("errada", login="nao.existe")
        self.assertContains(resp, MSG_LOGIN_INVALIDO)  # mesma mensagem: não revela se o login existe

    def test_quinta_falha_bloqueia_ate_com_senha_correta(self):
        for _ in range(MAX_FALHAS):
            self.tentar("errada")
        resp = self.tentar(SENHA_CERTA)
        self.assertContains(resp, MSG_BLOQUEADO)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_quatro_falhas_nao_bloqueiam(self):
        for _ in range(MAX_FALHAS - 1):
            self.tentar("errada")
        self.assertEqual(self.tentar(SENHA_CERTA).status_code, 302)

    def test_login_correto_zera_a_contagem(self):
        for _ in range(MAX_FALHAS - 1):
            self.tentar("errada")
        self.tentar(SENHA_CERTA)
        self.client.post(reverse("logout"))
        for _ in range(MAX_FALHAS - 1):
            self.tentar("errada")
        self.assertEqual(self.tentar(SENHA_CERTA).status_code, 302)

    def test_bloqueio_expira_apos_o_prazo(self):
        for _ in range(MAX_FALHAS):
            self.tentar("errada")
        ControleLogin.objects.update(bloqueado_ate=timezone.now() - timedelta(seconds=1))
        self.assertEqual(self.tentar(SENHA_CERTA).status_code, 302)

    def test_bloqueio_e_por_login_e_nao_afeta_outros_usuarios(self):
        Usuario.objects.create_user("outro", password=SENHA_CERTA)
        for _ in range(MAX_FALHAS):
            self.tentar("errada")
        self.assertEqual(self.tentar(SENHA_CERTA, login="outro").status_code, 302)

    def test_login_nao_diferencia_maiusculas_no_controle(self):
        for _ in range(MAX_FALHAS):
            self.tentar("errada", login="DONO.TESTE")
        self.assertContains(self.tentar(SENHA_CERTA), MSG_BLOQUEADO)

    def test_senha_nunca_e_gravada_no_controle(self):
        self.tentar("senha-errada-secreta")
        controle = ControleLogin.objects.get()
        self.assertEqual((controle.username, controle.falhas), ("dono.teste", 1))
        self.assertNotIn("senha-errada-secreta", str(controle.__dict__))
