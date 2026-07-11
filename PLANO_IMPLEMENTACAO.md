# Plano de Implementação — Minerva Travel

> Baseline da auditoria: 09/07/2026
> Estado-alvo: MVP seguro, reproduzível, observável e apto para piloto pago
> Regra de liberação: nenhum item P0 pode permanecer aberto antes de tráfego público ou cobrança

## 1. Objetivo e uso deste documento

Este documento transforma a auditoria técnica, de IA, produto e UX em um backlog executável. Cada frente contém:

- implementação necessária;
- dependências;
- checkpoints de entrega;
- critérios objetivos de aceite;
- validações manuais;
- testes automatizados;
- gate de liberação associado.

Os identificadores, como SEC-01 e PDF-01, devem ser preservados ao criar issues, mudanças OpenSpec, branches, PRs e dashboards de acompanhamento.

### Legenda

| Símbolo | Significado |
|---|---|
| [ ] | Não iniciado |
| [~] | Em andamento |
| [x] | Concluído e validado |
| P0 | Bloqueia exposição pública, dados reais ou cobrança |
| P1 | Necessário para MVP operacional |
| P2 | Necessário para qualidade, escala e piloto |
| P3 | Evolução ou redução de dívida |

## Progresso de implementação — 10/07/2026

### Entregue e verificado neste workspace

- Fundação: Docker multi-stage, Python 3.11/Node 22 fixados, CI de backend/frontend,
  smoke de PDF A4 com `pdfinfo`, `qpdf` e renderização.
- Segurança e privacidade: JWT Supabase em produção, owner scope, uploads sanitizados,
  SSRF restrito, rate limit/quota/concorrência/idempotência, consentimento versionado,
  exportação e exclusão de conta.
- PDF e conteúdo: roteiro revisado chega ao PDF A4, assets Wikimedia licenciados e
  rastreáveis, lineart local baseada na referência e créditos legíveis.
- Operação: jobs persistidos, canceláveis, idempotentes e recuperáveis com lease, backoff,
  limite de tentativas e telemetria JSON sem PII; worker separado e dashboard autenticado.
- UX: feedback acessível nos campos críticos, skip link, navegação móvel nomeada, rascunho
  protegido/restaurável/descartável, polling de progresso e orçamento de bundle no CI.
- Acessibilidade automatizada: Playwright + axe em Chromium desktop/mobile cobre as rotas
  públicas, skip link e cadastro → login → wizard; contraste e alvos do carrossel foram
  corrigidos e o fluxo respeita `prefers-reduced-motion`.
- Supply chain: `pip-audit`, `npm audit`, Bandit e Trivy (filesystem/container/segredos)
  fazem parte do CI. `python-multipart` e `starlette` foram atualizados; a exceção restrita
  do WeasyPrint está documentada em `docs/SECURITY_EXCEPTIONS.md` com mitigação e prazo.
- Frontend: código morto de Integrated AI/PocketBase removido; Supabase é a única identidade
  de produção e o bundle principal caiu para aproximadamente 250 kB sem gzip.
- Qualidade: migrações Supabase verificadas estaticamente; suíte Python e frontend, lint,
  build e E2E local executados com sucesso (273 testes Python, 107 frontend e 18 browser,
  cobertura global de 82,79% e typecheck de 30 módulos).
  A evidência mais recente está registrada nas mensagens desta tarefa e nos artefatos locais
  de `runtime/`.

### Ainda dependente de decisão ou infraestrutura externa

- DEC-01 a DEC-13: posicionamento comercial, mercado, marca/domínio, moeda/impostos,
  retenção legal, storage/queue de produção, pagamento e política de reembolso.
- Aplicar e exercitar as migrations/RLS em um projeto Supabase temporário; o CLI/credenciais
  de Supabase não estão disponíveis neste workspace.
- Escolher e homologar checkout/webhook/entitlements com provedor real antes de qualquer
  cobrança; o produto permanece corretamente sinalizado como piloto sem checkout.
- Configurar drain de logs, alertas, staging/produção, secrets e execução contínua do worker.
- Fazer validação humana de acessibilidade (VoiceOver/NVDA/TalkBack), pagamentos e o piloto
  com famílias consentidas. Esses gates não podem ser concluídos por código local.

### Definição global de pronto

Um item somente pode ser marcado como concluído quando:

- [ ] código, migrations, configuração e documentação foram entregues;
- [ ] testes unitários, integração e regressão relacionados passaram;
- [ ] critérios de acessibilidade aplicáveis foram verificados;
- [ ] logs, métricas e alertas necessários foram adicionados;
- [ ] nenhum segredo ou dado pessoal aparece em logs;
- [ ] rollout, rollback e compatibilidade com dados existentes foram definidos;
- [ ] validação ocorreu no mesmo tipo de ambiente usado em produção;
- [ ] evidências de teste foram anexadas ao PR ou mudança OpenSpec;
- [ ] comportamento real e copy do produto continuam equivalentes.

## 2. Estado de partida

### Baseline conhecido

- Frontend React/Vite: 70 testes passaram, ESLint passou e build de produção concluiu.
- Bundle principal atual: aproximadamente 795 kB minificado e 232 kB gzip.
- Backend: 89 testes independentes do renderer passaram.
- Suíte completa Python: bloqueada na coleta pela ausência de bibliotecas nativas do WeasyPrint.
- Ruff: 9 violações no baseline auditado.
- API publicada: catálogo disponível.
- Preview publicado: responde, mas todos os 51 assets de imagem observados estavam quebrados.
- PDF local mais recente: estruturalmente válido, porém em Letter, não tagueado e com capa/mapa/lineart provisórios.
- Workspace auditado: 10 arquivos modificados e 3 não rastreados já pertenciam ao trabalho em andamento.

### Restrições até o Gate G2

- Não abrir geração paga ao público.
- Não afirmar que existe checkout seguro sem cobrança real.
- Não processar fotos reais de crianças sem consentimento, retenção e exclusão implementados.
- Não liberar add-on por booleano controlado pelo navegador.
- Não promover o PDF como personalizado enquanto o fallback normal entregar silhuetas ou desenhos genéricos.
- Não adicionar novas integrações pagas antes de autenticação, quota e telemetria de custo.

## 3. Decisões bloqueantes de produto e arquitetura

Estas decisões devem ser registradas em ADR ou OpenSpec antes das implementações dependentes.

- [ ] DEC-01 — Posicionar oficialmente o produto como activity book/diário infantil personalizado de viagem.
- [ ] DEC-02 — Definir mercado inicial: Brasil, Portugal ou outro mercado único.
- [ ] DEC-03 — Unificar nome do produto, empresa, domínio, idioma e identidade visual.
- [ ] DEC-04 — Definir moeda única, impostos, preço-base e política de reembolso.
- [ ] DEC-05 — Definir faixa etária suportada; recomendação inicial: 3 a 12 anos.
- [ ] DEC-06 — Definir se a foto será obrigatória e oferecer alternativa de capa sem foto.
- [ ] DEC-07 — Definir A4 como padrão ou permitir escolha explícita A4/Letter.
- [ ] DEC-08 — Adotar uma única fonte de verdade para autenticação, usuários, guias e painel; recomendação: Supabase.
- [ ] DEC-09 — Escolher banco, object storage, queue/worker e mecanismo de rate limit.
- [ ] DEC-10 — Definir política de retenção por tipo de dado e estado do pedido.
- [ ] DEC-11 — Escolher provedor de pagamento e fluxo de piloto gratuito, pago ou por cupom.
- [ ] DEC-12 — Escolher política de fallback da capa: foto original sanitizada, capa sem foto ou ilustração explicitamente genérica.
- [ ] DEC-13 — Definir quais funções ficam no MVP e quais serão ocultadas ou marcadas como beta.

### Escopo recomendado do MVP

Incluído:

- autenticação ou draft convidado com vinculação posterior;
- destinos estruturados com ordem, período e duração;
- ritmo e interesses;
- composição familiar inclusiva;
- seleção e confirmação de atrações;
- capa validada e fallback honesto;
- PDF com roteiro, atividades, idioma e memória;
- preview, pagamento único, persistência e re-download;
- privacidade, consentimento, retenção e exclusão;
- instrumentação do funil e da geração.

Fora do MVP ou beta:

- sugestão avançada de rota por IA;
- restaurantes pagos;
- álbum com várias fotos e histórias;
- editor avançado do PDF;
- reservas, preços e disponibilidade em tempo real;
- expansão irrestrita de idiomas, destinos e atividades.

