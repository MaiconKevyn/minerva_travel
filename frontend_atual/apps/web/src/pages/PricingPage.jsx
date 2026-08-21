import React, { useEffect, useState } from 'react';
import { Helmet } from 'react-helmet';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ArrowRight, Check, Heart, ShieldCheck, Sparkles, Star } from 'lucide-react';
import { Button } from '@/components/ui/button';
import Header from '@/components/Header.jsx';
import {
  CompassRose,
  LeafSprig,
  PassportStamp,
  RouteDoodle,
} from '@/components/DecorativeElements.jsx';
import SiteFooter from '@/components/SiteFooter.jsx';
import { formatPrice, getGuideProduct } from '@/utils/minerva-api.js';

const FEATURES = [
  'Livro infantil personalizado em PDF A4',
  'Roteiro ilustrado na ordem da viagem',
  'Atividades calibradas para cada idade',
  'Foto familiar transformada em capa ilustrada',
  'Download privado do guia completo',
];

const TRUST_NOTES = [
  {
    icon: ShieldCheck,
    title: 'Pagamento fora do nosso site',
    description: 'Os dados financeiros são informados no ambiente seguro do Mercado Pago.',
  },
  {
    icon: Star,
    title: 'Uma compra, um livro completo',
    description: 'Sem mensalidade: o valor corresponde ao guia personalizado desta viagem.',
  },
  {
    icon: Heart,
    title: 'A foto continua sendo da família',
    description: 'Uso consentido para criar a capa, com exclusão e privacidade explícitas.',
  },
];

