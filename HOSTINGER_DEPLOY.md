# Deploy do frontend na Hostinger

Este projeto deve ficar em um unico repositorio. A Hostinger deve publicar
apenas o frontend React/Vite em `frontend_atual/apps/web`.

## Configuracao recomendada

No hPanel, conecte o GitHub ao site temporario e use:

```text
Repository: MaiconKevyn/minerva_travel
Branch: main
Root directory: frontend_atual/apps/web
Install command: npm ci
Build command: npm run build
Output directory: dist
Node.js: 22.x
```

Use o preset `Vite` se existir. Se nao existir, use `React`. Se o painel pedir
somente arquivos estaticos, publique o conteudo gerado em `dist`.

## Variaveis de ambiente

Adicione antes do build:

```env
VITE_API_BASE_URL=https://minerva-travel.onrender.com
```

O Vite grava essa variavel dentro dos assets finais. Se ela mudar, faca um novo
build/redeploy.

## Rotas internas

O arquivo `public/.htaccess` acompanha o build e redireciona rotas internas como
`/login`, `/create` e `/dashboard` para `index.html`. Isso evita 404 quando a
pagina e aberta diretamente no navegador.

## Backend e CORS

Enquanto o site estiver no dominio temporario da Hostinger, o backend pode usar:

```env
CORS_ALLOW_ORIGINS=*
```

Quando houver dominio definitivo, prefira restringir:

```env
CORS_ALLOW_ORIGINS=https://seudominio.com,https://www.seudominio.com
```

## Arquivos que nao devem subir

Nao publique arquivos locais exportados pela Hostinger/Horizons, como ZIP/TAR,
`pb_data`, banco SQLite local ou binario do PocketBase. O deploy de produto usa
o frontend estatico e o backend FastAPI ja publicado no Render.
