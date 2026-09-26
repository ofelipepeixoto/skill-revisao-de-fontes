"""Valida a estrutura de um relatório de fontes; não verifica fatos ou URLs."""

import json
import sys
from pathlib import Path

VEREDITOS = {"confirmada", "parcial", "contradita", "sem_evidencia"}


def validar(relatorio):
    erros = []
    fontes = relatorio.get("fontes", [])
    alegacoes = relatorio.get("alegacoes", [])
    if not isinstance(fontes, list) or not isinstance(alegacoes, list) or not alegacoes:
        return ["O relatório exige listas 'fontes' e 'alegacoes' não vazias"]
    ids = set()
    for fonte in fontes:
        if not isinstance(fonte, dict) or not all(fonte.get(k) for k in ("id", "url", "titulo", "emissor", "data_publicacao")):
            erros.append("Fonte sem id, url, titulo, emissor ou data_publicacao")
            continue
        if fonte["id"] in ids:
            erros.append(f"ID de fonte duplicado: {fonte['id']}")
        ids.add(fonte["id"])
        if not fonte["url"].startswith("https://"):
            erros.append(f"URL não HTTPS: {fonte['id']}")
    for indice, alegacao in enumerate(alegacoes, 1):
        if not isinstance(alegacao, dict) or not alegacao.get("texto"):
            erros.append(f"Alegação {indice} sem texto")
            continue
        veredito = alegacao.get("veredito")
        evidencias = alegacao.get("fontes", [])
        if veredito not in VEREDITOS or not isinstance(evidencias, list):
            erros.append(f"Alegação {indice} com veredito ou fontes inválidos")
            continue
        if veredito != "sem_evidencia" and not evidencias:
            erros.append(f"Alegação {indice} conclui sem fonte")
        if veredito == "sem_evidencia" and evidencias:
            erros.append(f"Alegação {indice} marca ausência, mas aponta fontes")
        for referencia in evidencias:
            if referencia not in ids:
                erros.append(f"Alegação {indice} referencia fonte inexistente: {referencia}")
    return erros


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Uso: python scripts/validar_relatorio.py relatorio.json")
    erros = validar(json.loads(Path(sys.argv[1]).read_text(encoding="utf-8")))
    print("Estrutura válida" if not erros else "\n".join(erros))
    raise SystemExit(bool(erros))
