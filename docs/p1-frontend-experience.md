# P1 — Biblioteca, consistência e continuidade da experiência

## Objetivo

Levar a identidade editorial do Guia de Memórias para além da primeira compra. O P1 transforma o painel autenticado em uma biblioteca de viagens orientada a próximos passos, elimina mensagens divergentes do fluxo real e consolida padrões compartilhados de navegação, rodapé, estados e feedback.

O P1 parte do P0 já validado: não altera preço, checkout, APIs ou geração do PDF e não reduz a prova visual da home.

## Escopo

### 1. Painel como biblioteca de viagens

- Trocar a hierarquia centrada em “dados da conta” por uma abertura centrada na jornada da família.
- Mostrar um resumo escaneável de guias prontos, guias em criação e próxima ação.
- Priorizar trabalhos em andamento antes da estante de guias concluídos.
- Manter os dados da conta disponíveis em um bloco compacto e secundário.

Critérios de aceite:

- Em desktop e celular, a primeira área do painel responde: “o que está pronto?”, “o que está sendo criado?” e “o que posso fazer agora?”.
- O CTA para um novo guia permanece visível sem competir com as ações de download e detalhes.
- Dados pessoais não ocupam um terço permanente da página.
- A hierarquia funciona igualmente nos estados vazio, carregando, erro e preenchido.

### 2. Cards de guia e acompanhamento da geração

- Tratar a capa como elemento principal do card, mantendo título, destinos e status próximos.
- Transformar o progresso da geração em um `progressbar` semanticamente completo.
- Dar prioridade visual a “Baixar PDF”; detalhes e exclusão permanecem secundários.
- Explicar de forma curta que a geração continua fora da página e que a entrega ocorre por e-mail.

Critérios de aceite:

- Status não depende apenas de cor.
- Progresso expõe valor atual, mínimo e máximo para tecnologias assistivas.
- Cards não causam overflow horizontal em 390 px.
- Confirmação de exclusão continua explícita e reversível antes da ação destrutiva.

### 3. Estados vazios e orientação da próxima ação

- Substituir o vazio passivo por uma chamada clara para criar o primeiro guia.
- Diferenciar biblioteca vazia de guia ainda em processamento.
- Usar skeletons com dimensões próximas do conteúdo final para reduzir salto visual.

Critérios de aceite:

- O estado vazio oferece CTA e explica o primeiro passo.
- Durante carregamento, a estrutura da página permanece estável.
- Erros continuam com mensagem, `role="alert"` e tentativa novamente.

### 4. Consistência entre páginas públicas

- Extrair o rodapé editorial compartilhado e reutilizá-lo na home, preço e páginas legais.
- Preservar links para privacidade e termos em todas as páginas públicas de decisão.
- Evitar duplicação que faça marca, data ou texto de piloto divergirem entre rotas.

Critérios de aceite:

- Existe uma única implementação do rodapé público.
- Home, preço, privacidade e termos usam a mesma marca e navegação legal.
- O rodapé adapta sua disposição sem apertar os links no celular.

### 5. Verdade do produto e microcopy

- Corrigir a home para afirmar que a foto familiar é opcional.
- Explicar que a família revisa a capa; as demais páginas são criadas em segundo plano.
- Manter entrega, formato, privacidade e pagamento coerentes com o fluxo implementado.

Critérios de aceite:

- Nenhuma página pública promete revisão página a página.
- Nenhuma página pública diz que a foto é obrigatória.
- A linguagem continua lúdica, mas ações, limites e consequências permanecem diretos.

### 6. Qualidade React, acessibilidade e performance perceptiva

- Remover avisos de propriedades DOM incompatíveis no console.
- Manter dados derivados como expressões de renderização, sem estado ou efeitos redundantes.
- Não adicionar dependências ou animações obrigatórias.
- Respeitar foco, redução de movimento e alvo mínimo de toque já definidos no P0.

Critérios de aceite:

- Navegação pública não gera avisos React causados pelo código alterado.
- O redesign não cria chamadas de rede adicionais nem polling duplicado.
- O orçamento atual de bundle continua aprovado.
- Dashboard e páginas públicas passam por Axe WCAG A/AA.

## Fora do escopo

- Edição do perfil da família.
- Busca, filtro ou ordenação de uma biblioteca grande.
- Compartilhamento público de guias.
- Alteração de retenção, download ou exclusão no backend.
- Tema visual dinâmico por destino.
- Mudança em preço, Mercado Pago ou contrato da geração.

## Plano de implementação

- [x] Criar o rodapé editorial compartilhado e substituir duplicações.
- [x] Corrigir microcopy pública para o fluxo vigente.
- [x] Redesenhar a abertura e os indicadores do dashboard.
- [x] Refinar cards, progresso, carregamento, vazio e erro do dashboard.
- [x] Corrigir avisos React e revisar renderização dos componentes alterados.
- [x] Adicionar cobertura E2E do dashboard preenchido e dos estados responsivos.
- [x] Executar lint, testes unitários, build, bundle e matriz E2E.

## Resultado implementado

- O painel agora abre como uma biblioteca da família, com guias prontos, criações ativas e a próxima ação em primeiro plano.
- Dados da conta permanecem acessíveis em um bloco recolhível, sem dominar a página.
- Geração, carregamento, erro, vazio, download, detalhes e exclusão têm hierarquia e feedback próprios.
- O progresso usa semântica de `progressbar` e o estado vazio conduz diretamente à criação.
- Home, preço, privacidade e termos compartilham o mesmo rodapé editorial.
- A home comunica corretamente foto opcional e aprovação da capa antes da geração em segundo plano.
- A implementação foi validada por lint, 166 testes de contrato, build, orçamento de bundle e 54 cenários E2E em três resoluções.

## Verificação

- ESLint sem erros.
- Testes unitários e de contrato estático do frontend.
- Build de produção e orçamento de bundle.
- E2E em desktop, Pixel 7 e 768×1024.
- Axe WCAG A/AA no dashboard e rotas públicas.
- Navegação por teclado nos detalhes, exclusão, CTA e menu.
- Verificação de overflow horizontal e console no navegador local.