## 4. Arquitetura-alvo

~~~mermaid
flowchart LR
    U["Usuário / Browser"] --> FE["Frontend React"]
    FE --> AUTH["Supabase Auth"]
    FE --> API["FastAPI autenticado"]
    API --> GUARD["JWT + autorização + quota + idempotência"]
    GUARD --> DB["Postgres / RLS"]
    GUARD --> Q["Queue de geração"]
    Q --> W["Worker"]
    W --> AI["OpenAI / Replicate"]
    W --> GEO["Google Places / Wikimedia"]
    W --> PDF["Renderer PDF restrito"]
    W --> OBJ["Object Storage privado"]
    PAY["Checkout"] --> WH["Webhook validado"]
    WH --> DB
    DB --> DASH["Dashboard / status / entitlement"]
    OBJ --> DL["Download autenticado ou URL assinada"]
    API --> OBS["Logs, traces, métricas e custos"]
    W --> OBS
~~~

## 5. Ordem de execução e gates

| Fase | Conteúdo | Dependência | Gate de saída |
|---|---|---|---|
| F0 | Baseline, ambientes, contratos e CI | decisões iniciais | G0 |
| F1 | Segurança, privacidade, uploads e SSRF | F0 | G1 |
| F2 | Fidelidade da capa, roteiro e PDF | F1 | G2 |
| F3 | Persistência, jobs, storage e dashboard | F1/F2 | G3 |
| F4 | UX, acessibilidade, responsividade e performance | F2/F3 | G4 |
| F5 | Pagamento, entitlement e operação comercial | F3/F4 | G5 |
| F6 | IA, qualidade de código, documentação, analytics e piloto | F1–F5 | G6 |

---

# F0 — Fundação reproduzível

## BASE-01 — Preservar e registrar o baseline

**Prioridade:** P0
**Dependências:** nenhuma

### Implementação

- [ ] Criar branch de trabalho sem sobrescrever as alterações existentes.
- [ ] Registrar arquivos modificados/não rastreados e mudanças OpenSpec ativas.
- [ ] Salvar resultados atuais de testes, lint, build, tamanho do bundle e PDF de referência.
- [ ] Definir owner para cada frente deste plano.

### Checkpoints

- [ ] CP1 — git diff --check sem erros.
- [ ] CP2 — baseline de testes anexado à primeira issue/PR.
- [ ] CP3 — nenhum arquivo existente foi descartado ou reformatado fora de escopo.

### Aceite e testes

- O trabalho atual pode ser reproduzido ou comparado durante toda a implementação.
- Toda regressão futura possui uma referência objetiva.

## BASE-02 — Fixar runtimes e dependências nativas

**Prioridade:** P0
**Dependências:** DEC-09

### Implementação

- [ ] Escolher e fixar uma versão Python validada com WeasyPrint.
- [ ] Fixar Node 22 em desenvolvimento, CI e produção.
- [ ] Declarar glib, pango, cairo, harfbuzz, fontconfig e demais dependências nativas.
- [ ] Criar Dockerfile multi-stage com usuário não root e healthcheck.
- [ ] Atualizar README com instalação macOS/Linux e diagnóstico do WeasyPrint.
- [ ] Manter uv.lock e package-lock.json como fontes reprodutíveis.

### Checkpoints

- [ ] CP1 — clone limpo instala dependências sem passos implícitos.
- [ ] CP2 — import de minerva_travel.app funciona no container.
- [ ] CP3 — um PDF real é gerado dentro do container.
- [ ] CP4 — runtimes local, CI e produção são equivalentes.

### Testes

- [ ] Build da imagem a partir de cache vazio.
- [ ] uv sync --frozen --extra dev.
- [ ] npm ci com Node 22.
- [ ] pytest completo incluindo app, itinerary e PDF.
- [ ] Smoke test de Uvicorn, health e geração de PDF.
- [ ] pdfinfo, qpdf --check e renderização com pdftoppm.

## BASE-03 — CI/CD completo

**Prioridade:** P0
**Dependências:** BASE-02

### Implementação

- [x] Adicionar job Python: Ruff check/format, typecheck, pytest e cobertura.
- [x] Manter job frontend: npm ci, lint, testes e build.
- [x] Adicionar geração e inspeção real de PDF.
- [x] Adicionar Playwright desktop/mobile.
- [x] Adicionar SAST, SCA, secret scan e scan do container.
- [x] Publicar screenshots, logs sanitizados e PDFs sintéticos como artefatos.
- [ ] Ativar branch protection para gates críticos.

### Checkpoints

- [ ] CP1 — pipeline executa em pull request e main.
- [x] CP2 — nenhuma etapa depende de segredo real em PR externo.
- [ ] CP3 — ambiente sandbox real roda periodicamente com orçamento limitado.

### Aceite

- Nenhum merge crítico ocorre com testes, segurança ou PDF quebrados.

## API-01 — Contratos tipados e compartilhados

**Prioridade:** P0
**Dependências:** BASE-02

### Implementação

- [x] Criar modelos Pydantic de request e response para todos os endpoints.
- [x] Padronizar erro com code, message, field_errors e request_id.
- [x] Centralizar limites de responsáveis, crianças, destinos, landmarks, ano e upload.
- [x] Gerar cliente frontend a partir de OpenAPI ou validar JSDoc/TypeScript contra o schema.
- [ ] Versionar contratos incompatíveis.
- [x] Garantir que entrada inválida resulte em 4xx, nunca 500.

**Estado validado em 10/07/2026:** o envelope de erro global e sua documentação no OpenAPI
estão cobertos por testes de validação e 404. Todos os endpoints JSON sob `/api/` agora
expõem modelos de resposta concretos, inclusive a união síncrona/assíncrona da geração.
Entradas JSON malformadas em toda a superfície de escrita e multipart incompleto retornam
422 no envelope comum. O formulário multipart de geração também é consolidado em um modelo
Pydantic com limites testados antes do processamento da imagem. O cliente gerado/validado
contra o schema usa um snapshot OpenAPI determinístico: o CI rejeita snapshot desatualizado
e os testes frontend verificam operações e campos consumidos. O versionamento de mudanças
incompatíveis continua pendente. Limites de família, destinos, landmarks, ano e upload têm
fonte única em `contract_limits.py`, são publicados no OpenAPI e comparados ao frontend.

### Checkpoints

- [x] CP1 — snapshot do OpenAPI aprovado.
- [x] CP2 — frontend não possui limites contraditórios ao backend.
- [ ] CP3 — erros 400/422 apontam os campos causadores.

### Testes

- [x] Contract tests frontend ↔ backend.
- [ ] Payload mínimo, máximo e campos desconhecidos.
- [ ] IDs desconhecidos, listas vazias, textos extensos e tipos incorretos.
- [ ] Compatibilidade com drafts existentes.

### Gate G0 — Fundação

- [ ] Ambiente limpo executa backend, frontend e renderer.
- [ ] CI completo está verde.
- [ ] Contratos e limites são únicos.
- [ ] PDF sintético real é produzido no ambiente de produção.

---

# F1 — Segurança, privacidade e confiança

## SEC-01 — Autenticação e autorização no FastAPI

**Prioridade:** P0
**Dependências:** DEC-08, API-01

### Implementação

- [x] Validar JWT Supabase por JWKS, issuer, audience, expiração e assinatura.
- [x] Criar dependência get_current_user.
- [x] Proteger geração, parsing OpenAI, descoberta Google, restaurantes, jobs e downloads.
- [x] Manter públicos apenas catálogo, páginas públicas e healthchecks.
- [x] Fazer o frontend enviar Authorization: Bearer e renovar sessão.
- [x] Desabilitar autenticação local e PocketBase em produção.
- [x] Aplicar autorização por owner em guia, job, asset e download.

### Checkpoints

- [x] CP1 — endpoint caro sem token retorna 401 antes de chamar provedor.
- [ ] CP2 — token válido identifica o usuário no job e no audit log.
- [x] CP3 — usuário B não acessa recursos do usuário A.

### Testes

- [x] Token ausente, expirado, adulterado, audience/issuer incorretos.
- [x] Token de outro projeto.
- [x] Acesso cruzado a job, guia, PDF e draft.
- [ ] Refresh de sessão e logout.
- [x] CORS preflight autenticado.

## SEC-02 — Rate limit, quota, concorrência e idempotência

**Prioridade:** P0
**Dependências:** SEC-01, DEC-09

### Implementação

