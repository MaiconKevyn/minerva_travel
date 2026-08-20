# Amostras da identidade Destinations

Um roteiro simples — Família Knopp em Paris, setembro de 2026 — gerado pelo
pipeline de produção. Serve para ver o resultado sem precisar gerar um guia
inteiro. A família da capa é inventada e descrita por escrito; nenhuma foto de
pessoa real entra neste fluxo.

Para regerar tudo:

```bash
python scripts/generate_sample_guide.py --tudo
```

O mesmo comando republica o folheável da página inicial e os cards de exemplo,
que são cópias do mesmo render — foi a geração à mão que as fez divergir. Use
`--somente-publicar` para republicar os PNGs do rascunho sem gastar geração.

| página | o que mostra |
|---|---|
| `01-capa` | capa da família, redesenhada a partir do retrato |
| `02-nosso-roteiro` | sumário da viagem com a rota entre as paradas |
| `03-destino-paris` | abertura de destino |
| `04-torre-eiffel` | página de ponto turístico |
| `05-labirinto` | atividade com painel desenhado por código sobre a arte |
| `06-colorir-louvre` | registro de traço puro, para a criança pintar |
| `07-minha-melhor-memoria` | página de escrever, com área em branco validada |

A referência é o projeto *Inspired Arts Destinations*, de Arantxa Larrea. O
estilo canônico mora em `src/minerva_travel/visual_identity.py`.

## Duas coisas que as amostras expõem

**Uma tipografia só.** Toda letra destas páginas foi escrita pelo compositor,
em Zilla Slab: a arte chega sem nenhuma. Antes, as páginas ilustradas traziam
a tipografia que a IA desenhava — diferente a cada geração e diferente das
páginas de atividade, dentro do mesmo livro.

**Os painéis continuam.** A referência não usa caixa nenhuma, mas as nossas
carregam função — grade, instrução, lista. Desvio consciente.

## Tinta por folha

Medido sobre estas amostras (fração da folha coberta, como a impressora vê):

| página | tinta |
|---|---|
| colorir | 9% |
| minha melhor memória | 10% |
| labirinto | 11% |
| destino | 13% |
| torre eiffel | 14% |
| nosso roteiro | 17% |
| capa | 26% |

O fundo claro é uma adaptação deliberada: a referência usa fundos saturados
nos cartões de título, mas estas folhas são impressas em casa e escritas a
lápis. Um fundo cobalto chapado consome 65% de tinta e o grafite some nele.
