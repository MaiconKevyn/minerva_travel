# Deploy na Hostinger

Este projeto fica em um unico repositorio, mas a Hostinger deve usar a branch
dedicada `hostinger-frontend`. Essa branch contem somente o app React/Vite, com
`package.json`, `index.html`, `vite.config.js`, `src/` e `public/` na raiz.

Isso evita o erro de "estrutura de projeto invalida" causado pela deteccao da
Hostinger em repositorios monorepo.

## Configuracao recomendada

No hPanel, conecte o GitHub ao site temporario e use:

```text
Repository: MaiconKevyn/minerva_travel
Branch: hostinger-frontend
Framework: Vite
Root directory: .
Install command: npm ci
Build command: npm run build
Output directory: dist
Node.js: 22.x
```

Use o preset `Vite` se existir. Se nao existir, use `React`. Se o painel ainda
nao detectar automaticamente, escolha `Other` e preencha os mesmos comandos
acima.

## Sincronizacao da branch

A branch `hostinger-frontend` e gerada a partir de:

```text
frontend_atual/apps/web
```

O workflow `.github/workflows/sync-hostinger-frontend.yml` atualiza essa branch
automaticamente quando a `main` recebe mudancas no frontend. Se o workflow
falhar por permissao, habilite em GitHub:

```text
Settings -> Actions -> General -> Workflow permissions -> Read and write permissions
```

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