- [x] Definir limites por usuário e IP para cada endpoint caro.
- [x] Definir quota de guias/créditos e concorrência por usuário.
- [x] Implementar limite global por provedor.
- [x] Retornar 429 com Retry-After e mensagem acionável.
- [ ] Exigir Idempotency-Key na criação de job e checkout.
- [ ] Registrar consumo, custo estimado e motivo de bloqueio.

### Checkpoints

- [x] CP1 — rajada não inicia trabalhos excedentes.
- [x] CP2 — retry com a mesma chave retorna o mesmo job.
- [x] CP3 — limites podem ser configurados por ambiente e plano.

### Testes

- [x] Rajada por IP e usuário.
- [x] Requisições paralelas com a mesma chave.
- [x] Limite de concorrência de Replicate/Google/OpenAI.
- [x] Quota esgotada e reset da quota.
- [x] Failover do armazenamento do rate limit.

## SEC-03 — Upload seguro de imagens

**Prioridade:** P0
**Dependências:** API-01

### Implementação

- [ ] Aplicar limite de corpo no proxy e FastAPI; referência inicial: 10 MB.
- [x] Ler em chunks e abortar assim que o limite for excedido.
- [x] Validar assinatura real, MIME, extensão, dimensões e quantidade de pixels.
- [x] Aceitar apenas JPEG, PNG e WebP anunciados.
- [x] Tratar decompression bombs, truncamento e arquivos vazios.
- [x] Corrigir orientação, reencodar e remover EXIF/GPS.
- [x] Gerar nome e extensão exclusivamente no servidor.
- [x] Exibir validação equivalente no frontend antes do upload.

### Checkpoints

- [x] CP1 — arquivo inválido é rejeitado antes do provedor externo.
- [x] CP2 — imagem persistida não contém EXIF.
- [x] CP3 — upload grande não cresce memória sem limite.

### Testes

- [x] Arquivo acima do limite, vazio, falso JPG, SVG e binário.
- [x] JPEG/PNG/WebP válidos em portrait e landscape.
- [x] Decompression bomb e dimensões extremas.
- [x] Nome malicioso e path traversal.
- [x] Upload simultâneo e cancelamento.

## SEC-04 — Eliminar SSRF e restringir WeasyPrint

**Prioridade:** P0
**Dependências:** API-01

### Implementação

- [ ] Remover URL arbitrária do modelo final do PDF.
- [ ] Referenciar imagens por asset_id interno e owner.
- [ ] Criar downloader central: HTTPS, allowlist, timeout, limite de bytes e MIME real.
- [ ] Resolver DNS e bloquear loopback, link-local, redes privadas e IPv6 local.
- [ ] Revalidar cada redirect ou desabilitá-lo.
- [x] Criar url_fetcher do WeasyPrint que aceite somente diretórios/objetos aprovados.
- [x] Bloquear rede, file:// fora da raiz, ftp e esquemas desconhecidos.
- [ ] Garantir que fallbacks nunca preservem URL não validada.

### Checkpoints

- [x] CP1 — somente paths/bytes internos chegam a img src no template.
- [x] CP2 — render do PDF não dispara rede.
- [ ] CP3 — testes ofensivos passam no CI.

### Testes

- [x] localhost, 127.0.0.1, ::1 e IP privado.
- [x] 169.254.169.254 e link-local.
- [x] file:///etc, URL codificada e hostname ambíguo.
- [ ] Redirect permitido → IP privado.
- [ ] DNS rebinding simulado.
- [ ] MIME falso, arquivo grande e timeout.

## SEC-05 — Artefatos privados e download autorizado

**Prioridade:** P0
**Dependências:** SEC-01, DATA-01

### Implementação

- [x] Remover download público baseado apenas em UUID.
- [x] Exigir owner no endpoint de download.
- [x] Usar URL assinada de curta duração ou streaming autorizado.
- [x] Evitar enumeração de IDs e nomes previsíveis.
- [x] Definir expiração e comportamento de re-download.

### Testes

- [x] Acesso cruzado entre dois usuários.
- [x] URL expirada, adulterada e reutilizada.
- [x] Guia excluído e artefato ausente.
- [x] Headers Content-Type, Content-Disposition, cache e filename.

## PRIV-01 — LGPD/GDPR, consentimento e ciclo de vida

**Prioridade:** P0
**Dependências:** DEC-02, DEC-10

### Implementação

- [ ] Inventariar dado, finalidade, base legal, owner, localização e subprocessador.
- [x] Classificar nomes, idades e fotos familiares.
- [x] Publicar Política de Privacidade e Termos com rotas funcionais.
- [x] Informar explicitamente quais provedores recebem foto/texto.
- [x] Obter consentimento do responsável antes do upload.
- [x] Não usar fotos para treinamento sem consentimento separado.
- [x] Implementar exportação e exclusão de conta/guia.
- [ ] Implementar retenção e limpeza automática por estado.
- [x] Redigir PII de logs, analytics, erros e suporte.
- [ ] Definir processo de incidente e canal de contato.

### Checkpoints

- [ ] CP1 — revisão jurídica do mercado escolhido.
- [x] CP2 — exclusão remove banco, upload, capa, PDF e cache.
- [x] CP3 — consentimento possui versão e timestamp.

### Testes

- [x] Exclusão end-to-end e reconciliação de órfãos.
- [x] Analytics sem nomes, foto ou texto livre.
- [x] Busca por PII em logs de teste.
- [ ] Retenção de draft, falha, guia pronto e reembolso.

## SEC-06 — Segredos, CORS, headers e supply chain

**Prioridade:** P1
**Dependências:** BASE-03

### Implementação

- [x] Restringir CORS aos domínios oficiais por ambiente.
- [x] Adicionar CSP, HSTS, X-Content-Type-Options, Referrer-Policy e Permissions-Policy.
- [ ] Confirmar restrição por referrer e quota da chave Google pública.
- [ ] Rotacionar chaves que não estejam corretamente restritas.
- [ ] Mover credenciais locais não relacionadas ao app para keychain.
- [x] Adicionar pip-audit/scanner Python e scanner npm.
- [x] Adicionar Semgrep/Bandit, secret scanning e scan do container.
- [ ] Definir SLA de atualização de vulnerabilidades.

### Gate G1 — Segurança

- [x] Nenhuma chamada paga anônima.
- [x] Nenhum bypass de entitlement pelo payload.
- [x] Upload malicioso é rejeitado de forma segura.
- [x] Nenhuma URL arbitrária chega ao WeasyPrint.
- [x] Owner e URLs assinadas protegem todos os artefatos.
- [ ] Privacidade, consentimento, retenção e exclusão estão implementados.
- [ ] Revisão de segurança aprovada.

---

# F2 — Fidelidade do produto e do PDF

## CORE-01 — Levar o roteiro completo da revisão ao PDF

**Prioridade:** P0
**Dependências:** API-01

### Implementação

- [x] Expandir GuideRequest com destinos ordenados, timing, dias e IDs estáveis.
- [x] Incluir ritmo, interesses, roteiro recomendado, dias e stops.
- [x] Serializar esses campos em Step5Review e minerva-api.
- [x] Validar o contrato no backend e persistir snapshot da revisão.
- [x] Renderizar o PDF pela ordem escolhida, não pela ordem do catálogo.
- [x] Definir seção para atrações sem dia.
- [x] Exibir na revisão apenas dados que o PDF suporta.
- [x] Registrar versão do template e do schema.

### Checkpoints

- [ ] CP1 — round-trip frontend → API → GuideContext preserva todos os campos.
- [x] CP2 — revisão e PDF possuem snapshot estruturado equivalente.
- [ ] CP3 — editar um dado e regenerar atualiza o PDF.

### Testes

- [ ] Roteiro conhecido, texto livre e rota sugerida.
- [x] Um e múltiplos destinos.
- [x] Ordem, timing e duração diferentes.
- [x] Atração com/sem itinerary_day.
- [x] Ritmos light, balanced e full.
- [ ] Payload máximo e compatibilidade com draft anterior.

## CORE-02 — Modelo familiar inclusivo e consistente

**Prioridade:** P0
**Dependências:** API-01, DEC-05

### Implementação

- [ ] Substituir string separada por vírgula por estruturas de responsáveis e crianças.
- [x] Definir o mesmo limite no frontend, API e PDF.
- [x] Permitir um, dois ou múltiplos responsáveis conforme decisão do produto.
- [x] Remover inferência automática mamãe/papai por posição.
- [ ] Permitir papel opcional: responsável, mãe, pai, avó, tutor etc.
- [x] Validar ano e idades antes da revisão.
- [x] Definir comportamento para famílias multietárias.

