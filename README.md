# Minerva Travel

MVP local para gerar um guia de viagem infantil personalizado em PDF.

## Escopo atual

- Roteiro baseado em `docs/PEQUENOS_EXPLORADORES_EUROPA_2026 - PDF.pdf`.
- Frontend Vite/React com upload de foto, dados da familia, selecao de roteiro e preview.
- Capa e imagens dos pontos turisticos geradas por provider configuravel
  (`placeholder` ou `replicate`).
- Interpretacao de pontos turisticos em linguagem natural via OpenAI no backend.
- PDF organizado em momentos da viagem: antes, durante e depois, com dicas de idioma e atividades infantis por destino.
- PDF final para download no navegador.

## Instalar

```bash
uv sync --extra dev
cd frontend_atual/apps/web
npm install
```

## Gerar assets placeholder

```bash
python3 scripts/create_placeholder_assets.py
```

## Rodar backend

```bash
uv run uvicorn minerva_travel.app:app --reload --host 127.0.0.1 --port 8000
```

Backend: `http://localhost:8000`.

## Rodar frontend

```bash
cd frontend_atual/apps/web
cp .env.example .env
npm install
npm run dev
```

Frontend: `http://localhost:3000`.

O frontend usa `VITE_API_BASE_URL` para chamar o backend FastAPI.

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

## Variaveis de ambiente

Backend `.env`:

```env
IMAGE_PROVIDER=replicate
IMAGE_GENERATION_CONCURRENCY=2
REPLICATE_API_TOKEN=sua_chave_aqui
OPENAI_API_KEY=sua_chave_openai_aqui
OPENAI_LANDMARK_MODEL=gpt-4o-2024-08-06
CORS_ALLOW_ORIGINS=*
```

Com `IMAGE_PROVIDER=replicate`, o backend usa a foto enviada para gerar a capa,
gera uma imagem colorida em estilo aquarela para cada ponto turistico confirmado
e gera uma segunda imagem em line art preto e branco para a secao de colorir.
`IMAGE_GENERATION_CONCURRENCY` controla quantos pontos turisticos sao
processados em paralelo; comece com `2` para reduzir risco de rate limit.

Frontend `frontend_atual/apps/web/.env`:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
VITE_SUPABASE_URL=https://seu-projeto.supabase.co
VITE_SUPABASE_PUBLISHABLE_KEY=sb_publishable_sua_chave_aqui
```

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
```

Para deploy estatico ja publicado, tambem e possivel configurar Supabase
editando `public_html/config.js` no gerenciador de arquivos da Hostinger:

```js
window.__MINERVA_CONFIG__ = {
  VITE_SUPABASE_URL: 'https://seu-projeto.supabase.co',
  VITE_SUPABASE_PUBLISHABLE_KEY: 'sb_publishable_sua_chave_aqui',
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
