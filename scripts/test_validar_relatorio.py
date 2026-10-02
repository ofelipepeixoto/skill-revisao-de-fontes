import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.validar_relatorio import validar


class TestRelatorio(unittest.TestCase):
    def relatorio_valido(self):
        return {
            "fontes": [{
                "id": "F1", "url": "https://example.com/ficticio",
                "titulo": "Comunicado", "emissor": "Empresa Exemplo",
                "data_publicacao": "2026-01-01",
            }],
            "alegacoes": [{"texto": "Há um comunicado", "veredito": "confirmada", "fontes": ["F1"]}],
        }

    def test_exige_evidencia_para_confirmacao(self):
        relatorio = {"fontes": [], "alegacoes": [{"texto": "Aprovado", "veredito": "confirmada", "fontes": []}]}
        self.assertTrue(any("sem fonte" in erro for erro in validar(relatorio)))

    def test_permite_abstencao(self):
        relatorio = {"fontes": [], "alegacoes": [{"texto": "Data de vigência", "veredito": "sem_evidencia", "fontes": []}]}
        self.assertEqual(validar(relatorio), [])

    def test_detecta_referencia_inexistente(self):
        relatorio = {"fontes": [], "alegacoes": [{"texto": "Aprovado", "veredito": "confirmada", "fontes": ["F1"]}]}
        self.assertTrue(any("inexistente" in erro for erro in validar(relatorio)))

    def test_exemplo_documentado_valido(self):
        exemplo = Path(__file__).resolve().parents[1] / "exemplos" / "relatorio_ficticio.json"
        self.assertEqual(validar(json.loads(exemplo.read_text(encoding="utf-8"))), [])

    def test_raizes_malformadas_retornam_erros(self):
        for raiz in ([], None, 1, True, "relatorio"):
            with self.subTest(raiz=raiz):
                self.assertTrue(any("objeto JSON" in erro for erro in validar(raiz)))

    def test_listas_malformadas_e_ausencia_de_alegacoes(self):
        for campo, valor in (("fontes", None), ("fontes", {}), ("alegacoes", "texto"), ("alegacoes", [])):
            with self.subTest(campo=campo, valor=valor):
                relatorio = self.relatorio_valido()
                relatorio[campo] = valor
                self.assertTrue(validar(relatorio))

    def test_fontes_e_campos_malformados_nao_lancam_excecao(self):
        for fonte in (None, [], 1, "fonte"):
            with self.subTest(fonte=fonte):
                relatorio = self.relatorio_valido()
                relatorio["fontes"] = [fonte]
                self.assertTrue(validar(relatorio))
        for campo in ("id", "url", "titulo", "emissor", "data_publicacao"):
            for valor in (None, 42, False, [], {}, "", " "):
                with self.subTest(campo=campo, valor=valor):
                    relatorio = self.relatorio_valido()
                    relatorio["fontes"][0][campo] = valor
                    self.assertTrue(validar(relatorio))

    def test_alegacoes_e_campos_malformados_nao_lancam_excecao(self):
        for alegacao in (None, [], 1, "alegacao"):
            with self.subTest(alegacao=alegacao):
                relatorio = self.relatorio_valido()
                relatorio["alegacoes"] = [alegacao]
                self.assertTrue(validar(relatorio))
        for campo, valores in (
            ("texto", (None, 42, [], {}, " ")),
            ("veredito", (None, 42, [], {}, "desconhecido")),
            ("fontes", (None, 42, {}, "F1")),
        ):
            for valor in valores:
                with self.subTest(campo=campo, valor=valor):
                    relatorio = self.relatorio_valido()
                    relatorio["alegacoes"][0][campo] = valor
                    self.assertTrue(validar(relatorio))

    def test_referencias_malformadas_nao_lancam_excecao(self):
        for referencia in (None, 42, False, [], {}, "", " "):
            with self.subTest(referencia=referencia):
                relatorio = self.relatorio_valido()
                relatorio["alegacoes"][0]["fontes"] = [referencia]
                self.assertTrue(any("referência de fonte inválida" in erro for erro in validar(relatorio)))

    def test_detecta_ids_duplicados(self):
        relatorio = self.relatorio_valido()
        relatorio["fontes"].append(dict(relatorio["fontes"][0]))
        self.assertTrue(any("duplicado" in erro for erro in validar(relatorio)))

    def test_abstencao_com_evidencia_inconsistente(self):
        relatorio = self.relatorio_valido()
        relatorio["alegacoes"][0]["veredito"] = "sem_evidencia"
        self.assertTrue(any("ausência, mas aponta fontes" in erro for erro in validar(relatorio)))

    def test_datas_invalidas_e_formatos_alternativos(self):
        for data_publicacao in ("not-a-date", "2026-02-31", "2023-02-29", "0000-01-01", "2026-13-01", "20260101", "2026-W01-1", "01/01/2026", "2026-01-01T00:00:00"):
            with self.subTest(data_publicacao=data_publicacao):
                relatorio = self.relatorio_valido()
                relatorio["fontes"][0]["data_publicacao"] = data_publicacao
                self.assertTrue(any("Data de publicação inválida" in erro for erro in validar(relatorio)))

    def test_datas_validas_incluem_ano_bissexto(self):
        for data_publicacao in ("2024-02-29", "2026-12-31"):
            with self.subTest(data_publicacao=data_publicacao):
                relatorio = self.relatorio_valido()
                relatorio["fontes"][0]["data_publicacao"] = data_publicacao
                self.assertEqual(validar(relatorio), [])

    def test_urls_sem_hostname_ou_sintaxe_invalida(self):
        for url in ("https://", "https:///caminho", "https://?q=1", "https://#fragmento", "https://user@", "https://exa mple.com", "https://example.com\n/caminho", "https://[invalid]", "https://example.com:abc", "https://example.com:65536", "https://.example.com", "https://example..com", "https://-example.com"):
            with self.subTest(url=url):
                relatorio = self.relatorio_valido()
                relatorio["fontes"][0]["url"] = url
                self.assertTrue(any("URL HTTPS inválida" in erro for erro in validar(relatorio)))

    def test_protocolos_nao_https(self):
        for url in ("http://example.com", "ftp://example.com", "file:///tmp/documento", "//example.com", "example.com", "javascript:alert(1)"):
            with self.subTest(url=url):
                relatorio = self.relatorio_valido()
                relatorio["fontes"][0]["url"] = url
                self.assertTrue(any("URL HTTPS inválida" in erro for erro in validar(relatorio)))

    def test_urls_https_validas_sem_consultar_rede(self):
        for url in ("https://example.com", "https://example.com:443/pagina?q=1#trecho", "HTTPS://example.com/pagina", "https://exemplo.test", "https://café.example", "https://127.0.0.1", "https://[::1]/pagina"):
            with self.subTest(url=url):
                relatorio = self.relatorio_valido()
                relatorio["fontes"][0]["url"] = url
                self.assertEqual(validar(relatorio), [])


