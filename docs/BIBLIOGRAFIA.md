# Piloto bibliográfico restrito

Adapter original em `scripts/bibliografia.py`; não copia nem instala a coleção
scientific-agent-skills. Referência técnica: K-Dense Inc., MIT, revisão
`a1043ef544e3a100c28e70a736b6cf32554d0677`,
`skills/literature-review/scripts/verify_citations.py`.
Não altera SKILL.md, validador existente, PR #1 ou schema de relatórios de fontes.

`consultar_doi(doi, transporte)` exige transporte explícito. Nos testes ele é Mock.
Não há CLI live, leitura de .env, token, LLM ou execução automática. O transporte
opcional `consultar_http` aceita somente endpoints canônicos de doi.org/Handle
e api.crossref.org/works. Recusa URLs arbitrárias, credenciais, portas, HTTP,
query e fragmentos; não segue redirects, usa timeout 5 s, corpo até 64 KiB,
sem proxies de ambiente, sem retries. São no máximo duas chamadas por DOI.
Uma aplicação que o invoque ainda precisa de autorização, orçamento, política
de egress/DNS e isolamento do host. Não é um serviço multi-tenant.

Estados: registro `registrado`, `ausente`, `inconclusivo`; metadados `obtidos` ou
`indisponiveis`. Ausência exige código Handle 100 com identidade correspondente.
Timeout, 403, redirects e identidades divergentes permanecem inconclusivos.
Crossref indisponível não invalida registro DOI confirmado. Sempre devolve
`suporte_alegacao=nao_avaliado`, `revisao_humana=pendente`. Nunca produz aprovação
do Evidence Kit, identidade verificada ou veredito factual.

Teste: `python -m unittest discover -s scripts -p 'test_*.py' -v`.
Fixtures são sintéticas; nenhum DOI foi consultado na rede. Falta homologar
HTTP real, DNS/egress, política de uso das APIs, identidade do revisor e suporte
semântico. Não usar para decisão clínica/jurídica ou publicação automática.

Triagem pendente upstream: relatório de segurança de 12/10/2026 e triagem com
revisão de setembro não coincidem. Achados do scanner não são vulnerabilidades
confirmadas nem podem ser descartados com a triagem anterior. Esta seleção não
audita as outras 176 skills, modelos/datasets ou suas licenças. Nenhuma nova
dependência científica, credencial, workflow ou integração de produção foi criada.
