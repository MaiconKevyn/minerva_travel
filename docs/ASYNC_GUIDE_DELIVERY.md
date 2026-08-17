# Decisão: capa aprovada e guia assíncrono

Data: 2026-08-17
Estado: implementado

## Decisão

O usuário revisa e aprova somente a capa. Depois disso, `POST
/api/guide-builder/{session_id}/generation-jobs` grava um job durável e responde
`202` imediatamente. O worker gera e aprova as outras páginas na ordem
canônica, monta um PDF com uma imagem por página e envia por e-mail um link
autenticado para download.

A geração é retomável: cada página usa uma chave idempotente derivada do job e
as páginas já aprovadas são ignoradas nas novas tentativas. Falhas temporárias
recebem backoff exponencial e limite de tentativas. O PDF só marca o job como
concluído depois da confirmação do envio do e-mail.

## Operação no Render

O estado atual usa SQLite, sessões e imagens no mesmo `MINERVA_RUNTIME_DIR`.
Como o disco persistente do Render pertence a um único serviço, produção usa
`IN_PROCESS_GUIDE_WORKER_ENABLED=true`: uma thread daemon supervisionada pela
API consome a mesma fila sem bloquear o event loop. `GUIDE_WORKER_POLL_SECONDS`
controla o intervalo ocioso.

SMTP é obrigatório para cumprir a entrega final: `SMTP_HOST`, `SMTP_PORT`,
`SMTP_FROM` e, quando o provedor exigir, `SMTP_USERNAME`/`SMTP_PASSWORD`. O PDF
não é anexado porque guias ilustrados ultrapassam limites comuns de mensagem;
o e-mail contém o link privado da conta.

## Rollout

1. Publicar backend e frontend compatíveis.
2. Confirmar disco montado em `MINERVA_RUNTIME_DIR`.
3. Confirmar worker embutido e SMTP no serviço de produção.
4. Enfileirar um guia sintético, fechar a aba e verificar job, PDF e e-mail.

## Rollback e compatibilidade

- Desativar apenas o consumidor embutido com
  `IN_PROCESS_GUIDE_WORKER_ENABLED=false`; jobs já gravados permanecem na fila.
- Os endpoints antigos de geração/aprovação por página e PDF continuam
  disponíveis durante a transição, portanto sessões anteriores não são
  invalidadas.
- Os novos campos de sessão são opcionais na leitura de JSON antigo.
- Para voltar à interface anterior basta reverter o frontend; não há migration
  destrutiva nem alteração incompatível no banco.
