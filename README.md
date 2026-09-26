# Revisão de fontes — skill autoral

Habilidade pública para auditar afirmações de textos e relatórios. Orienta a separar fatos, opiniões e previsões; confrontar cada alegação com fonte primária; marcar evidência insuficiente; e entregar um relatório rastreável.

## Estrutura

- [`SKILL.md`](SKILL.md): instruções para o assistente.
- [`scripts/validar_relatorio.py`](scripts/validar_relatorio.py): confere campos, vereditos e referências do relatório JSON. **Não** acessa URLs ou verifica a verdade das afirmações.
- [`scripts/test_validar_relatorio.py`](scripts/test_validar_relatorio.py): testa ausência de evidência, abstenção e referência inexistente.

## Exemplo de uso

> Revise as afirmações factuais deste texto, localize as fontes primárias, distinga proposta de aprovação e diga quais alegações não podem ser confirmadas.

Para validar a estrutura de um relatório JSON:

```bash
python scripts/validar_relatorio.py exemplos/relatorio_ficticio.json
python -m unittest -v scripts/test_validar_relatorio.py
```

O exemplo é inteiramente fictício. Uma verificação real exige pesquisa nas fontes pertinentes; passar no validador não prova que a alegação é verdadeira.

## Referências e autoria

O fluxo e o código deste repositório foram escritos para este projeto. A organização em `SKILL.md` e recursos foi inspirada no conceito público de [Agent Skills](https://github.com/anthropics/skills). Nenhum texto ou código das skills de terceiros foi copiado. Verifique as licenças de cada pasta antes de reutilizar materiais externos.
