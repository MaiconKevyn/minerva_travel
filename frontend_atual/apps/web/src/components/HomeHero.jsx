import React from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ArrowRight, Baby, Palette, Printer, Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { OPTIONAL_LANDMARK_ACTIVITY_TYPES } from '@/utils/landmark-activities.js';

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
    className: 'left-[5%] top-10 w-[42%] -rotate-[10deg]',
  },
  {
    image: '/activity-examples/route-sample.webp',
    className: 'right-[5%] top-6 w-[42%] rotate-[9deg]',
  },
];

const PROOF = [
  { icon: Palette, label: `${OPTIONAL_LANDMARK_ACTIVITY_TYPES.length} atividades diferentes` },
  { icon: Baby, label: 'No nível de cada idade' },
  { icon: Printer, label: 'PDF A4 para imprimir' },
];

const HomeHero = () => (
  <section className="relative overflow-hidden parchment-wash pt-10 pb-20 lg:pt-16 lg:pb-28">
    <div className="relative z-10 mx-auto grid max-w-7xl grid-cols-1 items-center gap-14 px-4 sm:px-6 lg:grid-cols-[1.05fr_1fr] lg:gap-16 lg:px-8">
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, ease: 'easeOut' }}
        className="space-y-7 text-center lg:text-left"
      >
        <p className="inline-flex items-center gap-2 rounded-full border border-border/60 bg-card px-4 py-1.5 text-sm font-bold text-secondary shadow-sm">
          <Sparkles className="h-4 w-4" aria-hidden="true" />
          Feito sob medida para o roteiro de vocês
        </p>

        <h1 className="text-4xl font-serif font-bold leading-[1.1] text-foreground sm:text-5xl">
          O livro de atividades da viagem que a sua família já marcou
        </h1>

        <p className="mx-auto max-w-xl text-lg font-medium leading-relaxed text-muted-foreground lg:mx-0 lg:text-xl">
          Você diz os destinos e os pontos turísticos. Nós ilustramos cada parada e montamos as
          brincadeiras no nível de cada criança — para a fila do museu, o avião e a noite no hotel.
        </p>

        <ul className="flex flex-wrap justify-center gap-2 lg:justify-start">
          {PROOF.map((item) => {
            const Icon = item.icon;
            return (
              <li
                key={item.label}
                className="inline-flex items-center gap-2 rounded-full bg-muted px-3.5 py-1.5 text-sm font-bold text-foreground"
              >
                <Icon className="h-4 w-4 text-primary" aria-hidden="true" />
                {item.label}
              </li>
            );
          })}
        </ul>

        <div className="flex flex-col items-center gap-3 pt-1 sm:flex-row lg:justify-start">
          <Button
            asChild
            size="lg"
            className="group w-full rounded-full bg-primary px-8 py-6 text-base font-bold text-white shadow-[0_8px_30px_rgb(160,72,45,0.28)] transition-all duration-300 hover:-translate-y-0.5 hover:bg-primary/90 sm:w-auto sm:text-lg"
          >
            <Link to="/create">
              Criar o guia da minha família
              <ArrowRight className="ml-2.5 h-5 w-5 transition-transform group-hover:translate-x-1" />
            </Link>
          </Button>
          <a
            href="#paginas"
            className="whitespace-nowrap rounded-full px-6 py-3 text-base font-bold text-foreground underline underline-offset-4 transition-colors hover:text-primary"
          >
            Ver as páginas por dentro
          </a>
        </div>

        <p className="text-sm font-medium text-muted-foreground">
          Piloto aberto e sem cobrança enquanto validamos o produto.
        </p>
      </motion.div>

      {/* O leque: capa na frente, roteiro e atividade atrás. */}
      <motion.div
        initial={{ opacity: 0, scale: 0.94 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.7, delay: 0.15, ease: 'easeOut' }}
        className="relative mx-auto w-full max-w-lg"
      >
        <div className="relative aspect-[4/3.5]">
          {PAGES.map((page) => (
            <div key={page.image} className={`page-frame absolute ${page.className}`}>
              <img
                src={page.image}
                alt=""
                width="1024"
                height="1536"
                className="aspect-[2/3] w-full object-cover"
              />
            </div>
          ))}

          <div className="page-frame absolute left-1/2 top-0 w-[50%] -translate-x-1/2">
            {/* Uma descrição só para o conjunto: as duas páginas atrás
                repetiriam a mesma ideia em um leitor de tela. */}
            <img
              src="/activity-examples/cover-sample.webp"
              alt="Três páginas do guia lado a lado: a capa ilustrada com a família, a página do roteiro e um caça-palavras"
              width="1024"
              height="1536"
              className="aspect-[2/3] w-full object-cover"
            />
          </div>
        </div>
      </motion.div>
    </div>
  </section>
);

export default HomeHero;
