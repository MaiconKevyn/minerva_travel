import React from 'react';
import { motion } from 'framer-motion';
import { GuideLockup } from '@/components/GuideLockup.jsx';

/**
 * A ordem real das páginas que o montador gera, na mesma sequência.
 *
 * Sem isto a home vendia "um guia" sem dizer o que é um guia: dá para achar
 * que é uma folha de atividades solta, quando é um livro com começo, paradas
 * e fim.
 *
 * Cada página é uma nota com a estrelinha mostarda — o marcador das notas de
 * leitura nas folhas ilustradas — em vez de um card com ícone e borda, que o
 * livro nunca teve.
 */
const PAGES = [
  {
    title: 'A capa de vocês',
    description:
      'Com foto, a família inspira a ilustração; sem foto, a capa nasce do roteiro e dos destinos.',
  },
  {
    title: 'Nosso roteiro',
    description: 'Todas as paradas numeradas e ilustradas, na ordem em que vocês vão visitar.',
  },
  {
    title: 'Uma página por ponto turístico',
    description: 'O lugar desenhado, uma curiosidade de verdade e espaço para marcar "já visitei".',
  },
  {
    title: 'As atividades que vocês escolheram',
    description: 'Distribuídas entre as paradas, na dificuldade certa para a idade de cada criança.',
  },
  {
    title: 'Minha melhor memória',
    description: 'Uma página para a criança desenhar e assinar o que mais gostou.',
  },
  {
    title: 'Hora de voltar para casa',
    description: 'O fecho do livro, com linhas para contar a viagem para quem ficou.',
  },
];

const BookAnatomy = () => (
  <section
    className="travel-page editorial-section relative overflow-hidden py-16 sm:py-20"
    aria-labelledby="anatomia-title"
  >
    <div className="guide-shell">
      <GuideLockup
        id="anatomia-title"
        overline="Um livro, não uma folha solta"
        title="Do embarque até a volta para casa"
        arched="Começo, paradas e fim"
      />
      <p className="editorial-copy mx-auto mt-4 max-w-2xl text-center text-foreground/70">
        Todo guia sai com esta espinha dorsal. O miolo muda conforme o roteiro e as idades.
      </p>

      <ol className="mx-auto mt-12 grid max-w-5xl border-y border-secondary/15 sm:grid-cols-2">
        {PAGES.map((page, index) => (
          <motion.li
            key={page.title}
            initial={{ opacity: 0, y: 16 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: '-60px' }}
            transition={{ duration: 0.45, delay: (index % 3) * 0.07 }}
            className={`grid grid-cols-[2.5rem_1fr] gap-4 py-6 sm:px-6 ${index % 2 === 0 ? 'sm:border-r sm:border-secondary/15' : ''} ${index < 4 ? 'border-b border-secondary/15' : index === 4 ? 'border-b border-secondary/15 sm:border-b-0' : ''}`}
          >
            <span className="font-ui pt-0.5 text-sm font-semibold text-primary" aria-hidden="true">
              {String(index + 1).padStart(2, '0')}
            </span>
            <div>
              <h3 className="font-serif text-lg font-semibold text-foreground">{page.title}</h3>
              <p className="mt-1.5 leading-relaxed text-foreground/70">
                {page.description}
              </p>
            </div>
          </motion.li>
        ))}
      </ol>
    </div>
  </section>
);

export default BookAnatomy;
