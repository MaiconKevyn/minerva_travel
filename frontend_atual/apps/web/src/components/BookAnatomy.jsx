import React from 'react';
import { motion } from 'framer-motion';
import { GuideLockup, GuideStar } from '@/components/GuideLockup.jsx';

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
      'A foto da família vira ilustração, com o sobrenome e o mês da viagem escritos na fonte do livro.',
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
    className="border-t border-border/50 bg-card py-20 sm:py-24"
    aria-labelledby="anatomia-title"
  >
    <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
      <GuideLockup
        id="anatomia-title"
        overline="Um livro, não uma folha solta"
        title="Do embarque até a volta para casa"
        arched="Começo, paradas e fim"
      />
      <p className="mx-auto mt-4 max-w-2xl text-center text-lg font-medium text-muted-foreground">
        Todo guia sai com esta espinha dorsal. O miolo muda conforme o roteiro e as idades.
      </p>

      <ol className="mx-auto mt-14 grid max-w-5xl gap-x-12 gap-y-8 sm:grid-cols-2 lg:grid-cols-3">
        {PAGES.map((page, index) => (
          <motion.li
            key={page.title}
            initial={{ opacity: 0, y: 16 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: '-60px' }}
            transition={{ duration: 0.45, delay: (index % 3) * 0.07 }}
            className="flex gap-3"
          >
            <GuideStar className="mt-0.5 h-6 w-6" />
            <div>
              <h3 className="font-serif text-lg font-bold text-foreground">{page.title}</h3>
              <p className="mt-1.5 font-medium leading-relaxed text-muted-foreground">
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
