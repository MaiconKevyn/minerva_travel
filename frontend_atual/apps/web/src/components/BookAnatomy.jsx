import React from 'react';
import { motion } from 'framer-motion';
import { BookHeart, Compass, Home, MapPin, PenLine, Sparkles } from 'lucide-react';

/**
 * A ordem real das páginas que o montador gera, na mesma sequência.
 *
 * Sem isto a home vendia "um guia" sem dizer o que é um guia: dá para achar
 * que é uma folha de atividades solta, quando é um livro com começo, paradas
 * e fim.
 */
const PAGES = [
  {
    icon: Sparkles,
    title: 'A capa de vocês',
    description:
      'A foto da família vira ilustração em aquarela, com o sobrenome e o mês da viagem.',
  },
  {
    icon: Compass,
    title: 'Nosso roteiro',
    description: 'Todas as paradas numeradas e ilustradas, na ordem em que vocês vão visitar.',
  },
  {
    icon: MapPin,
    title: 'Uma página por ponto turístico',
    description: 'O lugar desenhado, uma curiosidade de verdade e espaço para marcar "já visitei".',
  },
  {
    icon: PenLine,
    title: 'As atividades que vocês escolheram',
    description: 'Distribuídas entre as paradas, na dificuldade certa para a idade de cada criança.',
  },
  {
    icon: BookHeart,
    title: 'Minha melhor memória',
    description: 'Uma página para a criança desenhar e assinar o que mais gostou.',
  },
  {
    icon: Home,
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
      <div className="mx-auto max-w-2xl text-center">
        <p className="text-sm font-bold uppercase tracking-[0.2em] text-secondary">
          Um livro, não uma folha solta
        </p>
        <h2
          id="anatomia-title"
          className="mt-3 text-3xl font-serif font-bold text-foreground sm:text-4xl"
        >
          Do embarque até a volta para casa
        </h2>
        <p className="mt-4 text-lg font-medium text-muted-foreground">
          Todo guia sai com esta espinha dorsal. O miolo muda conforme o roteiro e as idades.
        </p>
      </div>

      <ol className="mt-14 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
        {PAGES.map((page, index) => {
          const Icon = page.icon;
          return (
            <motion.li
              key={page.title}
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: '-60px' }}
              transition={{ duration: 0.45, delay: (index % 3) * 0.07 }}
              className="rounded-[1.75rem] border-2 border-border/60 bg-background p-6"
            >
              <div className="flex items-center gap-3">
                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">
                  <Icon className="h-5 w-5" aria-hidden="true" />
                </span>
                <h3 className="font-serif text-lg font-bold text-foreground">{page.title}</h3>
              </div>
              <p className="mt-3 font-medium leading-relaxed text-muted-foreground">
                {page.description}
              </p>
            </motion.li>
          );
        })}
      </ol>
    </div>
  </section>
);

export default BookAnatomy;
