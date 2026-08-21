import React from 'react';
import { motion } from 'framer-motion';

/**
 * Amostra das páginas que o produto realmente gera. São os mesmos arquivos
 * usados como exemplo na escolha de atividades, então o que a home promete é
 * exatamente o que a família recebe — nada de imagem de banco genérica.
 */
const PAGES = [
  { image: '/activity-examples/cover-sample.webp', title: 'Capa da família', caption: 'Com o nome e o ano da viagem' },
  { image: '/activity-examples/route-sample.webp', title: 'Roteiro ilustrado', caption: 'O caminho da aventura em um mapa' },
  { image: '/activity-examples/detail-hunt-real.webp', title: 'Caça aos detalhes', caption: 'Para observar o lugar de perto' },
  { image: '/activity-examples/word-search-real.webp', title: 'Caça-palavras', caption: 'Com palavras do próprio passeio' },
  { image: '/activity-examples/coloring-real.webp', title: 'Página para colorir', caption: 'O ponto turístico em tracejado' },
  { image: '/activity-examples/investigator-real.webp', title: 'Missão do investigador', caption: 'Uma missão secreta por criança' },
];

const PageGallery = () => (
  // A galeria assenta na areia do site: os cartões de papel (.page-frame)
  // é que flutuam por cima, como as folhas sobre a mesa do mockup.
  <section
    id="paginas"
    className="scroll-mt-20 border-t border-border/50 py-20 sm:py-24"
    aria-labelledby="paginas-title"
  >
    <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-2xl text-center">
        <p className="travel-label">
          Por dentro do guia
        </p>
        <h2
          id="paginas-title"
          className="mt-3 font-display text-3xl font-bold text-secondary sm:text-4xl"
        >
          Páginas de verdade, feitas para a sua viagem
        </h2>
        <p className="editorial-copy mt-4 text-foreground/70">
          Cada página é ilustrada com os lugares que vocês escolheram e as idades das crianças.
        </p>
      </div>

      <ul className="mt-14 grid grid-cols-2 gap-5 sm:gap-6 lg:grid-cols-3">
        {PAGES.map((page, index) => (
          <motion.li
            key={page.image}
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: '-60px' }}
            transition={{ duration: 0.5, delay: (index % 3) * 0.08 }}
          >
            <figure className="group">
              {/* O chrome de papel-creme da identidade em volta da folha. */}
              <div className="page-frame transition-transform duration-300 group-hover:-translate-y-1">
                <img
                  src={page.image}
                  alt={`Exemplo de página do guia: ${page.title}`}
                  loading="lazy"
                  width="1024"
                  height="1536"
                  className="aspect-[2/3] w-full object-cover"
                />
              </div>
              <figcaption className="mt-3 text-center">
                <p className="font-display text-base font-bold text-secondary sm:text-lg">
                  {page.title}
                </p>
                <p className="font-serif text-sm font-medium text-muted-foreground">{page.caption}</p>
              </figcaption>
            </figure>
          </motion.li>
        ))}
      </ul>
    </div>
  </section>
);

export default PageGallery;