### Testes

- [ ] Um, dois, três e limite máximo de responsáveis.
- [ ] Família monoparental, homoafetiva, avós e tutores.
- [ ] Nomes longos, acentos e vírgulas.
- [x] Idade mínima, máxima e faixas mistas.
- [x] Frontend nunca aceita valor rejeitado por limite conhecido.

## COV-01 — Corrigir geração, validação e fallback da capa

**Prioridade:** P0
**Dependências:** DEC-06, DEC-12, PRIV-01

### Implementação

- [ ] Implementar validador real ou remover a expectativa de validação.
- [ ] Nunca executar geração paga se o resultado for inevitavelmente descartado.
- [ ] Criar estados generated, validated, retrying, fallback e failed.
- [ ] Se validação estiver indisponível, usar o fallback aprovado sem desperdiçar geração.
- [ ] Se o fallback for foto original, sanitizar, corrigir crop e preservar composição.
- [ ] Exibir status e mensagem equivalentes ao artefato entregue.
- [ ] Registrar modelo, prompt, seed, tentativas, custo e motivo do fallback sem PII.
- [ ] Permitir capa sem foto conforme decisão de produto.

### Checkpoints

- [ ] CP1 — caminho normal não termina sempre em silhueta.
- [ ] CP2 — absence de validador não consome Replicate inutilmente.
- [ ] CP3 — mensagem da UI corresponde à capa do PDF.

### Testes

- [ ] Gerador/validador aprovados, reprovados, inconclusivos e indisponíveis.
- [ ] Timeout, 429, 5xx e resposta inválida.
- [ ] Contagem esperada 1–10 e composições sintéticas.
- [ ] Portrait, landscape, rotação EXIF e crop.
- [ ] Regressão visual e aprovação humana com dados sintéticos.

## ASSET-01 — Assets reais, seguros e com proveniência

**Prioridade:** P0
**Dependências:** SEC-04

### Implementação

- [ ] Remover placeholders do caminho de produção pago.
- [ ] Criar política explícita de fallback aprovado por tipo de conteúdo.
- [ ] Persistir fonte, licença, autor, URL e attribution.
- [ ] Preservar attribution Google até o PDF.
- [ ] Manter filtros de licença Wikimedia.
- [ ] Validar se cada imagem/lineart representa o landmark correto.
- [ ] Sincronizar assets em object storage, não em paths locais frágeis.
- [ ] Impedir que asset sem direito de uso seja publicado.

### Testes

- [ ] Toda imagem não gerada possui proveniência.
- [ ] Créditos esperados aparecem no PDF.
- [ ] Asset ausente usa fallback aprovado, nunca figura geométrica genérica.
- [ ] Landmark incorreto é rejeitado.
- [ ] Manifest ausente não quebra silenciosamente a qualidade.

## CONTENT-01 — Qualidade editorial e adequação infantil

**Prioridade:** P1
**Dependências:** DEC-05

### Implementação

- [ ] Revisar acentuação, ortografia, capitalização e tom em templates, catálogo e prompts.
- [ ] Definir linguagem inclusiva de responsáveis.
- [ ] Definir atividade por faixa etária e objetivo pedagógico.
- [ ] Corrigir atividades chamadas caça-palavras que não exibem uma grade compatível.
- [ ] Definir limite mínimo de tamanho de fonte infantil.
- [ ] Revisar fatos, curiosidades, idiomas e pronúncia.
- [ ] Criar workflow editorial e versionamento do conteúdo.

### Testes e validações

- [ ] Spellcheck/dicionário customizado no CI.
- [ ] Amostra editorial por destino e idioma.
- [ ] Testes determinísticos das atividades por idade.
- [ ] Avaliação com educador/revisor e famílias do piloto.
- [ ] Nenhum texto interno de MVP/placeholder no PDF.

## PDF-01 — Renderer, formato, paginação e preview

**Prioridade:** P0
**Dependências:** BASE-02, CORE-01, ASSET-01

### Implementação

- [ ] Corrigir paths do preview publicado e servir assets por URL/rota válida.
- [ ] Definir A4/Letter conforme DEC-07.
- [ ] Remover cortes silenciosos causados por altura fixa e overflow hidden.
- [ ] Paginar resumo, destinos, créditos e conteúdo máximo.
- [ ] Definir corpo infantil mínimo de 12 pt e créditos mínimos de 9 pt.
- [ ] Embutir fontes e corrigir uso de Fraunces.
- [ ] Adicionar título, idioma, autoria e metadados.
- [ ] Avaliar PDF/UA; se o renderer não suportar, oferecer HTML acessível equivalente.
- [ ] Criar filename significativo e único.
- [ ] Diferenciar Abrir PDF de Baixar PDF.
- [ ] Informar páginas, tamanho e expiração do link.

### Checkpoints

- [ ] CP1 — preview publicado carrega 100% dos assets.
- [ ] CP2 — PDF máximo não corta texto, crédito ou atividade.
- [ ] CP3 — impressão no formato suportado não corta bordas.
- [ ] CP4 — extração de texto preserva ordem, idioma e acentos.

### Matriz visual de PDF

| Caso | Conteúdo |
|---|---|
| P1 | 1 destino e 1 landmark |
| P2 | 1 destino e 6 landmarks |
| P3 | 2–4 destinos e 13 landmarks |
| P4 | Limite máximo de destinos/landmarks |
| P5 | Nomes com 60+ caracteres |
| P6 | Muitos créditos e fontes |
| P7 | Crianças nas idades limítrofes |
| P8 | Diferentes composições familiares |
| P9 | Acentos e nomes internacionais |
| P10 | Fotos portrait, landscape e WEBP |
| P11 | Cada modalidade de fallback da capa |
| P12 | Restaurantes, se habilitados |
| P13 | A4 e Letter, se ambos suportados |
| P14 | Extração de texto e headings |
| P15 | Comparação automatizada revisão ↔ PDF |

### Testes automatizados

- [ ] qpdf --check, pdfinfo e pdffonts.
- [ ] Render de todas as páginas com pdftoppm.
- [ ] Visual regression com tolerância aprovada.
- [ ] Detecção de páginas vazias, imagens quebradas e texto fora da caixa.
- [ ] Snapshot dos créditos e metadados.
- [ ] Teste browser do preview remoto.

### Gate G2 — Fidelidade

- [ ] Tudo o que aparece na revisão chega ao PDF.
- [ ] Capa e fallback correspondem à promessa.
- [ ] Nenhum placeholder aparece em produção.
- [ ] Preview e PDF carregam todos os assets.
- [ ] Português, atividades e composição familiar estão revisados.
- [ ] PDF máximo imprime sem corte e atende o padrão definido.

---

# F3 — Persistência, jobs e operação

## DATA-01 — Unificar Supabase e remover dependência funcional de PocketBase

**Prioridade:** P1
**Dependências:** DEC-08, SEC-01

### Implementação

- [ ] Usar Supabase Auth como identidade canônica.
- [ ] Remover fallback funcional de dashboard/perfil para PocketBase.
- [ ] Criar migrations para guide_drafts, guide_jobs, guides, guide_assets, payments, entitlements, usage_events e audit_events.
- [ ] Incluir user_id, status, timestamps, versão do schema/template/modelo e erro seguro.
- [ ] Criar RLS por owner e papéis de suporte.
- [ ] Proteger parsing de registros legados.
- [ ] Migrar ou descartar dados PocketBase com plano explícito.

### Checkpoints

- [ ] CP1 — dashboard, perfil e geração usam a mesma identidade.
- [ ] CP2 — RLS nega acesso cruzado.
- [ ] CP3 — migrations e rollback passam em banco temporário.

## STO-01 — Object storage privado e retenção

**Prioridade:** P1
**Dependências:** DATA-01, PRIV-01

### Implementação

- [ ] Implementar buckets privados para family-uploads, generated-covers, generated-guides e landmark-assets.
- [ ] Definir paths por user_id/job_id e nomes não enumeráveis.
- [ ] Persistir PDF/capa antes de marcar job como concluído.
- [ ] Criar URL assinada curta e download autorizado.
- [ ] Implementar TTL de uploads e intermediários.
- [ ] Implementar exclusão transacional e reconciliação de órfãos.
- [ ] Definir backup e restore para pedidos pagos.

### Testes

