# Matriz de configuração por componente e ambiente

Os arquivos `.env.example` são a fonte executável dos nomes. O comando
`python scripts/check_env_examples.py` falha quando o código passa a ler uma
variável não documentada. Valores reais nunca devem ser versionados.

## Perfis

| Componente | Desenvolvimento | Staging | Produção |
|---|---|---|---|
| Frontend | `VITE_APP_ENV=development`, `VITE_AUTH_MODE=local` ou Supabase de sandbox | `VITE_APP_ENV=staging`, `VITE_AUTH_MODE=supabase` | `VITE_APP_ENV=production`, `VITE_AUTH_MODE=supabase` |
| API | `APP_ENV=development`; controles podem ser desativados para execução offline | `APP_ENV=staging`; autenticação e controles ativados | `APP_ENV=production`; autenticação, consentimento, idempotência, jobs e controles são obrigatórios |
| Worker | Pode usar providers placeholder e storage local | Mesmo banco/storage da API de staging | Mesmo banco/storage da API; processo independente e continuamente supervisionado |

## Frontend público

| Variável | Obrigatória em produção | Uso |
|---|---:|---|
| `VITE_API_BASE_URL` | sim | Origem HTTPS da API |
| `VITE_APP_ENV` | sim | Bloqueia modos de identidade de desenvolvimento |
| `VITE_AUTH_MODE` | sim | Deve ser `supabase` |
| `VITE_SUPABASE_URL` | sim | Projeto Supabase do ambiente |
| `VITE_SUPABASE_PUBLISHABLE_KEY` | sim | Chave pública; nunca usar service role |
| `VITE_GOOGLE_MAPS_BROWSER_KEY` | quando mapa embutido estiver ativo | Chave pública restrita por domínio e API |
| `VITE_GOOGLE_MAPS_MAP_ID` | quando Advanced Markers estiver ativo | Identificador público do mapa |

## API e worker

| Grupo | Variáveis principais | API | Worker |
|---|---|:---:|:---:|
| Ambiente | `APP_ENV`, `FRONTEND_BASE_URL`, `CORS_ALLOW_ORIGINS` | ✓ | — |
| Identidade | `AUTH_REQUIRED`, `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY`, `SUPABASE_JWT_AUDIENCE` | ✓ | — |
| Dados privados | `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_STORAGE_ENABLED`, `SUPABASE_BUCKET_LANDMARK_ASSETS` | ✓ | ✓ |
| Geração | `IMAGE_PROVIDER`, `REPLICATE_API_TOKEN`, `IMAGE_GENERATION_CONCURRENCY`, flags de lineart | ✓ | ✓ |
| IA e mapas | `OPENAI_API_KEY`, `OPENAI_LANDMARK_MODEL`, `OPENAI_IMAGE_MODEL`, `OPENAI_IMAGE_QUALITY`, `OPENAI_IMAGE_TIMEOUT_SECONDS`, `OPENAI_BASE_URL`, `GOOGLE_MAPS_API_KEY` | ✓ | ✓ |
| Upload | `IMAGE_UPLOAD_MAX_BYTES`, `IMAGE_UPLOAD_MAX_PIXELS`, `IMAGE_UPLOAD_MAX_WIDTH`, `IMAGE_UPLOAD_MAX_HEIGHT` | ✓ | ✓ |
| Jobs | `ASYNC_GUIDE_JOBS_ENABLED`, `GUIDE_JOB_MAX_ATTEMPTS` | ✓ | ✓ |
| Retenção | `GUIDE_RETENTION_DAYS`, `GUIDE_DRAFT_RETENTION_DAYS` | ✓ | ✓ |
| Controles | `REQUEST_CONTROL_*`, `RATE_LIMIT_*`, `QUOTA_*`, `CONCURRENCY_*`, `IDEMPOTENCY_*` | ✓ | — |
| Privacidade | `PHOTO_PROCESSING_CONSENT_REQUIRED`, `OBSERVABILITY_HASH_SALT` | ✓ | ✓ |

## Regras de promoção

- Staging e produção usam projetos, buckets, chaves e bancos distintos.
- `SUPABASE_SERVICE_ROLE_KEY`, tokens de providers e salt de observabilidade são
  secrets do servidor; não recebem prefixo `VITE_`.
- Produção não inicia com auth local, consentimento desativado, controles
  desativados ou geração síncrona.
- Toda alteração de variável exige atualização do `.env.example`, desta matriz,
  do ambiente de deploy e do rollback correspondente.
- Antes da promoção: executar `uv sync --frozen --extra dev`, `npm ci`, o CI
  completo e o smoke pós-deploy sem secrets de produção em logs.
