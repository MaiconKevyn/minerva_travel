import React from 'react';
import { Helmet } from 'react-helmet';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ArrowRight, Heart } from 'lucide-react';
import { Button } from '@/components/ui/button';
import Header from '@/components/Header.jsx';
import HomeHero from '@/components/HomeHero.jsx';
import SampleGuideReader from '@/components/SampleGuideReader.jsx';
import BookAnatomy from '@/components/BookAnatomy.jsx';
import HowItWorks from '@/components/HowItWorks.jsx';
import ActivityShowcase from '@/components/ActivityShowcase.jsx';
import HomeFaq from '@/components/HomeFaq.jsx';

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
          className="parchment-wash border-t border-border/50 bg-card py-20 sm:py-24"
          aria-labelledby="comecar-title"
        >
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: '-80px' }}
            transition={{ duration: 0.5 }}
            className="mx-auto max-w-2xl px-4 text-center sm:px-6 lg:px-8"
          >
            <h2
              id="comecar-title"
              className="text-3xl font-serif font-bold text-foreground sm:text-4xl"
            >
              A viagem já está marcada. Falta o livro.
            </h2>
            <p className="mt-4 text-lg font-medium text-muted-foreground">
              Comece pelo roteiro que vocês já têm — em poucos minutos você vê a primeira página
              ilustrada na tela.
            </p>
            <Button
              asChild
              size="lg"
              className="group mt-8 rounded-full bg-primary px-8 py-6 text-base font-bold text-white shadow-[0_8px_30px_rgb(160,72,45,0.28)] transition-all duration-300 hover:-translate-y-0.5 hover:bg-primary/90 sm:text-lg"
            >
              <Link to="/create">
                Criar o guia da minha família
                <ArrowRight className="ml-2.5 h-5 w-5 transition-transform group-hover:translate-x-1" />
              </Link>
            </Button>
          </motion.div>
        </section>
      </main>

      <footer className="mt-auto border-t border-border bg-muted py-12 transition-colors duration-200">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col items-center justify-between gap-6 md:flex-row">
            <div className="flex items-center gap-2">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-card shadow-sm">
                <Heart className="h-5 w-5 text-primary" aria-hidden="true" />
              </div>
              <span className="font-serif text-xl font-bold text-foreground">Minerva Travel</span>
            </div>
            <div className="flex gap-8 text-sm font-medium">
              <Link className="text-muted-foreground transition-colors hover:text-foreground" to="/privacy">
                Política de Privacidade
              </Link>
              <Link className="text-muted-foreground transition-colors hover:text-foreground" to="/terms">
                Termos de Uso
              </Link>
            </div>
            <p className="text-sm font-medium text-muted-foreground">
              © 2026 Minerva Travel · Projeto em piloto
            </p>
          </div>
        </div>
      </footer>
    </div>
  </>
);

export default HomePage;
