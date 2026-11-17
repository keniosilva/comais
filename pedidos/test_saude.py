from unittest import mock

from django.test import TestCase
from django.urls import reverse


class SaudeTests(TestCase):
    def test_responde_ok_sem_login(self):
        resp = self.client.get(reverse("saude"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {"status": "ok", "banco": "ok"})

    def test_responde_503_quando_o_banco_cai(self):
        with mock.patch("pedidos.views.connection.cursor", side_effect=Exception("banco fora")):
            resp = self.client.get(reverse("saude"))
        self.assertEqual(resp.status_code, 503)
        self.assertEqual(resp.json()["status"], "erro")
        self.assertNotIn("banco fora", resp.content.decode())  # não vaza detalhes