- [ ] Restart/deploy não perde PDF ou status.
- [ ] Falha de storage não marca guia como pronto.
- [ ] Exclusão remove banco e todos os objetos.
- [ ] Job de cleanup em volume.
- [ ] Restore de backup.

## JOB-01 — Geração assíncrona, recuperável e idempotente

**Prioridade:** P1
**Dependências:** DATA-01, STO-01, SEC-02

### Implementação

- [ ] POST de geração valida e retorna 202 + job_id em até 2 segundos.
- [ ] Worker executa etapas isoladas.
- [ ] Estados: queued, running, succeeded, failed e cancelled.
- [ ] Etapas: validar, preparar assets, capa, conteúdo, PDF, persistir e finalizar.
- [ ] Retry com backoff/jitter apenas para erros transitórios.
- [ ] Timeout e orçamento por etapa/provedor.
- [ ] Idempotency key e consumo atômico de crédito.
- [ ] Progresso persistido e polling/SSE autenticado.
- [ ] Cancelamento cooperativo e cleanup.
- [ ] Recuperação após restart do worker.

### Checkpoints

- [ ] CP1 — refresh do browser recupera o mesmo job.
- [ ] CP2 — duplo clique não cria dois guias.
- [ ] CP3 — job nunca fica indefinidamente running.
- [ ] CP4 — retry não repete cobrança ou chamada já concluída.

### Testes

- [ ] Restart durante cada etapa.
- [ ] 429, timeout, 5xx e payload inválido por provedor.
- [ ] Idempotência e concorrência.
- [ ] Cancelamento antes/depois de chamada externa.
- [ ] Queue congestionada e dead-letter.
- [ ] Cleanup após falha.

## RES-01 — Clientes externos resilientes

**Prioridade:** P1
**Dependências:** JOB-01

### Implementação

- [ ] Criar camada compartilhada de clientes HTTP, preferencialmente assíncrona.
- [ ] Definir timeouts de conexão, leitura e total.
- [ ] Implementar retry apenas para erros transitórios.
- [ ] Adicionar circuit breaker e limite de concorrência.
- [ ] Cachear Wikimedia e resultados estáveis.
- [ ] Reutilizar resolução Google já confirmada.
- [ ] Limitar orçamento de chamadas por guia.
- [ ] Tornar falha de restaurante explícita; nunca cobrar por conteúdo vazio.

### Testes

- [ ] MockTransport para sucesso, timeout, 429, 5xx e schema inválido.
- [ ] Cache hit não chama provedor.
- [ ] Circuit breaker abre/fecha corretamente.
- [ ] Fallback conhecido mantém o job consistente.

## OBS-01 — Logs, traces, métricas, custos e alertas

**Prioridade:** P1
**Dependências:** JOB-01

### Implementação

- [ ] Propagar request_id, job_id e user_id pseudonimizado.
- [ ] Adicionar logs JSON por etapa, sem PII.
- [ ] Instrumentar traces da API ao worker e provedores.
- [ ] Medir fila, duração, sucesso, fallback, retry, tokens, chamadas e custo.
- [ ] Medir tamanho de upload/PDF e uso de storage.
- [ ] Integrar error tracking.
- [ ] Alertar fila parada, erro elevado, custo anormal, storage e SLO.
- [ ] Criar dashboards de engenharia e produto.

### SLOs iniciais a aprovar

- geração concluída com sucesso ≥ 95%;
- zero acesso cruzado;
- criação do job p95 ≤ 2 s;
- tempo p95 de geração definido após baseline;
- custo p95 por guia dentro da margem aprovada;
- downloads disponíveis conforme prazo comercial.

### Testes

- [ ] Rastrear um job ponta a ponta.
- [ ] Exercitar cada alerta em staging.
- [ ] Verificar ausência de PII/segredos.
- [ ] Simular fila, banco, storage e provedor indisponíveis.

## OPS-01 — Deploy, health, migrations e runbooks

**Prioridade:** P1
**Dependências:** BASE-02, DATA-01, JOB-01

### Implementação

- [ ] Versionar configuração de API e worker.
- [ ] Criar /health/live e /health/ready.
- [ ] Readiness verifica banco, queue e storage sem chamar API paga.
- [ ] Definir staging e produção com ambientes/segredos separados.
- [ ] Usar migrations antes do rollout com rollback definido.
- [ ] Implementar graceful shutdown do worker.
- [ ] Criar runbooks de OpenAI, Google, Replicate, Supabase, queue e storage.
- [ ] Documentar rotação de chaves, incidentes e restore.

### Gate G3 — Operação

- [ ] Guia sobrevive a restart/deploy.
- [ ] Dashboard mostra status e download corretos.
- [ ] Jobs são idempotentes, recuperáveis e observáveis.
- [ ] RLS e storage privado passam nos testes.
- [ ] Retenção, cleanup, backup e restore foram exercitados.

---

# F4 — UX, acessibilidade e performance

## UX-01 — Validação visível e sistema único de feedback

**Prioridade:** P0
**Dependências:** API-01

### Implementação

- [ ] Unificar Sonner/useToast em um único sistema.
- [ ] Adicionar erro inline próximo ao campo.
- [ ] Usar aria-invalid, aria-describedby e role=alert.
- [ ] Levar foco ao primeiro campo inválido.
- [ ] Preservar detalhe acionável do backend.
- [ ] Manter dados preenchidos após erro/retry.
- [ ] Diferenciar erro de validação, rede, autenticação, quota e provedor.

### Testes

- [ ] Submit vazio em cada etapa.
- [ ] Backend 400/401/403/413/422/429/500/timeout.
- [ ] Leitor de tela anuncia o erro uma vez.
- [ ] Retry mantém o estado.

## UX-02 — IDs estáveis e limites consistentes

**Prioridade:** P0
**Dependências:** API-01, CORE-02

### Implementação

- [ ] Gerar UUID/counter monotônico para destinos, crianças e responsáveis.
- [ ] Nunca derivar ID de array.length.
- [ ] Centralizar limites no schema compartilhado.
- [ ] Validar antes da revisão.
- [ ] Manter foco no item criado ou vizinho após remoção.

### Testes

- [ ] Adicionar três destinos, remover o segundo e adicionar outro.
- [ ] Reordenar, editar e remover itens.
- [ ] IDs permanecem únicos após reload do draft.
- [ ] Nenhuma key React duplicada.

## UX-03 — Draft, autosave e continuidade da jornada

**Prioridade:** P1
**Dependências:** DATA-01

### Implementação

- [ ] Persistir draft versionado após cada alteração relevante.
- [ ] Armazenar PII apenas no backend protegido; limitar storage local a estado não sensível.
- [ ] Restaurar passo e dados após refresh/nova sessão.
- [ ] Confirmar saída quando houver alterações não salvas.
- [ ] Tratar browser back/forward sem duplicar chamadas.
- [ ] Preservar /create → login → cadastro → login → wizard.
- [ ] Permitir descartar draft.
- [ ] Exibir nome das etapas e progresso compreensível.
- [ ] Coletar idades antes da recomendação ou recalcular depois.

### Testes

- [ ] Refresh em cada etapa.
- [ ] Fechar/reabrir, logout/login e expiração da sessão.
- [ ] Back/forward e clique no header.
- [ ] Migração de versão do draft.
- [ ] Falha de autosave e retry.

## UX-04 — Geração, progresso, retry e download

**Prioridade:** P1
**Dependências:** JOB-01

### Implementação

- [ ] Mostrar estágio real e estimativa honesta.
- [ ] Usar live region para progresso.
- [ ] Permitir sair e recuperar o job.
- [ ] Impedir submissão duplicada.
- [ ] Oferecer cancelamento quando seguro.
- [ ] Exibir erro específico e retry sem nova cobrança.
- [ ] Fazer Download baixar de fato ou renomear para Abrir PDF.
- [ ] Exibir validade, tamanho e quantidade de páginas.

### Testes

- [ ] Geração lenta, sucesso, falha e retry.
- [ ] Refresh/fechamento durante o job.
- [ ] Duplo clique e múltiplas abas.
- [ ] Link expirado e guia excluído.

## UX-05 — Mapas e atrações com falhas parciais

**Prioridade:** P1
**Dependências:** UX-01, RES-01

### Implementação

