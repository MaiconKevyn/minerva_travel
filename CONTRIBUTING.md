# Contribuindo com o Minerva Travel

## Antes de alterar

1. Relacione a mudança a um ID de `PLANO_IMPLEMENTACAO.md` ou a uma decisão
   registrada.
2. Preserve alterações locais já existentes; não reformate arquivos fora do
   escopo.
3. Para mudanças de contrato, segurança, dados ou produto, registre rollout,
   rollback e compatibilidade antes da implementação.

## Ambiente e validação

Use Python 3.11 e Node 22 com os lockfiles da raiz:

```bash
uv sync --frozen --extra dev
npm ci
uv run ruff check .
uv run ruff format --check .
uv run mypy src/minerva_travel
uv run pytest --cov=minerva_travel --cov-fail-under=75
npm run lint --workspace minerva-travel-frontend
npm run test --workspace minerva-travel-frontend
npm run build --workspace minerva-travel-frontend
npm run test:e2e --workspace minerva-travel-frontend
python scripts/check_env_examples.py
```

Mudanças de PDF também exigem o smoke real, `pdfinfo`, `qpdf --check` e inspeção
visual da matriz afetada. Mudanças de migrations exigem
`bash scripts/check_supabase_migrations.sh` e teste RLS no ambiente Supabase.

## Dados e evidências

- Use somente famílias sintéticas ou dados com consentimento explícito.
- Nunca anexe foto, nome, token, payload livre ou log de produção ao PR.
- Screenshots e PDFs devem usar fixtures sintéticas e preservar créditos.
- Toda exceção de segurança precisa de owner, mitigação, teste e prazo em
  `docs/SECURITY_EXCEPTIONS.md`.

## Pull request

Preencha o template em `.github/pull_request_template.md`. Um PR não está pronto
se depender de segredo real, esconder falha de teste ou afirmar que um gate
manual/externo foi concluído sem evidência.
