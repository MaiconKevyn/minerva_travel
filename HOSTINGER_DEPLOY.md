# Deploy na Hostinger

O deploy da Hostinger deve usar o repositorio dedicado:

```text
MaiconKevyn/minerva-travel-frontend
```

Esse repo contem somente o app React/Vite, com `package.json`, `index.html`,
`vite.config.js`, `src/` e `public/` na raiz. Isso evita o erro de "estrutura de
projeto invalida" causado pela deteccao da Hostinger em repositorios monorepo.

## Configuracao recomendada

No hPanel, conecte o GitHub ao site temporario e use:

```text
Repository: MaiconKevyn/minerva-travel-frontend
Branch: main
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

O frontend dedicado foi publicado a partir de:

```text
frontend_atual/apps/web
```

Para sincronizar manualmente depois de alterar o frontend neste monorepo:

```text
git subtree split --prefix=frontend_atual/apps/web -b hostinger-frontend
git push frontend-hyphen hostinger-frontend:main
```

## Variaveis de ambiente

Adicione antes do build:

```env
VITE_API_BASE_URL=https://minerva-travel.onrender.com
VITE_GOOGLE_MAPS_BROWSER_KEY=sua_chave_publica_restrita_por_dominio
VITE_GOOGLE_MAPS_MAP_ID=seu_map_id_opcional
```

O Vite grava essa variavel dentro dos assets finais. Se ela mudar, faca um novo
build/redeploy.

`VITE_GOOGLE_MAPS_BROWSER_KEY` e necessaria para o botao "Ver mapa da viagem" no
passo 4. Use uma chave diferente da chave do backend, restrita por HTTP referrer
ao dominio temporario/final da Hostinger, com Maps JavaScript API habilitada.
`VITE_GOOGLE_MAPS_MAP_ID` e opcional, mas recomendado para exibir marcadores com
foto.

Se o deploy estatico ja estiver publicado, tambem e possivel preencher essas
variaveis em `public_html/config.js` no gerenciador de arquivos da Hostinger:

```js
window.__MINERVA_CONFIG__ = {
  VITE_SUPABASE_URL: 'https://seu-projeto.supabase.co',
  VITE_SUPABASE_PUBLISHABLE_KEY: 'sb_publishable_sua_chave_aqui',
  VITE_GOOGLE_MAPS_BROWSER_KEY: 'sua_chave_publica_restrita_por_dominio',
  VITE_GOOGLE_MAPS_MAP_ID: 'seu_map_id_opcional',
};
```

## Rotas internas

O arquivo `public/.htaccess` acompanha o build e redireciona rotas internas como
`/login`, `/create` e `/dashboard` para `index.html`. Isso evita 404 quando a
pagina e aberta diretamente no navegador.

## Backend e CORS

Enquanto o site estiver no dominio temporario da Hostinger, o backend pode usar:

```env
CORS_ALLOW_ORIGINS=*
```

Para a etapa de roteiro dinamico funcionar, configure no backend publicado
(Render ou equivalente), nao na Hostinger:

```env
GOOGLE_MAPS_API_KEY=sua_chave_google_maps_aqui
```

Essa chave tambem e usada pelo backend para retornar fotos do Google Places nos
cards do roteiro. A chave nao deve ir para o frontend nem para `config.js`; para
o mapa embutido, use `VITE_GOOGLE_MAPS_BROWSER_KEY`.

Quando houver dominio definitivo, prefira restringir:

```env
CORS_ALLOW_ORIGINS=https://seudominio.com,https://www.seudominio.com
```

## Arquivos que nao devem subir

Nao publique arquivos locais exportados pela Hostinger/Horizons, como ZIP/TAR,
`pb_data`, banco SQLite local ou binario do PocketBase. O deploy de produto usa
o frontend estatico e o backend FastAPI ja publicado no Render.
