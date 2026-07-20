## Context

O `Destination` do catálogo já possui `intro` e pode possuir `curiosities`. Destinos
personalizados conhecidos também recebem conteúdo do catálogo editorial de
`destination_facts.py`. O builder, porém, atualmente reduz a seleção diretamente a contextos de
pontos turísticos e não preserva uma página pedagógica de destino.

As imagens finais são geradas e aprovadas uma a uma. O texto obrigatório fica em
`required_copy`, os bytes aprovados são imutáveis e a exportação PDF apenas concatena esses PNGs.

## Goals / Non-Goals

**Goals:**

- Criar exatamente uma abertura para cada destino que possua ao menos um ponto selecionado.
- Dar contexto de cidade e país antes de apresentar seus pontos.
- Colocar texto curto, infantil e verificável dentro da imagem gerada.
- Manter fatos estáveis entre versões e impedir invenção factual pelo modelo de imagem.
- Preservar limites de custo, privacidade, aprovação sequencial e exportação atual.

**Non-Goals:**

- Enriquecimento factual em tempo real pela internet.
- Página separada para país e outra para cidade na primeira versão.
- Mostrar personagens genéricos diferentes da família.
- Alterar o compositor do PDF.

## Page Sequence

O servidor percorre os pontos na ordem confirmada e insere a abertura na primeira ocorrência de
cada destino:

```text
cover
trip_summary
destination_intro-paris
landmark-eiffel
activities-eiffel...
landmark-louvre
destination_intro-london
landmark-tower-bridge
activities-tower-bridge...
best_memory
```

Se pontos do mesmo destino reaparecerem mais tarde, a abertura não é duplicada. Sessões antigas
mantêm seu array materializado sem migração.

## Decisions

### Decision 1: Contexto de destino resolvido somente no servidor

Cada abertura armazena `destination_id`, cidade, país, título, dois aprendizados, curiosidade,
tipo da curiosidade, nomes dos pontos vinculados e ordem. O cliente não envia prompts, fatos,
cópia ou posição.

O título visual usa a cidade quando disponível e o país como subtítulo. Isso suporta o padrão
do livro (`Londres`) e garante que roteiros internacionais mostrem o país correspondente.

### Decision 2: Fonte editorial e fallback seguro

Os dois aprendizados vêm de `Destination.intro`, normalizados, deduplicados e limitados. A
curiosidade segue esta prioridade:

1. `Destination.curiosities`;
2. catálogo editorial de `lookup_destination_facts(city, country)`;
3. outro item ainda não usado de `Destination.intro`;
4. missão de observação não factual.

Para pontos turísticos, uma `Landmark.curiosity` explícita é preferida. Se ela não existir, o
segundo parágrafo editorial da descrição pode ser promovido a curiosidade confiável. Descrições
genéricas de pontos personalizados continuam como observação, não como fato.

### Decision 3: Contrato de texto da abertura

O prompt renderiza exatamente uma vez:

- título da cidade/destino;
- país, quando houver;
- `Descubra este destino`;
- dois aprendizados curtos;
- `Você sabia?` ou `Missão de observação`;
- curiosidade/missão.

A composição se inspira na hierarquia de um diário infantil de viagem: título grande, pequenos
blocos de aprendizado, uma ilustração reconhecível e um cartão de curiosidade. Não copia bordas,
personagens ou texto do PDF fornecido.

### Decision 4: Pessoas ficam proibidas nas aberturas

A primeira geração usa `/images/generations` sem foto ou capa da família. A regeneração usa
`/images/edits` somente com a versão selecionada. O prompt remove pessoas herdadas da referência
e a UI não mostra `Incluir família` para esse tipo.

### Decision 5: Página de ponto ganha hierarquia pedagógica explícita

O prompt atual já recebe descrição e curiosidade exatas. Ele passa a exigir layout com o título,
local, ilustração reconhecível, `Conheça o lugar`, descrição, rótulo de curiosidade/missão e o
respectivo texto. O modelo não pode acrescentar outros fatos ou textos.

### Decision 6: Custo e PDF permanecem genéricos

O máximo progressivo cresce em até `MAX_GUIDE_DESTINATIONS`. A quota existente continua maior
que o plano máximo. Como `destination_intro` produz PNG 1024x1536 e entra no array de páginas, a
exportação já o inclui automaticamente sem ramo especial.

### Decision 7: O checkbox `Já visitei` é composto pelo servidor

Toda página `landmark` reserva uma faixa calma no rodapé. Depois da geração ou edição pela OpenAI,
o servidor aplica um painel pequeno com um quadrado vazio e o texto exato `Já visitei`. O elemento
funcional não é delegado ao modelo de imagem, evitando caixas deformadas, texto incorreto ou
desaparecimento entre regenerações. Ele entra em `required_copy`, permanece igual com ou sem
família e é preservado no PNG aprovado e no PDF.

## Validation Strategy

- Plano com um e vários destinos, atividades intercaladas e memória final.
- Apenas destinos realmente selecionados recebem abertura e cada abertura aparece uma vez.
- Cópia confiável e fallback de observação não inventam fatos.
- Prompt da abertura preserva todas as strings, proíbe pessoas e usa geração/edição corretas.
- Prompt de ponto inclui rótulos pedagógicos e preserva texto durante revisões.
- Compositor adiciona quadrado vazio e `Já visitei` em todas as versões de ponto.
- API despacha `destination_intro` sem foto/capa da família.
- UI rotula o novo tipo e mostra país/destino para revisão.
- PDF sintético mantém a nova ordem e uma imagem por página.

## Risks / Trade-offs

- Mais uma página por destino aumenta custo e tempo de revisão. A quantidade é limitada pelo
  número já limitado de destinos selecionados.
- Textos demais reduzem a legibilidade do modelo. A primeira versão limita a dois aprendizados e
  uma curiosidade curta.
- Destinos desconhecidos podem não ter fatos editoriais. O fallback assume isso claramente e
  oferece uma missão de observação em vez de uma afirmação não verificada.
