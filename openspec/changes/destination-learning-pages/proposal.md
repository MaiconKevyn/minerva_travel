## Why

O builder progressivo já cria capa, resumo, páginas de pontos turísticos e atividades, mas não
apresenta o contexto do destino antes dos pontos. Além disso, muitos pontos sem uma curiosidade
editorial explícita terminam apenas com uma missão de observação, o que reduz o valor pedagógico
do guia.

O livro de referência em `docs/Exploradores.pdf` demonstra uma hierarquia mais clara para
crianças: primeiro uma abertura da cidade/país com fatos curtos; depois uma página de cada ponto
com descrição, curiosidade e ilustração reconhecível. Essa hierarquia também precisa funcionar em
roteiros com mais de um país e continuar sendo revisável diretamente na UI antes do PDF.

## What Changes

- Adicionar uma página `destination_intro` antes do primeiro ponto de cada destino selecionado.
- Mostrar cidade, país, dois aprendizados curtos e uma curiosidade confiável na própria imagem.
- Reordenar o plano como capa, resumo, destino, pontos/atividades daquele destino, próximo destino
  e, ao final, `Minha melhor memória`.
- Reforçar o prompt de cada ponto com as seções exatas `Conheça o lugar` e `Você sabia?`.
- Adicionar um checkbox imprimível `Já visitei` em toda página de ponto turístico.
- Quando um ponto não tiver curiosidade factual confiável, usar `Missão de observação` e nunca
  pedir ao modelo de imagem para inventar um fato.
- Gerar aberturas de destino sem pessoas ou referências da família. Regenerações usam somente a
  versão selecionada da própria página.
- Expor na UI o novo tipo, o destino e todo texto obrigatório para revisão antes da aprovação.
- Preservar a exportação existente: cada PNG aprovado continua ocupando uma página do PDF.

## Capabilities

### New Capabilities

- `destination-learning-pages`: resolução de contexto pedagógico, planejamento, geração e revisão
  de uma abertura para cada destino selecionado.

### Modified Capabilities

- `progressive-guide-page-generation`: inclui páginas de destino na sequência imutável.
- `openai-guide-page-art`: adiciona prompt de abertura pedagógica e reforça a hierarquia textual
  das páginas de pontos.
- `guide-content-generation`: diferencia curiosidade confiável de missão de observação.

## Impact

- Modelos privados e públicos do builder.
- Planejamento e limite máximo de páginas progressivas.
- Protocolo e prompts do gerador OpenAI.
- UI de montagem, contrato OpenAPI e testes frontend.
- Testes de ordem, fallback, geração/regeneração e PDF.

## Non-Goals

- Copiar personagens, identidade visual ou texto do PDF de referência.
- Gerar automaticamente fatos novos com o modelo de imagem.
- Inserir a família por padrão nas páginas de destino.
- Migrar sessões do builder já materializadas.
