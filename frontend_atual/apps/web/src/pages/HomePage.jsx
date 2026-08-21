import React from 'react';
import { Helmet } from 'react-helmet';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ArrowRight } from 'lucide-react';
import { ArchedText } from '@/components/GuideLockup.jsx';
import { Button } from '@/components/ui/button';
import Header from '@/components/Header.jsx';
import HomeHero from '@/components/HomeHero.jsx';
import SampleGuideReader from '@/components/SampleGuideReader.jsx';
import BookAnatomy from '@/components/BookAnatomy.jsx';
import HowItWorks from '@/components/HowItWorks.jsx';
import ActivityShowcase from '@/components/ActivityShowcase.jsx';
import HomeFaq from '@/components/HomeFaq.jsx';
import SiteFooter from '@/components/SiteFooter.jsx';
import { MapPinDoodle, RouteDoodle } from '@/components/DecorativeElements.jsx';

const HomePage = () => (
  <>
    <Helmet>
      <title>Minerva Travel - Livro de atividades da viagem da sua família</title>
      <meta
        name="description"
        content="Transforme o roteiro que a sua família já marcou em um livro de atividades ilustrado, no nível de cada criança, em PDF A4 para imprimir."
      />
    </Helmet>

    <div className="flex min-h-screen flex-col bg-background transition-colors duration-200">
      <Header />

      <main id="main-content" tabIndex={-1} className="flex-1">
        <HomeHero />
        <SampleGuideReader />
        <BookAnatomy />
        <HowItWorks />
        <ActivityShowcase />
        <HomeFaq />

        {/* Fechamento: quem rolou a página inteira não pode precisar subir
            de volta até o topo para achar o botão. */}
        <section
          className="travel-page storybook-blush relative overflow-hidden border-t border-primary/10 py-20 sm:py-24"
          aria-labelledby="comecar-title"
        >
          <MapPinDoodle className="pointer-events-none absolute -bottom-6 -left-4 h-36 w-36 -rotate-12 text-primary/10" />
          <RouteDoodle className="pointer-events-none absolute -right-5 top-8 hidden h-36 w-72 rotate-6 text-secondary/20 sm:block" />
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: '-80px' }}
            transition={{ duration: 0.5 }}
            className="mx-auto max-w-2xl px-4 text-center sm:px-6 lg:px-8"
          >
            {/* O fechamento fala como a capa: o nome do produto em arco por
                cima do título. */}
            <div className="mx-auto max-w-sm text-secondary">
              <ArchedText direction="up">Guia de Memórias</ArchedText>
            </div>
            <h2
              id="comecar-title"
              className="!mt-1 text-3xl font-serif font-bold leading-tight text-secondary sm:text-5xl"
            >
              A viagem já está marcada. Falta o livro.
            </h2>
            <p className="editorial-copy mt-4 text-foreground/70">
              Comece pelo roteiro que vocês já têm — em poucos minutos você vê a primeira página
              ilustrada na tela.
            </p>
            <Button
              asChild
              size="lg"
              className="travel-cta group mt-8 h-auto px-8 py-4 text-base font-bold sm:text-lg"
            >
              <Link to="/create">
                Criar o guia da minha família
                <ArrowRight className="ml-2.5 h-5 w-5 transition-transform group-hover:translate-x-1" />
              </Link>
            </Button>
          </motion.div>
        </section>
      </main>

      <SiteFooter />
    </div>
  </>
);

export default HomePage;
