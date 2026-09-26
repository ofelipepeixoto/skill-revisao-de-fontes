import unittest

from scripts.validar_relatorio import validar


class TestRelatorio(unittest.TestCase):
    def test_exige_evidencia_para_confirmacao(self):
        relatorio = {"fontes": [], "alegacoes": [{"texto": "Aprovado", "veredito": "confirmada", "fontes": []}]}
        self.assertTrue(any("sem fonte" in erro for erro in validar(relatorio)))

    def test_permite_abstencao(self):
        relatorio = {"fontes": [], "alegacoes": [{"texto": "Data de vigência", "veredito": "sem_evidencia", "fontes": []}]}
        self.assertEqual(validar(relatorio), [])

    def test_detecta_referencia_inexistente(self):
        relatorio = {"fontes": [], "alegacoes": [{"texto": "Aprovado", "veredito": "confirmada", "fontes": ["F1"]}]}
        self.assertTrue(any("inexistente" in erro for erro in validar(relatorio)))


if __name__ == "__main__":
    unittest.main()
