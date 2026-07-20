# Minerva Travel

MVP de diário/activity book infantil personalizado de viagem, em PDF A4.

## Escopo atual

- Roteiro baseado em `docs/PEQUENOS_EXPLORADORES_EUROPA_2026 - PDF.pdf`.
- Frontend Vite/React com upload de foto, dados da família, seleção de roteiro, rascunho
  seguro e painel de re-download.
- Capa e imagens dos pontos turisticos geradas por provider configuravel
  (`placeholder` ou `replicate`), com reaproveitamento de imagens Wikimedia
  quando houver uma foto representativa do ponto turistico.
- Interpretacao de pontos turisticos em linguagem natural via OpenAI no backend.
- PDF organizado em momentos da viagem: antes, durante e depois, com dicas de idioma e atividades infantis por destino.
- Jobs assíncronos, idempotentes e recuperáveis; o dashboard acompanha o status e o download.
- Rascunhos protegidos por owner, com expiração padrão de 14 dias; a foto não entra no
  rascunho e deve ser reenviada com consentimento antes da geração.

## Instalar

O ambiente de referencia usa Python 3.11.15 (fixado em `.python-version`) e Node
22. As dependencias Python devem ser instaladas a partir de `uv.lock`, sem
recalcular versoes:

```bash
uv sync --frozen --extra dev
cd frontend_atual/apps/web
npm ci
```

O WeasyPrint tambem depende de bibliotecas nativas. No macOS com Homebrew:

```bash
brew install glib pango cairo harfbuzz fontconfig libffi
```

Em Debian/Ubuntu:

```bash
sudo apt-get update
sudo apt-get install -y \
  fonts-dejavu-core libcairo2 libfontconfig1 libfreetype6 \
  libgdk-pixbuf-2.0-0 libglib2.0-0 libharfbuzz-subset0 libharfbuzz0b \
  libpango-1.0-0 libpangocairo-1.0-0 libpangoft2-1.0-0 shared-mime-info
```

Confirme o carregamento das bibliotecas e uma geracao real antes de iniciar o
backend:

```bash
uv run python -c "from weasyprint import HTML; HTML(string='<h1>Minerva</h1>').write_pdf('/tmp/minerva-smoke.pdf')"
uv run python scripts/smoke_pdf.py /tmp/minerva-guide-smoke.pdf
```

Se o macOS ainda informar que nao encontrou `libgobject-2.0-0`, confirme o
prefixo com `brew --prefix glib` e exponha as bibliotecas do Homebrew no mesmo
terminal:

```bash
export DYLD_FALLBACK_LIBRARY_PATH="$(brew --prefix)/lib:${DYLD_FALLBACK_LIBRARY_PATH:-}"
```

## Gerar assets placeholder

```bash
python3 scripts/create_placeholder_assets.py
```

Os ícones acima são fixtures offline de desenvolvimento. Para atualizar os
assets que podem ser publicados, baixe e registre as referências licenciadas do
catálogo com:

```bash
PYTHONPATH=src .venv/bin/python scripts/fetch_wikimedia_assets.py
```

O comando grava as imagens em `assets/wikimedia/` e a fonte, autor e licença em
`data/wikimedia/manifest.json`. A API de produção recusa gerar um guia se algum
landmark selecionado não tiver esse registro verificável.

## Rodar backend

```bash
uv run uvicorn minerva_travel.app:app --reload --host 127.0.0.1 --port 8000
```

Backend: `http://localhost:8000`.

O backend não publica mais uma segunda interface: `GET /` responde com redirecionamento
para o frontend e o antigo `POST /generate` responde `410`. Use sempre `/api/generate`.

### Rodar backend em container

O Dockerfile usa o mesmo Python do desenvolvimento e CI, inclui as bibliotecas
nativas do WeasyPrint e executa o processo com usuario nao root:

