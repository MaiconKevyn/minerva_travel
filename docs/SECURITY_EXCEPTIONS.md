# Exceções temporárias de segurança

Este registro existe para impedir que uma vulnerabilidade seja ignorada sem
escopo, mitigação, teste e prazo de revisão. Exceções não autorizam ampliar o
uso afetado.

## SEC-EX-001 — WeasyPrint / CVE-2026-49452

- Status: mitigada no uso atual; correção upstream ainda indisponível.
- Pacote afetado: `weasyprint <= 68.1`.
- Impacto publicado: injeção de CSS e possível requisição server-side quando
  HTML não confiável é processado com `presentational_hints=True`.
- Uso do projeto: `write_pdf` força explicitamente
  `presentational_hints=False`. O HTML é produzido por template Jinja com
  autoescape, e o `url_fetcher` aceita somente arquivos dentro das raízes
  internas aprovadas; rede e paths externos são recusados.
- Evidência automatizada:
  `tests/test_pdf_security.py::test_write_pdf_supplies_local_only_fetcher_to_weasyprint`
  verifica simultaneamente o fetcher restrito e a opção desabilitada.
- Exceção no scanner: apenas `CVE-2026-49452`, no comando `pip-audit` do CI.
- Owner: Engenharia.
- Próxima revisão obrigatória: 2026-08-10 ou imediatamente após uma nova versão
  do WeasyPrint, o que ocorrer primeiro.
- Critério de remoção: atualizar para a primeira versão corrigida, remover o
  `--ignore-vuln` e executar novamente a suíte PDF e o smoke no container.

Referência: <https://github.com/advisories/GHSA-jhhc-3hcp-qhm5>.
