import React from 'react';
import { motion } from 'framer-motion';
import { GuideLockup } from '@/components/GuideLockup.jsx';

/**
 * Os três passos na gramática da página "Nosso roteiro": bolinha numerada
 * terracota, nome ao lado, rota pontilhada ligando as paradas. Os cards com
 * ícone e borda eram linguagem de landing page — o livro nunca teve caixa.
 */
const STEPS = [
  {
    title: 'Contem a viagem',
    description:
      'Digam os destinos, os pontos turísticos que já estão no roteiro e quem embarca. As idades das crianças ajustam as atividades.',
  },
  {
    title: 'Aprovem a capa',
    description:
      'Vejam a capa ilustrada, peçam mudanças de estilo e aprovem quando ela tiver a cara da família e da viagem.',
  },
  {
    title: 'Recebam o livro por e-mail',
    description:
      'Com um clique, criamos todas as páginas em segundo plano e enviamos o PDF A4 pronto para imprimir e encadernar.',
  },
];

const HowItWorks = () => (
  <section
    className="travel-page editorial-section relative overflow-hidden py-16 sm:py-20"
    aria-labelledby="como-funciona-title"
  >
    <div className="guide-shell">
      <GuideLockup
        id="como-funciona-title"
        overline="Como funciona"
        title="Três passos até o livro de vocês"
        arched="Do roteiro ao PDF"
      />

      <ol className="mx-auto mt-12 flex max-w-md flex-col gap-0 rounded-xl bg-[hsl(var(--mint)/0.65)] p-6 md:max-w-none md:flex-row md:items-start md:gap-0 md:p-8">
        {STEPS.map((step, index) => (
          <React.Fragment key={step.title}>
            {index > 0 ? (
              <>
                {/* A rota pontilhada entre as paradas, como na página do
                    roteiro: deitada no desktop, de pé no celular. */}
                {/* Largura garantida: como item flexível, o conector era a
                    primeira coisa a colapsar a zero e a rota sumia. */}
                <li aria-hidden="true" className="hidden shrink-0 md:block md:w-10 md:pt-5 lg:w-20">
                  <div className="guide-route-h" />
                </li>
                <li aria-hidden="true" className="md:hidden">
                  <div className="guide-route-v ml-[1.35rem] h-8" />
                </li>
              </>
            ) : null}
            <motion.li
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: '-80px' }}
              transition={{ duration: 0.5, delay: index * 0.1 }}
              className="flex gap-4 md:flex-1"
            >
              <span className="guide-bullet" aria-hidden="true">
                {index + 1}
              </span>
              <div>
                <h3 className="pt-1.5 text-xl font-display font-bold text-foreground">
                  {step.title}
                </h3>
                <p className="mt-2 font-serif leading-relaxed text-foreground/70">
                  {step.description}
                </p>
              </div>
            </motion.li>
          </React.Fragment>
        ))}
      </ol>
    </div>
  </section>
);

export default HowItWorks;