```bash
docker build --pull -t minerva-travel .
docker volume create minerva-travel-runtime
docker run --rm --name minerva-travel \
  -p 8000:8000 \
  -v minerva-travel-runtime:/app/runtime \
  minerva-travel
```

Para habilitar providers externos, acrescente `--env-file .env` ao comando
`docker run`. O healthcheck consulta `http://127.0.0.1:8000/api/catalog`; em outro
terminal, consulte o estado com:

```bash
docker inspect --format '{{.State.Health.Status}}' minerva-travel
```

## Rodar frontend

```bash
cd frontend_atual/apps/web
cp .env.example .env
npm ci
npm run dev
```

Frontend: `http://localhost:3000`.

O frontend usa `VITE_API_BASE_URL` para chamar o backend FastAPI.
A separação completa de variáveis entre frontend, API, worker, staging e
produção está em `docs/ENVIRONMENT_MATRIX.md`.

### Worker de geração

Em produção, `ASYNC_GUIDE_JOBS_ENABLED=true` faz o `POST /api/generate` retornar `202`
com `job_id`. Execute um processo worker separado com as mesmas variáveis de ambiente:

```bash
uv run python scripts/run_guide_worker.py
```

O worker aplica lease, retry exponencial para falhas transitórias e limite de tentativas.
Eventos JSON sem PII incluem `request_id`, `job_id`, estágio, duração e um hash do usuário.

O CI audita dependências, executa SAST e procura vulnerabilidades, segredos e
configurações inseguras. Exceções temporárias devem ter mitigação, teste e prazo
de revisão registrados em `docs/SECURITY_EXCEPTIONS.md`; exceções genéricas não
são aceitas.

## Preview do layout do PDF

Com o backend rodando, abra:

```text
http://127.0.0.1:8000/preview/sample
```

Essa rota renderiza o mesmo HTML/CSS usado na exportacao do PDF, facilitando ajustes visuais antes de gerar o arquivo final.

## Pontos turisticos livres

A API tambem aceita pontos turisticos fora do catalogo local. Envie `custom_landmarks`
como texto no `POST /api/generate`, um ponto por linha:

```text
Colosseum, Rome, Italy
Trevi Fountain, Rome, Italy
Sagrada Familia, Barcelona, Spain
```

O backend valida e estrutura esses itens em cidades/destinos internos, cria
`selection_id` automaticamente e gera as imagens dos pontos confirmados para
usar no PDF.

Tambem existe o fluxo em linguagem natural para o frontend:

```bash
curl -X POST http://127.0.0.1:8000/api/landmarks/parse \
  -H "Content-Type: application/json" \
  -d '{"message":"Em Paris queremos visitar Torre Eiffel, Louvre e Arco do Triunfo. Em Londres vamos ver Big Ben."}'
```

Esse endpoint chama a OpenAI pelo backend, separa os pontos turisticos e retorna
JSON estruturado para o frontend montar os cards de confirmacao. A chave da
OpenAI nunca deve ficar no frontend.

Para validar a estrutura antes de gerar o PDF:

```bash
curl -X POST http://127.0.0.1:8000/api/custom-landmarks/resolve \
  -H "Content-Type: application/json" \
  -d '{"landmarks":"Colosseum, Rome, Italy\nTrevi Fountain, Rome, Italy"}'
```

## Rodar tudo localmente

Terminal 1:

```bash
uv run uvicorn minerva_travel.app:app --reload --host 127.0.0.1 --port 8000
```

Terminal 2:

```bash
cd frontend_atual/apps/web
npm run dev
```

Depois abra:

```text
http://127.0.0.1:3000
```

## Geracao progressiva das paginas

Na etapa final, o frontend cria uma sessao privada e mostra uma pagina por vez.
Nada e gerado automaticamente: a familia solicita a capa, confere a imagem
completa e os textos, pode gerar ate quatro versoes e escolhe uma antes de
aprovar. Somente entao o fluxo libera o sumario ilustrado e, depois, as paginas
dos pontos turisticos. A conclusao retorna o manifesto das imagens aprovadas;
esse fluxo nao cria PDF.