class TestCLI(unittest.TestCase):
    def executar(self, caminho):
        script = Path(__file__).with_name("validar_relatorio.py")
        return subprocess.run([sys.executable, str(script), str(caminho)], capture_output=True, text=True, check=False)

    def test_cli_raiz_lista_retorna_erro_sem_traceback(self):
        with tempfile.TemporaryDirectory() as diretorio:
            caminho = Path(diretorio) / "relatorio.json"
            caminho.write_text("[]", encoding="utf-8")
            resultado = self.executar(caminho)
        self.assertEqual(resultado.returncode, 1)
        self.assertIn("objeto JSON", resultado.stdout)
        self.assertNotIn("Traceback", resultado.stderr)

    def test_cli_json_invalido_retorna_erro_util(self):
        with tempfile.TemporaryDirectory() as diretorio:
            caminho = Path(diretorio) / "relatorio.json"
            caminho.write_text("{", encoding="utf-8")
            resultado = self.executar(caminho)
        self.assertEqual(resultado.returncode, 1)
        self.assertIn("Não foi possível ler o relatório JSON", resultado.stderr)
        self.assertNotIn("Traceback", resultado.stderr)

    def test_cli_arquivo_ausente_retorna_erro_util(self):
        with tempfile.TemporaryDirectory() as diretorio:
            resultado = self.executar(Path(diretorio) / "ausente.json")
        self.assertEqual(resultado.returncode, 1)
        self.assertIn("Não foi possível ler o relatório JSON", resultado.stderr)
        self.assertNotIn("Traceback", resultado.stderr)

    def test_cli_inteiro_acima_do_limite_retorna_erro_util(self):
        limite = getattr(sys, "get_int_max_str_digits", lambda: 0)()
        if not limite:
            self.skipTest("Este Python não limita dígitos de inteiros JSON")
        with tempfile.TemporaryDirectory() as diretorio:
            caminho = Path(diretorio) / "relatorio.json"
            caminho.write_text('{"valor":' + "1" * (limite + 1) + '}', encoding="utf-8")
            resultado = self.executar(caminho)
        self.assertEqual(resultado.returncode, 1)
        self.assertIn("Não foi possível ler o relatório JSON", resultado.stderr)
        self.assertNotIn("Traceback", resultado.stderr)

    def test_cli_json_aninhado_acima_do_limite_retorna_erro_util(self):
        # Python 3.12 tem um limite do parser C distinto do limite Python.
        profundidade = max(10000, sys.getrecursionlimit() * 2)
        with tempfile.TemporaryDirectory() as diretorio:
            caminho = Path(diretorio) / "relatorio.json"
            caminho.write_text("[" * profundidade + "0" + "]" * profundidade, encoding="utf-8")
            resultado = self.executar(caminho)
        self.assertEqual(resultado.returncode, 1)
        self.assertIn("Não foi possível ler o relatório JSON", resultado.stderr)
        self.assertNotIn("Traceback", resultado.stderr)

    def test_cli_exemplo_documentado(self):
        exemplo = Path(__file__).resolve().parents[1] / "exemplos" / "relatorio_ficticio.json"
        resultado = self.executar(exemplo)
        self.assertEqual(resultado.returncode, 0)
        self.assertEqual(resultado.stdout.strip(), "Estrutura válida")


if __name__ == "__main__":
    unittest.main()
