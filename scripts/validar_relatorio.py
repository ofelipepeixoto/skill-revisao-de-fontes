"""Valida a estrutura de um relatório de fontes; não verifica fatos nem acessa URLs."""

import json
import re
import sys
from datetime import date
from ipaddress import ip_address
from pathlib import Path
from urllib.parse import urlsplit

VEREDITOS = {"confirmada", "parcial", "contradita", "sem_evidencia"}


def _texto_valido(valor):
    return isinstance(valor, str) and bool(valor.strip())


def _url_https_valida(url):
    """Confere somente a sintaxe; não consulta DNS nem acessa a URL."""
    if any(caractere.isspace() or ord(caractere) < 32 for caractere in url):
        return False
    try:
        partes = urlsplit(url)
        hostname = partes.hostname
        # A propriedade port também valida portas numéricas e seu intervalo.
        partes.port
        if partes.scheme != "https" or not partes.netloc or not hostname:
            return False
        try:
            ip_address(hostname)
            return True
        except ValueError:
            hostname = hostname.encode("idna").decode("ascii")
        if hostname.endswith("."):
            hostname = hostname[:-1]
        return len(hostname) <= 253 and all(
            re.fullmatch(r"[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?", parte)
            for parte in hostname.split(".")
        )
    except (ValueError, UnicodeError):
        return False


def _data_valida(valor):
    if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", valor):
        return False
    try:
        date.fromisoformat(valor)
    except ValueError:
        return False
    return True


def validar(relatorio):
    if not isinstance(relatorio, dict):
        return ["O relatório deve ser um objeto JSON"]
    erros = []
    fontes = relatorio.get("fontes", [])
    alegacoes = relatorio.get("alegacoes", [])
    if not isinstance(fontes, list) or not isinstance(alegacoes, list) or not alegacoes:
        return ["O relatório exige listas 'fontes' e 'alegacoes', com ao menos uma alegação"]
    ids = set()
    for fonte in fontes:
        if not isinstance(fonte, dict) or not all(_texto_valido(fonte.get(k)) for k in ("id", "url", "titulo", "emissor", "data_publicacao")):
            erros.append("Fonte exige id, url, titulo, emissor e data_publicacao como textos não vazios")
            continue
        if fonte["id"] in ids:
            erros.append(f"ID de fonte duplicado: {fonte['id']}")
        ids.add(fonte["id"])
        if not _url_https_valida(fonte["url"]):
            erros.append(f"URL HTTPS inválida ou sem hostname: {fonte['id']}")
        if not _data_valida(fonte["data_publicacao"]):
            erros.append(f"Data de publicação inválida (AAAA-MM-DD): {fonte['id']}")
    for indice, alegacao in enumerate(alegacoes, 1):
        if not isinstance(alegacao, dict) or not _texto_valido(alegacao.get("texto")):
            erros.append(f"Alegação {indice} sem texto")
            continue
        veredito = alegacao.get("veredito")
        evidencias = alegacao.get("fontes", [])
        if not isinstance(veredito, str) or veredito not in VEREDITOS or not isinstance(evidencias, list):
            erros.append(f"Alegação {indice} com veredito ou fontes inválidos")
            continue
        if veredito != "sem_evidencia" and not evidencias:
            erros.append(f"Alegação {indice} conclui sem fonte")
        if veredito == "sem_evidencia" and evidencias:
            erros.append(f"Alegação {indice} marca ausência, mas aponta fontes")
        for referencia in evidencias:
            if not _texto_valido(referencia):
                erros.append(f"Alegação {indice} com referência de fonte inválida")
            elif referencia not in ids:
                erros.append(f"Alegação {indice} referencia fonte inexistente: {referencia}")
    return erros


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Uso: python scripts/validar_relatorio.py relatorio.json")
    try:
        relatorio = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError, RecursionError) as erro:
        print(f"Não foi possível ler o relatório JSON: {erro}", file=sys.stderr)
        raise SystemExit(1)
    erros = validar(relatorio)
    print("Estrutura válida" if not erros else "\n".join(erros))
    raise SystemExit(bool(erros))
