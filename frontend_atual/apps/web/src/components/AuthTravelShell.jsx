import React from 'react';
import Header from '@/components/Header.jsx';
import {
  Airplane,
  CompassRose,
  LeafSprig,
  RouteDoodle,
} from '@/components/DecorativeElements.jsx';

const AuthTravelShell = ({ children, eyebrow, title, description, note }) => (
  <div className="min-h-screen bg-background flex flex-col transition-colors duration-200">
    <Header />

    <main
      id="main-content"
      tabIndex={-1}
      className="travel-page storybook-sky storybook-grid relative flex flex-1 items-center overflow-hidden px-4 py-10 sm:px-6 lg:py-16"
    >
      <CompassRose className="page-corner -right-5 top-10 rotate-12" />
      <LeafSprig className="page-corner -bottom-10 -left-7 -rotate-12 text-secondary" />

      <div className="guide-shell relative z-10 grid items-center gap-10 lg:grid-cols-[0.92fr_1.08fr] lg:gap-16">
        <section className="clean-surface relative mx-auto hidden w-full max-w-md overflow-hidden bg-[hsl(var(--mint)/0.55)] p-8 lg:block" aria-label="Apresentação do Guia de Memórias">
          <RouteDoodle className="absolute -right-10 top-3 z-20 h-20 w-40 rotate-6 text-secondary/30" />
          <Airplane className="absolute left-7 top-[43%] z-20 h-12 w-12 -rotate-12 text-primary/55" />

          <div className="page-frame mx-auto w-[62%] -rotate-3">
            <img
              src="/activity-examples/cover-sample.webp"
              alt="Capa ilustrada de um Guia de Memórias personalizado"
              width="1024"
              height="1536"
              className="aspect-[2/3] w-full object-cover"
            />
          </div>

          <div className="mt-7 border-t border-secondary/15 pt-5">
            <p className="font-hand text-center text-lg leading-snug text-secondary">{note}</p>
          </div>
        </section>

        <section className="mx-auto w-full max-w-xl">
          <div className="mb-6 text-center lg:text-left">
            <span className="travel-label -rotate-1">{eyebrow}</span>
            <h1 className="mt-4 text-4xl font-bold leading-none tracking-[-0.025em] text-secondary sm:text-5xl">
              {title}
            </h1>
            <p className="editorial-copy mt-3 text-foreground/70">{description}</p>
          </div>

          <div className="clean-surface relative px-6 py-7 sm:px-9 sm:py-9">
            {children}
          </div>
        </section>
      </div>
    </main>
  </div>
);

export default AuthTravelShell;
