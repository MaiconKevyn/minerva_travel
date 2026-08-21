# P0 — Experiência superior no frontend

## Objetivo

Reduzir a distância entre encantamento, compreensão e ação nos dois fluxos mais importantes do produto: conhecer o Guia de Memórias e criar o primeiro guia. O P0 preserva a identidade editorial já implementada e prioriza clareza no celular, prova concreta do produto, confiança contextual e acessibilidade.

## Escopo

### 1. Hero mobile orientado ao produto

- Mostrar a composição de páginas antes do texto secundário no celular.
- Manter título, produto, preço e CTA principal dentro da primeira experiência de rolagem.
- Consolidar formato, faixa etária/personalização e compra única em uma faixa de fatos rápidos.
- Preservar a composição lado a lado no desktop.

Critérios de aceite:

- A capa e pelo menos duas páginas são visíveis sem o usuário percorrer todo o hero no celular.
- O preço aparece antes ou imediatamente junto ao CTA principal.
- Imagens do hero têm dimensões, `sizes` e prioridade de carregamento apropriadas.

### 2. Home mais curta sem perda de prova

- Transformar o leitor de 19 páginas em uma vitrine compacta inicialmente.
- Exibir miniaturas visuais nomeadas para páginas representativas.
- Manter acesso explícito ao guia completo por expansão.
- Exibir uma amostra de atividades por categoria e oferecer expansão para a lista completa.

Critérios de aceite:

- O estado compacto comunica capa, roteiro, lugar, atividade e memória.
- A expansão é acessível por teclado e informa seu estado com `aria-expanded`.
- Nenhum conteúdo deixa de estar acessível.
- A altura inicial das seções de guia e atividades é materialmente menor em mobile e tablet.

### 3. Ação segura no passo de atrações

- Evitar que o CTA fixo permita confirmar locais antes de o usuário revisar a seleção.
- Incluir no CTA um resumo do que será confirmado.
- Reduzir a altura do cabeçalho da etapa em telas pequenas.
- Garantir que conteúdo focado não fique oculto pelo CTA persistente.

Critérios de aceite:

- O botão persistente só aparece após a área de seleção ter sido alcançada ou traz contexto suficiente sobre a seleção.
- O CTA informa quantidade e, para seleção unitária, o nome do local.
- Existe espaçamento inferior suficiente para o último controle não ficar coberto.

### 4. Confiança contextual

- Foto: explicar finalidade, persistência e possibilidade de revisão junto do upload.
- Atrações: explicar que a seleção pode ser alterada antes da geração.
- Revisão/pagamento: mostrar valor, formato entregue, fluxo de aprovação e checkout seguro no contexto da ação.
- Geração: explicar que o processamento continua e que o resultado será enviado por e-mail, quando aplicável.

Critérios de aceite:

- Informações críticas não dependem apenas do FAQ ou da página de preço.
- Mensagens são curtas, escaneáveis e associadas ao controle correspondente.
- Claims de privacidade refletem o comportamento já implementado pelo produto.

### 5. Acessibilidade, movimento e performance perceptiva

- Usar 44 px como alvo padrão para controles móveis importantes.
- Garantir foco visível e não oculto por elementos fixos.
- Respeitar `prefers-reduced-motion` no CSS e nas animações principais.
- Substituir o `@import` bloqueante de fontes por carregamento no documento com `preconnect`.
- Adicionar imagens responsivas e lazy-loading onde o conteúdo não é crítico.

Critérios de aceite:

- Controles principais do header, leitor e builder têm área confortável de toque.
- A interface continua utilizável com movimento reduzido.
- O build não introduz regressão no orçamento de bundle.

## Fora do escopo

- Mudanças no backend, preço ou contrato do Mercado Pago.
- Nova geração de ilustrações.
- Redesign completo do dashboard.
- Temas visuais dinâmicos por destino.
- Alterações no conteúdo gerado do PDF.

## Verificação

- Testes unitários do frontend.
- ESLint sem erros.
- Build de produção e verificação do orçamento de bundle.
- Testes E2E existentes, quando o ambiente permitir.
- QA visual em 390×844, 768×1024 e desktop.
- Navegação por teclado nos controles alterados.
- Validação da preferência `prefers-reduced-motion`.