- [ ] Manter landmarks válidos no mapa quando parte deles não possuir coordenadas.
- [ ] Exibir lista textual equivalente com nome, status, endereço e ação.
- [ ] Diferenciar ponto confirmado, sugerido e sem localização.
- [ ] Permitir retry somente dos pontos ausentes.
- [ ] Evitar que ausência de chave/configuração apareça como instrução técnica ao usuário.
- [ ] Garantir operação por teclado, foco e leitor de tela.
- [ ] Definir fallback externo seguro quando o mapa embutido não estiver disponível.

### Testes

- [ ] Todos os pontos com coordenada.
- [ ] Parte dos pontos sem coordenada.
- [ ] Nenhum ponto com coordenada.
- [ ] Falha de Maps JavaScript, Geocoding e Places.
- [ ] Advanced Markers indisponível.
- [ ] Teclado, leitor de tela e viewports mobile.

## A11Y-01 — WCAG 2.2 AA

**Prioridade:** P1
**Dependências:** UX-01

### Implementação

- [x] Definir lang=pt-BR.
- [x] Adicionar skip link e hierarquia de headings.
- [ ] Associar label/for/id e autocomplete em todos os formulários.
- [x] Tornar medidor de senha textual e programático.
- [x] Implementar mostrar/ocultar senha.
- [x] Usar radio groups para modos/ritmo.
- [ ] Usar checkbox ou aria-pressed para interesses/atrações.
- [ ] Tornar cards e upload operáveis por Enter/Espaço.
- [x] Dar nome ao logo e menu mobile.
- [x] Adicionar aria-current, aria-expanded e aria-controls.
- [ ] Usar dialogs com nome, focus trap, Escape e restauração de foco.
- [ ] Oferecer alternativa textual completa ao mapa.
- [x] Adicionar status/live regions para loading, seleção e geração.
- [ ] Marcar SVG decorativo como aria-hidden.
- [ ] Garantir foco visível e alvo mínimo de 44×44 px.
- [x] Implementar prefers-reduced-motion.
- [x] Corrigir contraste para 4,5:1 em texto normal e 3:1 em texto grande/controles.

### Matriz de teclado

| Área | Validação |
|---|---|
| Header | Tab, Enter e Escape; foco retorna ao menu |
| Stepper | Ordem acompanha leitura |
| Modos | Setas/Espaço como radio group |
| Interesses | Espaço alterna e anuncia |
| Destinos | Criar/remover preserva foco |
| Atrações | Seleção e mapa sem mouse |
| Upload | Enter/Espaço abre seletor |
| Modais | Escape fecha e restaura foco |
| Review | Ordem, add-on e total compreensíveis |
| Erros | Submit leva ao primeiro erro |
| Sucesso | Download/painel acessíveis |

### Matriz de leitor de tela

- [ ] VoiceOver + Safari macOS.
- [ ] VoiceOver + Safari iOS.
- [ ] NVDA + Firefox/Chrome Windows.
- [ ] TalkBack + Chrome Android.

Para cada combinação:

- [ ] título, idioma, etapa e total anunciados;
- [ ] label, ajuda, obrigatoriedade e erro associados;
- [ ] seleção atual anunciada;
- [ ] dialog nomeado;
- [ ] loading/conclusão anunciados uma vez;
- [ ] conteúdo decorativo não polui a leitura.

### Testes

- [x] axe em CI nas rotas críticas.
- [ ] Jornada completa apenas por teclado.
- [ ] Leitor de tela nos fluxos críticos.
- [ ] Zoom 200% e fontes ampliadas.
- [ ] Contraste automático e revisão manual.

## UI-01 — Responsividade e consistência visual

**Prioridade:** P1
**Dependências:** A11Y-01

### Implementação

- [ ] Corrigir tokens primary, secondary, accent e destructive.
- [ ] Configurar Fraunces no Tailwind ou remover utilities conflitantes.
- [ ] Remover classes/tokens inexistentes.
- [ ] Empilhar campos familiares em telas estreitas.
- [ ] Ajustar área de upload mobile.
- [ ] Tratar safe-area em CTAs sticky.
- [ ] Suportar nomes e títulos longos.
- [ ] Evitar teclado virtual cobrindo campo, erro ou CTA.
- [ ] Validar claro/escuro em todos os estados.
- [ ] Garantir ausência de overflow horizontal desde 320 px.

### Matriz responsiva

| ID | Viewport/condição | Jornada |
|---|---|---|
| R1 | 320×568 | Cadastro, família, upload e review |
| R2 | 360×800 | Wizard completo |
| R3 | 375×667 | Menu e dialogs |
| R4 | 390×844 | Mapa e sticky CTA |
| R5 | 768×1024 | Wizard, mapa e review |
| R6 | 1024×768 | Mapa fullscreen e painel |
| R7 | 1280×800 | Jornada completa |
| R8 | 1440×900 | Home, preço e dashboard |
| R9 | Zoom 200% | Todas as rotas |
| R10 | Fonte ampliada | Auth e wizard |
| R11 | Teclado virtual | Formulários |
| R12 | Claro/escuro | Todos os estados |

Critérios:

- [ ] sem corte/overflow;
- [ ] foco e erros sempre visíveis;
- [ ] sem sobreposição de mapa, modal e CTA;
- [ ] contraste e imagens consistentes.

## FE-01 — Performance e manutenção do frontend

**Prioridade:** P2
**Dependências:** BASE-03

### Implementação

- [x] Dividir rotas e componentes pesados por dynamic import.
- [ ] Separar Step4Attractions e minerva-api em módulos menores.
- [x] Remover Integrated AI/PocketBase morto ou concluir sua função.
- [ ] Reativar no-unused-vars e regras React úteis.
- [ ] Adicionar typecheck por TypeScript ou JSDoc validado.
- [ ] Otimizar imagens, fontes e dependências.
- [ ] Definir orçamento de bundle e Web Vitals. (orçamento de bundle entregue; Web Vitals pendente)

### Testes

- [x] Build falha ao exceder orçamento aprovado.
- [ ] Lighthouse/Web Vitals em desktop e mobile.
- [ ] Navegação inicial não baixa código de mapas/wizard desnecessário.
- [ ] Regressão visual após code splitting.

### Gate G4 — Experiência

- [ ] Nenhum erro bloqueante é silencioso.
- [ ] Refresh e autenticação preservam o draft.
- [ ] Fluxo crítico funciona por teclado e leitor de tela.
- [ ] WCAG 2.2 AA nas rotas críticas.
- [ ] Sem overflow a partir de 320 px e com zoom 200%.
- [ ] Geração é recuperável e download é claro.

---

# F5 — Pagamento, entitlement e ciclo comercial

## PROD-01 — Verdade da proposta, marca e copy

**Prioridade:** P0 antes de cobrança
**Dependências:** DEC-01 a DEC-07

### Implementação

- [ ] Unificar marca, empresa, domínio, mercado, idioma e moeda.
- [ ] Alinhar landing/preço ao que o PDF realmente entrega.
- [ ] Remover ou marcar como beta roteiro avançado, múltiplas fotos/histórias e restaurantes.
- [ ] Exibir faixa etária, formato de impressão e pré-requisitos.
- [ ] Remover selos de pagamento até checkout homologado.
- [ ] Explicar preço-base, extras, total e reembolso antes da compra.

### Aceite

- Nenhuma promessa comercial depende de comportamento inexistente.

## PAY-01 — Checkout server-side e webhooks

**Prioridade:** P1
**Dependências:** DEC-11, DATA-01, SEC-01

### Implementação

- [ ] Centralizar produtos, preço e moeda no backend.
- [ ] Criar checkout no servidor.
- [ ] Validar assinatura de webhook.
- [ ] Processar webhook com idempotência e tolerância a eventos fora de ordem.
- [ ] Estados: pending, paid, failed, refunded e cancelled.
- [ ] Vincular pagamento, usuário, pedido e guia.
- [ ] Persistir recibo/referência do provedor.
- [ ] Implementar sandbox e produção separados.
- [ ] Definir falha pós-pagamento: retry, crédito ou reembolso.

### Testes

- [ ] Preço adulterado no frontend não altera cobrança.
- [ ] Webhook duplicado/atrasado/fora de ordem.
- [ ] Pagamento aprovado, recusado, cancelado e reembolsado.
- [ ] Pagamento aprovado + geração falha.
- [ ] Assinatura inválida.
- [ ] Timeout do browser após checkout.

## ENT-01 — Entitlement e créditos no backend

**Prioridade:** P0 antes de cobrança
**Dependências:** PAY-01, SEC-02

### Implementação

