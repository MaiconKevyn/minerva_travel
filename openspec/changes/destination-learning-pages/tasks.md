## 1. Contracts And Context

- [x] 1.1 Definir o contexto privado de destino e os campos públicos de revisão.
- [x] 1.2 Resolver aprendizados e curiosidades com prioridade editorial e fallback seguro.
- [x] 1.3 Associar cada ponto ao seu destino canônico e atualizar o limite máximo de páginas.

## 2. Progressive Page Plan

- [x] 2.1 Inserir uma `destination_intro` antes da primeira ocorrência de cada destino.
- [x] 2.2 Preservar pontos, atividades e `Minha melhor memória` na ordem correta.
- [x] 2.3 Incluir toda cópia pedagógica em `required_copy` e metadados públicos.

## 3. OpenAI Generation

- [x] 3.1 Adicionar geração/regeneração people-free de abertura de destino ao protocolo.
- [x] 3.2 Implementar prompt com texto exato, ilustração reconhecível e cartão de curiosidade.
- [x] 3.3 Reforçar o prompt dos pontos com descrição e curiosidade/missão rotuladas.
- [x] 3.4 Despachar o novo tipo sem resolver nem encaminhar foto/capa da família.

## 4. Frontend And Contract

- [x] 4.1 Rotular e contextualizar páginas de destino na montagem progressiva.
- [x] 4.2 Atualizar o contrato OpenAPI consumido pelo frontend.
- [x] 4.3 Confirmar que `Incluir família` continua exclusivo das páginas de ponto.

## 5. Verification

- [x] 5.1 Cobrir contexto, ordem multi-destino, deduplicação e fallback com testes backend.
- [x] 5.2 Cobrir prompt, endpoint, geração e regeneração sem referências familiares.
- [x] 5.3 Executar testes Python/frontend, lint, formato e validações de contrato afetadas.
- [x] 5.4 Validar que o PDF continua usando a sequência aprovada sem alteração no compositor.

## 6. Landmark Visit Checkbox

- [x] 6.1 Incluir `Já visitei` no contrato obrigatório de toda página `landmark`.
- [x] 6.2 Reservar o rodapé no prompt e compor deterministicamente o quadrado vazio e o rótulo.
- [x] 6.3 Cobrir primeira geração, regeneração, modo com/sem família, UI e PDF com testes.
- [x] 6.4 Executar validação completa antes de publicar `main` e `hostinger-frontend`.
