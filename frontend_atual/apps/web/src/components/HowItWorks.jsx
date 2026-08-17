import React from 'react';
import { motion } from 'framer-motion';
import { BookHeart, MapPin, Wand2 } from 'lucide-react';

const STEPS = [
  {
    icon: MapPin,
    title: 'Conte a viagem',
    description:
      'Diga os destinos, os pontos turísticos que já estão no roteiro e quem vai viajar. As idades das crianças ajustam as atividades.',
  },
  {
    icon: Wand2,
    title: 'Aprove a sua capa',
    description:
      'Veja a capa ilustrada, peça mudanças de estilo e aprove quando ela representar bem a família e a viagem.',
  },
  {
    icon: BookHeart,
    title: 'Receba o livro por e-mail',
    description:
      'Com um clique, criamos todas as páginas em segundo plano e enviamos o PDF A4 pronto para imprimir e encadernar.',
  },
];

const HowItWorks = () => (
  <section
    className="border-t border-border/50 py-20 sm:py-24"
    aria-labelledby="como-funciona-title"
  >
    <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-2xl text-center">
        <p className="text-sm font-bold uppercase tracking-[0.2em] text-secondary">
          Como funciona
        </p>
        <h2
          id="como-funciona-title"
          className="mt-3 text-3xl font-serif font-bold text-foreground sm:text-4xl"
        >
          Três passos até o livro da sua família
        </h2>
      </div>

      <ol className="mt-14 grid gap-8 md:grid-cols-3">
        {STEPS.map((step, index) => {
          const Icon = step.icon;
          return (
            <motion.li
              key={step.title}
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: '-80px' }}
              transition={{ duration: 0.5, delay: index * 0.1 }}
              className="relative rounded-[2rem] border-2 border-border/60 bg-card p-7 shadow-sm"
            >
              <span
                className="absolute -top-4 left-7 flex h-9 w-9 items-center justify-center rounded-full bg-primary font-serif text-lg font-bold text-white shadow-md"
                aria-hidden="true"
              >
                {index + 1}
              </span>
              <Icon className="mb-4 mt-2 h-8 w-8 text-secondary" aria-hidden="true" />
              <h3 className="mb-2 text-xl font-serif font-bold text-foreground">{step.title}</h3>
              <p className="font-medium leading-relaxed text-muted-foreground">
                {step.description}
              </p>
            </motion.li>
          );
        })}
      </ol>
    </div>
  </section>
);

export default HowItWorks;
