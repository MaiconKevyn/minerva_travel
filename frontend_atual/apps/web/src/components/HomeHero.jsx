import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ArrowRight } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { ArchedText, GuideStar } from '@/components/GuideLockup.jsx';
import {
  Airplane,
  CompassRose,
  LeafSprig,
  RouteDoodle,
} from '@/components/DecorativeElements.jsx';
import { OPTIONAL_LANDMARK_ACTIVITY_TYPES } from '@/utils/landmark-activities.js';
import { formatPrice, getGuideProduct } from '@/utils/minerva-api.js';

/**
 * O produto é um livro inteiro, não uma capa bonita.
 *
 * A vitrine antiga mostrava uma capa solta flutuando, e quem chegava aqui não
 * tinha como saber que existem dezoito atividades dentro. O leque mostra três
 * páginas ao mesmo tempo — capa, roteiro e uma atividade — que é a primeira
 * coisa que precisa ficar clara.
 */
// A rotação fica em classe CSS, não em prop do framer-motion: a animação
// escreve `transform` inline e apagaria o ângulo, deixando o leque reto.
const PAGES = [
  {
    image: '/activity-examples/word-search-real.webp',
    // A rotação estufa a caixa: encostadas na borda, as páginas de trás
    // saíam cortadas pela metade no celular.
    className: 'left-[1%] top-16 w-[42%] -rotate-[9deg] sm:left-[4%]',
  },
  {
    image: '/activity-examples/route-sample.webp',
    className: 'right-[1%] top-10 w-[42%] rotate-[8deg] sm:right-[4%]',
  },
];

// As provas na voz do livro: notas com a estrelinha mostarda, como as notas
// de leitura da página de destino — não chips de landing page.
const PROOF = [
  `${OPTIONAL_LANDMARK_ACTIVITY_TYPES.length} atividades diferentes`,
  'No nível de cada idade',
  'PDF A4 para imprimir',
];

const HomeHero = () => {
  const [guideProduct, setGuideProduct] = useState(null);

  useEffect(() => {
    const controller = new AbortController();
    getGuideProduct({ signal: controller.signal })
      .then(setGuideProduct)
      .catch((error) => {
        if (error.name !== 'AbortError') setGuideProduct(null);
      });
    return () => controller.abort();
  }, []);

  return (
    <section className="travel-page storybook-sky storybook-grid relative overflow-hidden border-b border-secondary/10 py-12 sm:py-16 lg:py-20">
      <CompassRose className="page-corner -right-5 top-10 rotate-12" />
      <LeafSprig className="page-corner -bottom-8 -left-5 -rotate-12 text-secondary" />
      <Airplane className="pointer-events-none absolute left-[48%] top-16 hidden h-12 w-12 -rotate-12 text-primary/15 lg:block" />

      <div className="guide-shell relative z-10 grid items-center gap-10 lg:grid-cols-[0.88fr_1.12fr] lg:gap-16">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, ease: 'easeOut' }}
          className="text-center lg:text-left"
        >
          <div className="mx-auto max-w-sm text-secondary lg:mx-0">
            <ArchedText direction="up">Guia de Memórias</ArchedText>
          </div>

          <h1 className="!mt-0 text-[2.55rem] font-serif font-bold leading-[0.98] tracking-[-0.03em] text-secondary sm:text-6xl lg:text-[4rem]">
            A viagem da família vira um livro
          </h1>

          <p className="editorial-copy mx-auto mt-5 max-w-xl text-foreground/75 lg:mx-0">
            Um guia ilustrado com o roteiro, os lugares e atividades na idade de cada criança —
            pronto para imprimir e levar na mala.
          </p>

          <p className="font-ui mt-5 text-sm font-semibold text-foreground/70 sm:text-base">
            {guideProduct?.enabled
              ? `Compra única de ${formatPrice(guideProduct.amount_minor, guideProduct.currency)}`
              : 'Piloto aberto e sem cobrança'}
            <span className="mx-2 text-primary" aria-hidden="true">·</span>
            PDF A4 pronto para imprimir
          </p>

          <div className="mt-7 flex flex-col items-center gap-4 sm:flex-row lg:justify-start">
            <Button
              asChild
              size="lg"
              className="travel-cta group h-auto w-full px-7 py-4 text-base font-bold sm:w-auto"
            >
              <Link to="/create">
                Criar o guia da família
                <ArrowRight className="ml-2.5 h-5 w-5 transition-transform group-hover:translate-x-1" />
              </Link>
            </Button>
            <a href="#guia-exemplo" className="travel-paper-link whitespace-nowrap px-1 py-2 text-base">
              Ver o guia demonstrativo
            </a>
          </div>

          <ul className="mt-7 grid gap-2.5 border-t border-secondary/15 pt-5 text-left sm:grid-cols-3">
            {PROOF.map((item) => (
              <li key={item} className="flex items-start gap-2 font-ui text-sm font-semibold leading-snug text-secondary">
                <GuideStar className="mt-0.5 h-4 w-4" />
                {item}
              </li>
            ))}
          </ul>
        </motion.div>

        {/* Um pequeno mapa editorial: as páginas são as paradas e a rota as
            conecta. No celular ele vem logo após o título: a família vê o
            produto antes de precisar ler toda a explicação. */}
        <motion.div
          initial={{ opacity: 0, scale: 0.94, rotate: 1 }}
          animate={{ opacity: 1, scale: 1, rotate: 0 }}
          transition={{ duration: 0.72, delay: 0.12, ease: 'easeOut' }}
          className="relative mx-auto w-full max-w-xl"
        >
          <RouteDoodle className="pointer-events-none absolute -right-4 top-0 z-20 h-24 w-48 rotate-6 text-secondary/55" />
          <p className="travel-note absolute -right-1 top-20 z-20 hidden sm:block">cada parada vira uma descoberta</p>

          <div className="relative mx-auto aspect-[4/3.25] w-full max-w-[25rem] rounded-xl bg-[hsl(var(--paper)/0.28)] p-4 sm:aspect-[4/3.55] sm:max-w-none">
            {PAGES.map((page) => (
              <div key={page.image} className={`page-frame absolute ${page.className}`}>
                <img
                  src={page.image}
                  alt=""
                  width="1024"
                  height="1536"
                  sizes="(min-width: 1024px) 22vw, 42vw"
                  decoding="async"
                  className="aspect-[2/3] w-full object-cover"
                />
              </div>
            ))}

            <div className="page-frame absolute left-1/2 top-0 z-10 w-[50%] -translate-x-1/2">
              <img
                src="/activity-examples/cover-sample.webp"
                alt="Três páginas do guia lado a lado: a capa ilustrada com a família, a página do roteiro e um caça-palavras"
                width="1024"
                height="1536"
                sizes="(min-width: 1024px) 27vw, 50vw"
                decoding="async"
                className="aspect-[2/3] w-full object-cover"
              />
            </div>
          </div>

          <div className="travel-stamp absolute bottom-0 left-1 rotate-[-7deg] bg-[hsl(var(--paper)/0.82)] text-secondary sm:bottom-4">
            feito para imprimir
          </div>
        </motion.div>
      </div>
    </section>
  );
};

export default HomeHero;
