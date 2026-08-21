# P2 — Continuidade e segurança na criação do guia

## Objetivo

Transformar o fluxo de criação em uma jornada previsível, retomável e segura. O P2 melhora a
orientação entre etapas, torna o autosave compreensível, oferece uma saída explícita para continuar
depois e protege o rascunho contra descarte acidental.

O P2 parte do P0 e P1 já validados. Não altera o contrato do guia, o checkout, a geração de imagens,
o preço nem o conteúdo do PDF.

## Problemas observados

- Os marcadores atuais mostram números, mas não comunicam todas as etapas nem a próxima ação.
- O progresso não possui semântica de `progressbar` para tecnologias assistivas.
- O estado do rascunho ocupa espaço mesmo quando não há mensagem e não diferencia claramente
  “salvando”, “salvo”, recuperação local e erro.
- Não existe uma ação explícita “continuar depois” próxima ao progresso.
- “Descartar” executa uma ação irreversível sem confirmação.
- Em celular, voltar, progresso e descarte competem dentro de três colunas estreitas.

## Escopo

### 1. Mapa semântico da jornada

- Criar um componente compartilhado para representar as etapas visíveis do modo de roteiro atual.
- Exibir etapa atual, quantidade concluída e nome da próxima etapa.
- Mostrar todos os nomes em desktop e um resumo compacto em celular.
- Expor o avanço com `role="progressbar"`, valor atual, mínimo e máximo.

Critérios de aceite:

- O usuário entende onde está e o que vem depois sem depender apenas dos números.
- O modo “Já sei o roteiro” continua omitindo corretamente a etapa de preferências.
- A etapa atual usa `aria-current="step"` e estados não dependem apenas de cor.
- A barra não causa overflow em 390 px.

### 2. Estado do rascunho compreensível

- Apresentar um indicador compacto apenas quando houver informação útil.
- Diferenciar salvamento em andamento, progresso salvo, recuperação local e erro.
- Preservar `aria-live` sem anunciar mensagens vazias.
- Manter a mensagem detalhada de erro retornada pelo contexto.

Critérios de aceite:

- “Salvando” e “salvo” são distinguíveis por texto e ícone.
- Erro usa `role="alert"` e continua visível até uma nova tentativa de salvamento.
- Nenhuma atualização cria uma chamada de rede adicional ou outro temporizador de autosave.

### 3. Continuar depois com segurança

- Adicionar uma ação explícita para salvar o estado mais recente e voltar à biblioteca.
- Reutilizar a função de persistência atual, sem duplicar o contrato de rascunho.
- Bloquear cliques repetidos enquanto a saída está sendo preparada.
- Permanecer na criação e informar o problema se o salvamento confirmado falhar.

Critérios de aceite:

- A ação aparece quando existe um rascunho persistido.
- Em sucesso, a navegação termina em `/dashboard`.
- Em falha, o usuário não perde o contexto atual.
- A ação funciona por teclado e possui nome completo no celular.

### 4. Descarte protegido

- Substituir a exclusão imediata por um `AlertDialog` acessível.
- Explicar que escolhas e progresso da criação serão removidos.
- Separar visualmente cancelar e descartar definitivamente.
- Manter o tratamento de erro já existente no contexto.

Critérios de aceite:

- O primeiro clique nunca apaga o rascunho.
- Escape, cancelar e clique fora não confirmam a ação destrutiva.
- A confirmação chama a API uma única vez e reinicia o fluxo apenas após sucesso.

### 5. Qualidade React, responsividade e acessibilidade

- Manter componentes novos fora do corpo de outros componentes.
- Derivar posição, rótulos e próxima etapa durante renderização, sem estado redundante.
- Respeitar redução de movimento e alvos de toque já definidos.
- Não adicionar dependências.

Critérios de aceite:

- ESLint e revisão React não encontram novos problemas.
- Axe WCAG A/AA passa no fluxo restaurado.
- Desktop, Pixel 7 e 768×1024 não apresentam overflow.
- O orçamento atual do bundle permanece aprovado.

## Design de implementação

### `GuideCreationProgress`

Recebe `visibleSteps`, `currentStep` e o catálogo de nomes. Calcula posição e próxima etapa sem
estado próprio. Renderiza resumo textual, barra semântica e uma lista ordenada de etapas. A lista
completa fica visível a partir do desktop; no celular o resumo preserva a mesma informação.

### `DraftStatusNotice`

Recebe `status`, `error`, `restoredProgress` e `builderSessionId`. Retorna `null` quando não existe
mensagem útil. Ícone, texto e papel semântico são determinados por uma configuração estática.

### Ações de continuidade

`persistLatestDraft` será exposto pelo contexto como `saveDraftNow`, preservando uma única fonte de
verdade. A página aguarda essa Promise antes de navegar. O descarte continua centralizado em
`discardDraft`, mas passa a ser chamado somente pela confirmação do diálogo.

## Fora do escopo

- Navegação livre para etapas futuras ou já concluídas.
- Histórico ou múltiplos rascunhos por conta.
- Edição de um guia já finalizado.
- Alterações no backend de retenção ou sincronização.
- Mudanças em Mercado Pago, preço ou entrega.
- Notificações push ou colaboração entre pessoas.

## Plano de implementação

- [x] Criar o mapa semântico e responsivo das etapas.
- [x] Criar o indicador acessível do estado do rascunho.
- [x] Expor o salvamento imediato pelo contexto existente.
- [x] Implementar “Continuar depois” com espera, erro e navegação segura.
- [x] Proteger o descarte com confirmação acessível.
- [x] Adicionar contratos estáticos e E2E nos três viewports.
- [x] Executar lint, testes, build, bundle, E2E e QA no navegador.

## Matriz de verificação

- Fluxo novo sem rascunho e fluxo restaurado.
- Modo com roteiro conhecido e modo com preferências.
- Salvar e continuar depois em sucesso e falha.
- Cancelar e confirmar descarte.
- Progresso por teclado e leitura por Axe.
- 390×844, Pixel 7, 768×1024 e desktop.
- Console, overlay de erro e overflow horizontal.

## Resultado da validação

- ESLint: aprovado sem erros.
- Testes Node: 170 aprovados.
- Build Vite: aprovado, com 2.142 módulos transformados.
- Orçamento de bundle: 16 chunks JavaScript dentro do limite de 320 KiB.
- Playwright: 63 cenários aprovados em desktop, Pixel 7 e tablet, incluindo a fronteira
  explícita de 390×844.
- Axe: nenhuma violação automática WCAG A/AA nos fluxos cobertos.
- Inspeção visual: hierarquia, ações, progresso e conteúdo aprovados em desktop e mobile.
