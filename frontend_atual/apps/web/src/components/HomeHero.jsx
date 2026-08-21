import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ArrowRight } from 'lucide-react';
import { GuideStar } from '@/components/GuideLockup.jsx';
import { OPTIONAL_LANDMARK_ACTIVITY_TYPES } from '@/utils/landmark-activities.js';
import { formatPrice, getGuideProduct } from '@/utils/minerva-api.js';

/**
 * O hero do mockup (docs/minerva-home-3a.png): título em Baloo sobre a areia,
 * a palavra "livro" marcada a marca-texto mostarda, e à direita um leque de
 * páginas de verdade — labirinto, diário, capa e colorir — com a estrela e o
 * carimbo "Feito para imprimir".
 */

// A rotação fica em classe CSS, não em prop do framer-motion: a animação
// escreve `transform` inline e apagaria o ângulo, deixando o leque reto.
const FAN_PAGES = [
  {
    image: '/activity-examples/maze-real.webp',
    className: 'left-0 top-[16%] w-[40%] -rotate-[9deg]',
    z: 'z-[1]',
  },
  {
    image: '/activity-examples/travel-diary-real.webp',
    className: 'left-[20%] top-[8%] w-[43%] -rotate-[3.5deg]',
    z: 'z-[2]',
  },
  {
    image: '/activity-examples/coloring-real.webp',
    className: 'left-[78%] top-[10%] w-[40%] rotate-[11deg]',
    z: 'z-0',
  },
];

// As três bandeirinhas do topo, na ordem e nas cores do mockup.
const FLAGS = [
  { label: `${OPTIONAL_LANDMARK_ACTIVITY_TYPES.length} atividades`, tone: 'pill-flag--blush' },
  { label: 'por idade', tone: 'pill-flag--mint' },
  { label: 'PDF A4', tone: 'pill-flag--paper' },
];

// A trilha pontilhada que sobe das bandeirinhas em direção ao leque, como um
// caminho de roteiro desenhado a lápis.
const DOT_TRAIL = [
  { cx: 12, cy: 128, r: 7 },
  { cx: 34, cy: 104, r: 8 },
  { cx: 60, cy: 82, r: 9 },
  { cx: 92, cy: 62, r: 9 },
  { cx: 128, cy: 46, r: 10 },
  { cx: 168, cy: 34, r: 10 },
  { cx: 210, cy: 28, r: 11 },
  { cx: 252, cy: 30, r: 10 },
  { cx: 292, cy: 40, r: 9 },
  { cx: 326, cy: 56, r: 8 },
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
    <section className="relative overflow-hidden pb-24 pt-10 sm:pb-28 sm:pt-14 lg:pb-32 lg:pt-16">
      <div className="guide-shell relative z-10 grid items-center gap-x-8 gap-y-14 lg:grid-cols-[0.94fr_1.06fr]">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, ease: 'easeOut' }}
          className="relative text-center lg:text-left"
        >
          <svg
            viewBox="0 0 340 140"
            aria-hidden="true"
            className="pointer-events-none absolute -top-8 right-0 hidden w-72 text-primary/30 lg:block"
          >
            {DOT_TRAIL.map((dot) => (
              <circle key={`${dot.cx}-${dot.cy}`} {...dot} fill="currentColor" />
            ))}
          </svg>

          <div className="flex flex-wrap items-center justify-center gap-2.5 lg:justify-start">
            {FLAGS.map((flag) => (
              <span key={flag.label} className={`pill-flag ${flag.tone}`}>
                {flag.label}
              </span>
            ))}
          </div>

          <h1 className="mt-7 font-display text-[3.1rem] font-extrabold leading-[1.02] tracking-[-0.01em] text-secondary sm:text-[4.2rem] lg:text-[4.6rem]">
            A viagem
            <span className="block">da família</span>
            <span className="block text-primary">
              vira um{' '}
              <span className="highlight-blob text-foreground">livro</span>
            </span>
          </h1>

          <p className="editorial-copy mx-auto mt-6 max-w-lg text-[1.12rem] leading-[1.75] text-foreground/80 lg:mx-0 lg:text-[1.26rem]">
            O roteiro que vocês já marcaram volta ilustrado, com os lugares da viagem e uma
            missão para a criança em cada parada.
          </p>

          <div className="mt-9 flex flex-col items-center gap-5 sm:flex-row sm:gap-7 lg:justify-start">
            <Link
              to="/create"
              className="travel-cta group inline-flex w-full items-center justify-center gap-2.5 px-8 py-4 text-lg sm:w-auto"
            >
              Criar o guia da família
              <ArrowRight className="h-5 w-5 transition-transform group-hover:translate-x-1" />
            </Link>
            <a href="#guia-exemplo" className="travel-paper-link whitespace-nowrap px-1 py-2 text-lg">
              Folhear o exemplo
            </a>
          </div>

          {guideProduct?.enabled ? (
            <p className="travel-note mt-9 inline-block">
              {`compra única de ${formatPrice(guideProduct.amount_minor, guideProduct.currency)} — sem assinatura`}
            </p>
          ) : null}
        </motion.div>

        {/* O leque: quatro páginas de verdade espalhadas como sobre a mesa.
            A folha de colorir sangra para fora da tela, como no mockup. */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95, rotate: 1 }}
          animate={{ opacity: 1, scale: 1, rotate: 0 }}
          transition={{ duration: 0.72, delay: 0.12, ease: 'easeOut' }}
          className="relative mx-auto w-full max-w-[27rem] lg:max-w-none"
        >
          <div className="relative aspect-[10/9] w-full sm:aspect-[10/8.5]">
            <GuideStar className="absolute left-[46%] top-[-3%] z-20 h-12 w-12 -rotate-[14deg] sm:h-14 sm:w-14" />

            {FAN_PAGES.map((page) => (
              <div
                key={page.image}
                className={`absolute overflow-hidden rounded-xl shadow-[0_18px_34px_-18px_hsl(30_27%_13%/0.45)] ${page.z} ${page.className}`}
              >
                <img
                  src={page.image}
                  alt=""
                  width="1024"
                  height="1536"
                  sizes="(min-width: 1024px) 21vw, 38vw"
                  decoding="async"
                  className="aspect-[2/3] w-full object-cover"
                />
              </div>
            ))}

            <div className="absolute left-[45%] top-[2%] z-10 w-[46%] overflow-hidden rounded-xl shadow-[0_22px_40px_-18px_hsl(30_27%_13%/0.5)] rotate-[3deg]">
              <img
                src="/activity-examples/cover-sample.webp"
                alt="Páginas do guia em leque: a capa ilustrada da família, o labirinto de um ponto turístico, o diário de viagem e a página de colorir"
                width="1024"
                height="1536"
                sizes="(min-width: 1024px) 24vw, 44vw"
                decoding="async"
                className="aspect-[2/3] w-full object-cover"
              />
            </div>

            <div className="stamp-circle absolute -bottom-14 left-[30%] z-20 h-36 w-36 text-[1.05rem] sm:-bottom-[4.5rem] sm:h-[10.5rem] sm:w-[10.5rem] sm:text-[1.2rem]">
              <span>
                Feito
                <br />
                para
                <br />
                imprimir
              </span>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  );
};

export default HomeHero;