A capa usa a foto enviada em `/v1/images/edits`, preservando sua composicao no prompt.
O sumario e as paginas seguintes usam `/v1/images/generations`. Todas as paginas
sao PNG verticais de 1024x1536, e os nomes/datas fazem parte do contrato do
prompt para serem renderizados dentro da propria imagem. Falhas da OpenAI ficam
visiveis e permitem nova tentativa; nao existe fallback para placeholder, foto
bruta ou geracao legada de PDF.

As sessoes, uploads e tentativas ficam no runtime privado, associados ao dono,
e seguem `GUIDE_DRAFT_RETENTION_DAYS`. O script de limpeza de guias tambem
remove sessoes expiradas. A implantacao atual deve usar uma unica instancia da
API enquanto essa persistencia estiver em disco local.

## Variaveis de ambiente

Backend `.env`:

```env
IMAGE_PROVIDER=replicate
LANDMARK_ART_GENERATION=false
LANDMARK_STYLIZED_ART=true
COLORING_LINEART_GENERATION=true
IMAGE_GENERATION_CONCURRENCY=2
REPLICATE_API_TOKEN=sua_chave_aqui
OPENAI_API_KEY=sua_chave_openai_aqui
OPENAI_LANDMARK_MODEL=gpt-4o-2024-08-06
OPENAI_IMAGE_MODEL=gpt-image-2
OPENAI_IMAGE_QUALITY=medium
OPENAI_IMAGE_TIMEOUT_SECONDS=180
# OPENAI_BASE_URL=https://api.openai.com/v1
GOOGLE_MAPS_API_KEY=sua_chave_google_maps_aqui
SUPABASE_URL=https://seu-projeto.supabase.co
SUPABASE_SERVICE_ROLE_KEY=sb_secret_sua_chave_aqui
SUPABASE_STORAGE_ENABLED=true
SUPABASE_BUCKET_LANDMARK_ASSETS=landmark-assets
SUPABASE_BUCKET_FAMILY_UPLOADS=family-uploads
SUPABASE_BUCKET_GENERATED_GUIDES=generated-guides
SUPABASE_BUCKET_GENERATED_COVERS=generated-covers
CORS_ALLOW_ORIGINS=https://minerva-travel.hostingerapp.com
FRONTEND_BASE_URL=https://minerva-travel.hostingerapp.com
GUIDE_RETENTION_DAYS=30
GUIDE_DRAFT_RETENTION_DAYS=14
ASYNC_GUIDE_JOBS_ENABLED=true
GUIDE_JOB_MAX_ATTEMPTS=3
OBSERVABILITY_HASH_SALT=gere_um_valor_unico_por_ambiente
```

Com `IMAGE_PROVIDER=replicate`, o backend usa a foto enviada para gerar a capa.
Por padrao, pontos turisticos nao geram imagem por IA: o PDF usa imagens
Wikimedia/licenciadas e sincroniza esses assets no bucket
`landmark-assets` quando o Supabase Storage esta configurado. Mantenha
`LANDMARK_ART_GENERATION=false` para reduzir custo e latencia. Se precisar
gerar arte/lineart premium para cada ponto, configure
`LANDMARK_ART_GENERATION=true`; nesse caso,
`IMAGE_GENERATION_CONCURRENCY` controla quantos pontos turisticos sao
processados em paralelo. A lineart premium e gerada como desenho editorial
limpo a partir do nome/local do ponto turistico, sem tracar a foto de
referencia, para evitar ruido fotografico e manter uma pagina realmente boa
para criancas colorirem.