- [ ] Criar entitlement a partir de pagamento confirmado.
- [ ] Validar entitlement antes do job pago.
- [ ] Consumir crédito de forma atômica e idempotente.
- [ ] Nunca confiar em restaurant_recommendations_extra do cliente.
- [ ] Modelar add-ons no servidor.
- [ ] Definir efeito de reembolso e expiração.
- [ ] Manter restaurantes ocultos até conteúdo e SLA estarem aprovados.

### Testes

- [ ] Sem entitlement retorna 403 antes de chamar provedor.
- [ ] Alterar payload não libera extra.
- [ ] Pagamento gera exatamente um entitlement.
- [ ] Concorrência não consome crédito duas vezes.
- [ ] Reembolso segue a política definida.

## DASH-01 — Histórico, detalhes e re-download

**Prioridade:** P1
**Dependências:** DATA-01, STO-01, JOB-01

### Implementação

- [ ] Exibir draft, aguardando pagamento, fila, gerando, pronto, falhou e expirou.
- [ ] Implementar Ver detalhes, download, retry e exclusão.
- [ ] Diferenciar estado vazio, erro e indisponibilidade.
- [ ] Exibir prazo de retenção.
- [ ] Permitir suporte recuperar pedido pago sem acessar foto desnecessariamente.

### Testes

- [ ] Guia aparece após refresh e novo login.
- [ ] Detalhes abrem o guia correto.
- [ ] Erro não vira falso estado vazio.
- [ ] Download expira e pode ser renovado pelo owner.
- [ ] Exclusão respeita retenção legal/comercial.

### Gate G5 — Comercial

- [ ] Checkout e webhooks homologados.
- [ ] Entitlement é exclusivamente server-side.
- [ ] Nenhum pedido pago é perdido após falha.
- [ ] Dashboard e re-download funcionam.
- [ ] Termos, privacidade, preço e reembolso aparecem antes da compra.
- [ ] Fluxo de suporte/reembolso foi testado.

---

# F6 — IA, analytics, piloto e lançamento

## AI-01 — Avaliações versionadas de texto e roteiro

**Prioridade:** P2
**Dependências:** API-01, OBS-01

### Implementação

- [ ] Centralizar modelos, prompts e versões.
- [ ] Criar dataset versionado com português, inglês e espanhol.
- [ ] Incluir pedidos ambíguos, cidades homônimas, landmarks inexistentes e texto incompleto.
- [ ] Incluir prompt injection e conteúdo inadequado para crianças.
- [ ] Tratar refusal, resposta incompleta, timeout e schema inválido.
- [ ] Definir threshold de confiança e confirmação humana.
- [ ] Verificar locais/fatos por fonte antes de apresentá-los como verdade.
- [ ] Registrar tokens, latência, custo e fallback sem PII.
- [ ] Exigir suíte de eval antes de trocar modelo ou prompt.

### Métricas

- schema válido;
- precisão/recall de destinos e landmarks;
- taxa de confirmação/correção humana;
- alucinação/fato não verificado;
- segurança contra prompt injection;
- latência e custo;
- taxa de fallback.

### Testes

- [ ] Unitários herméticos com respostas gravadas/sintéticas.
- [ ] Eval offline em todo PR que altera prompt.
- [ ] Eval real periódica em sandbox com orçamento.
- [ ] Comparação de regressão por modelo/prompt.

## AI-02 — Avaliação de capa e conteúdo visual

**Prioridade:** P2
**Dependências:** COV-01

### Implementação

- [ ] Criar conjunto sintético/consentido de composições familiares.
- [ ] Medir preservação de quantidade, composição, segurança e qualidade.
- [ ] Avaliar lineart por reconhecibilidade e facilidade para colorir.
- [ ] Avaliar landmark correto e ausência de artefatos.
- [ ] Definir aprovação humana amostral.

### Critérios

- nenhum membro desaparece/adiciona no caminho aprovado;
- fallback é acionado corretamente;
- desenho representa o landmark;
- custo e tentativas ficam dentro do orçamento.

## AI-03 — Sugestão real de rota, após o MVP

**Prioridade:** P3
**Dependências:** CORE-01, AI-01

### Implementação

- [ ] Usar idades antes da recomendação.
- [ ] Gerar mais de uma opção explicável.
- [ ] Considerar duração, ritmo, deslocamento e interesses.
- [ ] Manter edição e confirmação humana.
- [ ] Marcar claramente sugestão versus dado confirmado.

### Testes

- [ ] Rotas coerentes para um/múltiplos destinos.
- [ ] Restrições contraditórias e dados insuficientes.
- [ ] Comparação de qualidade com baseline determinístico.

## CODE-01 — Refatoração incremental e qualidade de código

**Prioridade:** P2
**Dependências:** BASE-03, API-01

### Implementação

- [ ] Dividir app.py em routers de catálogo, itinerário, landmarks, jobs, downloads e health.
- [ ] Separar a orquestração de geração dos adapters de IA, mapas, imagens, storage e PDF.
- [ ] Dividir place_discovery.py e image_generation.py por responsabilidade.
- [ ] Injetar clientes externos e relógio/IDs para testes herméticos.
- [ ] Remover excepts silenciosos e criar taxonomia de erros.
- [x] Corrigir as 9 violações Ruff do baseline.
- [x] Adicionar format check, typecheck e cobertura ao CI.
- [ ] Definir meta crescente de cobertura para auth, segurança, jobs, pagamento e PDF.
  (baseline global atual: 81,74%; mínimo do CI: 75%)
- [ ] Realizar refatoração por seam, sem reescrita total ou alteração simultânea de comportamento.

### Checkpoints

- [ ] CP1 — cada extração mantém testes e contratos verdes.
- [ ] CP2 — routers não chamam SDKs externos diretamente.
- [ ] CP3 — serviços críticos podem ser testados sem rede, disco global ou chaves reais.

### Testes

- [ ] Characterization tests antes de mover comportamento legado.
- [ ] Contract tests após cada extração.
- [ ] Mutation/fault tests nos módulos de segurança e pagamento.
- [ ] Comparação de PDF e respostas antes/depois.

## DOC-01 — Documentação, rotas e governança OpenSpec

**Prioridade:** P2/P3
**Dependências:** decisões e arquitetura consolidadas

### Implementação

- [ ] Unificar README e HOSTINGER_DEPLOY.md em uma estratégia de deploy atual.
- [x] Documentar requisitos nativos do WeasyPrint e comandos de diagnóstico.
- [x] Criar matriz de variáveis por frontend, API, worker, staging e produção.
- [x] Manter .env.example apenas com variáveis realmente implementadas.
- [x] Corrigir llms.txt para as rotas reais / e /create.
- [x] Remover ou redirecionar a segunda UI legada publicada na raiz do FastAPI.
- [x] Remover Integrated AI/PocketBase morto ou documentar sua função futura.
- [ ] Documentar arquitetura, contratos, runbooks, rollback e resposta a incidentes.
- [ ] Sincronizar specs principais e arquivar mudanças OpenSpec somente após validação.
- [x] Criar guia de contribuição e checklist de PR baseado neste plano.

### Testes e validações

- [ ] Links, rotas e comandos da documentação executam em ambiente limpo.
- [x] Validador confirma que .env.example cobre todas as variáveis lidas pelo código.
- [ ] Nenhum segredo/valor real aparece na documentação.
- [ ] OpenSpec validate passa antes de sync/archive.
- [x] Smoke test confirma que rotas documentadas existem.

## ANL-01 — Analytics de produto sem PII

**Prioridade:** P1 antes do piloto
**Dependências:** PRIV-01, OBS-01

### North Star

Guias válidos baixados e avaliados positivamente por famílias por semana.

### Eventos mínimos

- [ ] landing_view;
- [ ] create_cta_clicked;
- [ ] signup_started/completed;
- [ ] guide_started;
- [ ] destinations_completed;
- [ ] attractions_loaded/confirmed;
- [ ] family_completed;
- [ ] cover_uploaded;
- [ ] review_reached;
- [ ] checkout_started/completed;
- [ ] generation_started/completed/failed;
- [ ] pdf_downloaded;
- [ ] quality_rating_submitted.

### Métricas

- conversão por etapa;
- abandono e motivo;
- p50/p95 de descoberta e geração;
- fallback de capa;
- atrações sem imagem/mapa;
- custo e margem por guia;
- reembolso/correção;
- nota do PDF e intenção de imprimir;
- re-download e suporte.

### Testes

