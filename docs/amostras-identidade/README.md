# Amostras da identidade Destinations

Um roteiro simples — Família Knopp em Paris, setembro de 2026 — gerado pelo
pipeline de produção depois da troca de identidade (commit `b06acf5`). Serve
para comparar o antes e o depois sem precisar gerar um guia inteiro.

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

**Dois mundos tipográficos — já resolvido no código, ainda visível aqui.**
Compare `06-colorir-louvre` com `02-nosso-roteiro`: o primeiro usa Zilla Slab,
desenhada pelo compositor; o segundo tem a tipografia desenhada pela IA. As
quatro páginas ilustradas (capa, roteiro, destino e ponto turístico) já
migraram para o código — a arte chega sem letra nenhuma e o compositor escreve
por cima. **Estas imagens são anteriores à migração** e só somem quando forem
regeradas:

```bash
python scripts/generate_sample_guide.py --tudo
```

O mesmo comando republica o folheável do site e os cards de exemplo, que são
cópias do mesmo render — foi a geração à mão que as fez divergir.

**Os painéis continuam.** A referência não usa caixa nenhuma, mas as nossas
carregam função — grade, instrução, lista. Desvio consciente.

## Tinta por folha

Medido sobre estas amostras, com o estilo antigo como comparação:

| página | tinta |
|---|---|
| colorir | 9% |
| minha melhor memória | 11% |
| labirinto | 12% |
| nosso roteiro | 21% |
| destino | 22% |
| torre eiffel | 24% |
| capa | 27% |
| *caça-palavras no estilo antigo* | *17%* |

O fundo claro é uma adaptação deliberada: a referência usa fundos saturados
nos cartões de título, mas estas folhas são impressas em casa e escritas a
lápis. Um fundo cobalto chapado consome 65% de tinta e o grafite some nele.