const PricingPage = () => {
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

  const checkoutEnabled = guideProduct?.enabled === true;
  const price = checkoutEnabled
    ? formatPrice(guideProduct.amount_minor, guideProduct.currency)
    : null;

  return (
    <>
      <Helmet>
        <title>Preço do guia - Minerva Travel</title>
        <meta name="description" content="Conheça o conteúdo e o valor do guia personalizado da Minerva Travel." />
      </Helmet>

      <div className="flex min-h-screen flex-col bg-background transition-colors duration-200">
        <Header />

        <main id="main-content" tabIndex={-1} className="flex-1">
          <section className="travel-page storybook-sky storybook-grid relative overflow-hidden border-b border-secondary/10 py-16 lg:py-24">
            <CompassRose className="page-corner -right-5 top-8 rotate-12" />
            <LeafSprig className="page-corner -bottom-8 -left-5 -rotate-12 text-secondary" />

            <div className="guide-shell relative z-10">
              <motion.div
                initial={{ opacity: 0, y: 18 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5 }}
                className="mx-auto max-w-3xl text-center"
              >
                <span className="travel-label -rotate-1">
                  {checkoutEnabled ? 'Compra única' : 'Piloto controlado'}
                </span>
                <h1 className="mt-5 text-4xl font-serif font-bold leading-[1] tracking-[-0.03em] text-secondary md:text-6xl">
                  Um livro inteiro para esta viagem
                </h1>
                <p className="editorial-copy mx-auto mt-5 max-w-2xl text-foreground/70">
                  Não é assinatura nem pacote de créditos. Você paga uma vez e recebe o guia de
                  memórias personalizado da sua família, pronto para imprimir.
                </p>
              </motion.div>

              <div className="mx-auto mt-14 grid max-w-5xl items-center gap-10 lg:grid-cols-[0.78fr_1.22fr] lg:gap-16">
                <motion.div
                  initial={{ opacity: 0, x: -18, rotate: -2 }}
                  animate={{ opacity: 1, x: 0, rotate: -1.5 }}
                  transition={{ duration: 0.62, delay: 0.08 }}
                  className="relative mx-auto w-full max-w-[21rem]"
                >
                  <div className="page-frame p-2">
                    <img
                      src="/activity-examples/cover-sample.webp"
                      alt="Capa ilustrada de exemplo do Guia de Memórias"
                      width="1024"
                      height="1536"
                      className="aspect-[2/3] w-full object-cover"
                    />
                  </div>
                  <PassportStamp className="absolute -bottom-9 -right-8 h-28 w-28 rotate-[-8deg] text-primary/65" />
                  <p className="travel-note absolute -left-12 top-1/3 hidden -rotate-6 sm:block">feito só para vocês</p>
                </motion.div>

                <motion.article
                  initial={{ opacity: 0, y: 24 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.58, delay: 0.12 }}
                  className="travel-card travel-card-pink overflow-hidden p-7 sm:p-9"
                  aria-labelledby="produto-guia-title"
                >
                  <RouteDoodle className="pointer-events-none absolute -right-5 top-1 h-20 w-44 rotate-6 text-secondary/20" />

                  <div className="relative z-10 flex flex-col gap-7">
                    <div className="flex items-start justify-between gap-5">
                      <div>
                        <p className="font-ui text-xs font-extrabold uppercase tracking-[0.2em] text-primary">
                          Bilhete da aventura
                        </p>
                        <h2 id="produto-guia-title" className="mt-2 text-3xl font-serif font-bold text-secondary sm:text-4xl">
                          Guia de Memórias personalizado
                        </h2>
                      </div>
                      <span className="flex h-12 w-12 shrink-0 rotate-3 items-center justify-center rounded-[0.7rem_1rem_0.75rem_1.15rem] bg-primary/10 text-primary">
                        <Sparkles className="h-6 w-6" aria-hidden="true" />
                      </span>
                    </div>

                    <div className="border-y-2 border-dashed border-secondary/20 py-6">
                      <p className="font-ui text-xs font-bold uppercase tracking-[0.18em] text-muted-foreground">Valor do guia completo</p>
                      <p className="mt-1 text-4xl font-serif font-bold text-secondary">
                        {checkoutEnabled ? price : 'Sem cobrança ativa'}
                      </p>
                      <p className="font-ui mt-2 text-sm font-medium text-muted-foreground">
                        {checkoutEnabled
                          ? 'Pagamento único por este guia, processado pelo Mercado Pago.'
                          : 'O preço aparece aqui assim que o checkout deste ambiente for ativado.'}
                      </p>
                    </div>

                    <ul className="grid gap-3 sm:grid-cols-2">
                      {FEATURES.map((feature) => (
                        <li key={feature} className="flex items-start gap-2.5 text-foreground/90">
                          <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-secondary text-secondary-foreground">
                            <Check className="h-3 w-3" aria-hidden="true" />
                          </span>
                          <span className="leading-snug">{feature}</span>
                        </li>
                      ))}
                    </ul>

                    <Button asChild size="lg" className="travel-cta group h-auto w-full px-7 py-4 text-base font-bold sm:text-lg">
                      <Link to="/create">
                        {checkoutEnabled ? 'Criar e comprar meu guia' : 'Criar um guia de teste'}
                        <ArrowRight className="ml-2 h-5 w-5 transition-transform group-hover:translate-x-1" />
                      </Link>
                    </Button>
                  </div>
                </motion.article>
              </div>
            </div>
          </section>

          <section className="travel-page storybook-paper py-16 sm:py-20" aria-labelledby="compra-segura-title">
            <div className="guide-shell">
              <div className="mx-auto max-w-2xl text-center">
                <span className="travel-label">Antes de embarcar</span>
                <h2 id="compra-segura-title" className="mt-4 text-3xl font-serif font-bold text-secondary sm:text-4xl">
                  Simples para comprar. Especial para guardar.
                </h2>
              </div>

              <div className="mt-10 grid gap-5 md:grid-cols-3">
                {TRUST_NOTES.map(({ icon: Icon, title, description }, index) => (
                  <article key={title} className={`travel-card p-6 ${index === 1 ? 'travel-card-blue md:-translate-y-3' : 'travel-card-pink'}`}>
                    <div className="flex h-11 w-11 items-center justify-center rounded-full bg-secondary/10 text-secondary">
                      <Icon className="h-5 w-5" aria-hidden="true" />
                    </div>
                    <h3 className="mt-4 text-xl font-serif font-bold text-secondary">{title}</h3>
                    <p className="mt-2 leading-relaxed text-foreground/70">{description}</p>
                  </article>
                ))}
              </div>
            </div>
          </section>
        </main>

        <SiteFooter />
      </div>
    </>
  );
};

export default PricingPage;