- [ ] Eventos disparam uma vez e na ordem correta.
- [ ] Nenhum evento contém nome, foto ou texto livre.
- [ ] Consentimento/opt-out respeitado.
- [ ] Dashboard reconcilia evento, job e pagamento.

## PILOT-01 — Piloto controlado

**Prioridade:** P2
**Dependências:** Gates G1–G5

### Implementação

- [ ] Recrutar 10–20 famílias diversas.
- [ ] Incluir idades, composições e roteiros variados.
- [ ] Incluir um e múltiplos destinos.
- [ ] Definir roteiro de observação e suporte.
- [ ] Medir tempo, dúvidas, desistência, custo e qualidade.
- [ ] Revisar cada PDF por precisão, idade, legibilidade, impressão e preservação familiar.
- [ ] Coletar avaliação após criação e, quando possível, após a viagem.
- [ ] Registrar disposição a pagar.
- [ ] Definir critérios prévios de continuar, corrigir ou interromper.

### Metas iniciais propostas

- [ ] ≥ 95% das gerações iniciadas concluídas.
- [ ] ≥ 90% dos participantes baixam sem suporte.
- [ ] satisfação média ≥ 4/5.
- [ ] < 5% de correção/reembolso por qualidade.
- [ ] zero acesso cruzado.
- [ ] margem positiva no cenário p95.
- [ ] p95 de geração aprovado e comunicado.

### Gate G6 — Lançamento

- [ ] Metas do piloto atingidas.
- [ ] Nenhum P0/P1 crítico aberto.
- [ ] Monitoramento e alertas ativos.
- [ ] Runbooks e suporte aprovados.
- [ ] Custo, margem, retenção e reembolso conhecidos.
- [ ] Go/no-go aprovado por Produto, Engenharia, Segurança e responsável legal/comercial.

---

# 6. Matriz consolidada de testes

## Testes unitários

- [ ] JWT, owner e entitlement.
- [ ] Rate limit, quota e idempotency key.
- [ ] Upload: limite, MIME, pixels, EXIF e nomes.
- [ ] Validador de URL/IP/redirect.
- [ ] url_fetcher do WeasyPrint.
- [ ] Máquina de estados da capa.
- [ ] Estados/retries de job.
- [ ] Contrato completo do roteiro.
- [ ] IDs estáveis e limites.
- [ ] Attribution e licenças.
- [ ] Redação de PII.
- [ ] Retenção e cleanup.
- [ ] Atividades por idade e word search.

## Testes de integração

- [ ] Supabase Auth/JWKS.
- [ ] RLS com dois usuários.
- [ ] Storage privado e URL assinada.
- [ ] Banco + queue + worker.
- [ ] Checkout + webhook + entitlement.
- [ ] Geração real no container.
- [ ] WeasyPrint sem rede.
- [ ] Provedores simulados em sucesso/falha.
- [ ] Dashboard lendo guia gerado.
- [ ] Migration e rollback.
- [ ] Review ↔ GuideContext ↔ PDF.

## Testes de segurança

- [ ] Endpoint caro sem token.
- [ ] Token inválido/de outro projeto.
- [ ] Acesso cruzado.
- [ ] Bypass de add-on/entitlement.
- [ ] Upload grande/falso/decompression bomb.
- [ ] SSRF IPv4, IPv6, redirect, file:// e DNS simulado.
- [ ] Enumeração de IDs/URLs.
- [ ] CORS não permitido.
- [ ] Secret, dependency, SAST e container scans sem crítico.
- [ ] Logs/analytics sem PII.

## Testes E2E

- [ ] Cadastro, confirmação, login, recuperação e logout.
- [ ] Entrada por /create com retorno ao wizard.
- [ ] Roteiro conhecido.
- [ ] Texto livre com complementação.
- [ ] Rota sugerida e editada.
- [ ] Um/múltiplos destinos com remoção intermediária.
- [ ] Idades e composições familiares diversas.
- [ ] Seleção, mapas e pontos sem coordenada.
- [ ] Upload válido/inválido/substituído.
- [ ] Checkout ou cupom do piloto.
- [ ] Job assíncrono, progresso, refresh e retry.
- [ ] Cada fallback da capa.
- [ ] Extra com/sem entitlement.
- [ ] Download autenticado.
- [ ] Guia no dashboard após novo login.
- [ ] Exclusão do guia e artefatos.
- [ ] Desktop, mobile, teclado e axe.
- [ ] PDF sem páginas vazias, assets quebrados ou créditos ausentes.

## Testes operacionais

- [ ] Smoke pós-deploy.
- [ ] Restart do worker durante job.
- [ ] Indisponibilidade de cada provedor.
- [ ] Queue congestionada.
- [ ] Banco/storage indisponíveis.
- [ ] Load test por usuário e global.
- [ ] Memória com uploads simultâneos.
- [ ] Cleanup/retention em volume.
- [ ] Rotação de chaves.
- [ ] Backup/restore.
- [ ] Disparo e recebimento de alertas.
- [ ] Fluxo de suporte e reembolso.

# 7. Matriz de erros esperados

| Cenário | Resultado esperado |
|---|---|
| Sem rede no login | Erro inline, retry e draft preservado |
| Email não confirmado | Orientação ao usuário, sem instrução administrativa |
| Falha de sugestões | Retry e entrada manual |
| Nenhuma atração | Editar busca ou inserir manualmente |
| Places indisponível | Fallback de produto, não mensagem de configuração |
| Ponto sem coordenada | Outros pontos continuam visíveis |
| Foto inválida/grande | Rejeição local e backend consistente |
| API 400/422 | Campos causadores identificados |
| API 401/403 | Reautenticar ou explicar entitlement |
| API 429 | Retry-After e nenhuma duplicação |
| Geração 500/timeout | Job recuperável e retry |
| Dashboard indisponível | Estado de erro, não vazio |
| PDF expirado | Renovar link, regenerar ou suporte |
| Falha parcial de asset | Fallback aprovado, nunca placeholder |
| Pagamento aprovado + falha | Pedido recuperável, sem nova cobrança |

# 8. Evidências obrigatórias por PR

- [ ] link da issue/ID deste plano;
- [ ] decisão/ADR quando aplicável;
- [ ] testes adicionados e comandos executados;
- [ ] screenshots desktop/mobile;
- [ ] PDF sintético e contact sheet quando alterar renderização;
- [ ] resultado de axe quando alterar UI;
- [ ] resultado de segurança quando alterar entrada/URL/upload/auth;
- [ ] migration, rollback e compatibilidade;
- [ ] métricas/logs novos;
- [ ] feature flag e plano de rollout;
- [ ] confirmação de que nenhum dado real foi anexado ao PR.

# 9. Checklist final de aceite do MVP

- [ ] Usuário novo conclui cadastro ou fluxo convidado, pagamento, wizard, geração e download sem intervenção.
- [ ] Todos os dados da revisão aparecem corretamente no PDF.
- [ ] Ordem, dias, timing, ritmo e atrações são preservados.
- [ ] Atividades correspondem à faixa etária.
- [ ] Diferentes composições familiares não quebram nem geram copy incorreta.
- [ ] Falhas externas não duplicam cobrança ou pedido.
- [ ] Geração é recuperável após refresh/restart.
- [ ] Guia permanece disponível durante o prazo prometido.
- [ ] Outro usuário não acessa draft, job, guia ou arquivo.
- [ ] Exclusão e retenção funcionam.
- [ ] Termos, privacidade, preço e reembolso são visíveis antes da compra.
- [ ] Nenhum recurso pago é liberado por parâmetro do cliente.
- [ ] Nenhum placeholder, asset quebrado ou texto sem revisão chega ao PDF.
- [ ] Preview e PDF passam na matriz visual máxima.
- [ ] Fluxo crítico atende WCAG 2.2 AA.
- [ ] Analytics, custos, SLOs e alertas estão ativos.
- [ ] Backup, restore, incidente e suporte foram exercitados.

# 10. Próxima sequência recomendada

1. Concluir decisões DEC-01 a DEC-13.
2. Entregar BASE-02, BASE-03 e API-01.
3. Implementar SEC-01 a SEC-05 e PRIV-01.
4. Corrigir CORE-01, CORE-02, COV-01, ASSET-01 e PDF-01.
5. Implementar DATA-01, STO-01, JOB-01 e OBS-01.
6. Corrigir UX-01/02, depois draft, acessibilidade e responsividade.
7. Implementar checkout, entitlement e dashboard.
8. Instrumentar analytics/evals.
9. Executar piloto controlado.
10. Realizar go/no-go somente após Gate G6.