`LANDMARK_STYLIZED_ART=true` transforma a foto real de cada ponto turistico
em ilustracao aquarela (flux-kontext) antes de montar o PDF, preservando a
arquitetura verdadeira do lugar. A arte e gerada uma unica vez por ponto no
mundo: o resultado fica em cache por `place_id` em `runtime/landmark-art/`
(camada local) e no bucket `landmark-assets` (camada duravel compartilhada),
com prefixo de versao de estilo (`stylized/v1/...`) para invalidar quando o
prompt visual mudar.

`COLORING_LINEART_GENERATION=true` mantem a lineart premium ativa para pontos
personalizados/dinamicos mesmo quando `LANDMARK_ART_GENERATION=false`. Isso evita
o fallback de bordas fotograficas em lugares como castelos, museus e igrejas,
onde a foto costuma virar um desenho pontilhado dificil de identificar.

`SUPABASE_SERVICE_ROLE_KEY` e usada somente no backend. Nunca coloque essa chave
em variaveis `VITE_`, no frontend publicado ou em `public_html/config.js`.

`GOOGLE_MAPS_API_KEY` e usada apenas pelo backend para montar roteiros dinamicos
com Geocoding API, Places API e fotos do Google Places nos cards da etapa de
roteiro. Nao coloque essa chave em variaveis `VITE_` nem no frontend publicado,
porque isso expoe o segredo no navegador.

Frontend `frontend_atual/apps/web/.env`:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
VITE_SUPABASE_URL=https://seu-projeto.supabase.co
VITE_SUPABASE_PUBLISHABLE_KEY=sb_publishable_sua_chave_aqui
VITE_GOOGLE_MAPS_BROWSER_KEY=sua_chave_publica_restrita_por_dominio
VITE_GOOGLE_MAPS_MAP_ID=seu_map_id_opcional
```

`VITE_GOOGLE_MAPS_BROWSER_KEY` e usada somente para o mapa embutido do passo 4
no navegador. Crie uma chave separada da chave do backend, restrinja por HTTP
referrer e habilite a Maps JavaScript API. `VITE_GOOGLE_MAPS_MAP_ID` e opcional,
mas recomendado para Advanced Markers.

## Deploy temporario na Hostinger

Use a branch estatica `hostinger-frontend` do repositorio
`MaiconKevyn/minerva_travel`. Ela contem o build Vite pronto na raiz e tambem
em `public_html/`, para ficar compativel com as duas configuracoes comuns da
Hostinger.

```text
Repository: MaiconKevyn/minerva_travel
Branch: hostinger-frontend
Root directory: public_html
```

Configure a variavel antes do build:

```env
VITE_API_BASE_URL=https://minerva-travel.onrender.com
VITE_SUPABASE_URL=https://seu-projeto.supabase.co
VITE_SUPABASE_PUBLISHABLE_KEY=sb_publishable_sua_chave_aqui
VITE_GOOGLE_MAPS_BROWSER_KEY=sua_chave_publica_restrita_por_dominio
VITE_GOOGLE_MAPS_MAP_ID=seu_map_id_opcional
```

Para deploy estatico ja publicado, tambem e possivel configurar Supabase
editando `public_html/config.js` no gerenciador de arquivos da Hostinger:

```js
window.__MINERVA_CONFIG__ = {
  VITE_SUPABASE_URL: 'https://seu-projeto.supabase.co',
  VITE_SUPABASE_PUBLISHABLE_KEY: 'sb_publishable_sua_chave_aqui',
  VITE_GOOGLE_MAPS_BROWSER_KEY: 'sua_chave_publica_restrita_por_dominio',
  VITE_GOOGLE_MAPS_MAP_ID: 'seu_map_id_opcional',
};
```

Para recuperacao de senha funcionar, configure no Supabase:

```text
Authentication > URL Configuration
Site URL: https://seu-dominio-ou-hostinger-temp
Redirect URLs: https://seu-dominio-ou-hostinger-temp/reset-password
```

Enquanto nao houver dominio definitivo, use o dominio temporario fornecido pelo
painel. Quando o dominio final existir, adicione-o no backend em
`CORS_ALLOW_ORIGINS`.
