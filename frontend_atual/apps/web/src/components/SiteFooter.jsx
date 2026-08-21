import React from 'react';
import { Link } from 'react-router-dom';
import { GuideStar } from '@/components/GuideLockup.jsx';

const CURRENT_YEAR = new Date().getFullYear();

const SiteFooter = () => (
  <footer className="travel-page storybook-paper mt-auto border-t border-secondary/15 py-10 transition-colors duration-200 sm:py-12">
    <div className="guide-shell">
      <div className="grid items-center gap-7 text-center md:grid-cols-[1fr_auto_1fr] md:text-left">
        <Link
          to="/"
          aria-label="Guia de Memórias — página inicial"
          className="mx-auto flex w-fit items-center gap-2.5 md:mx-0"
        >
          <GuideStar className="h-6 w-6" />
          <span className="flex flex-col leading-tight">
            <span className="font-serif text-xl font-bold text-secondary">Guia de Memórias</span>
            <span className="font-ui text-[0.62rem] font-bold uppercase tracking-[0.18em] text-primary">
              por Minerva Travel
            </span>
          </span>
        </Link>

        <nav aria-label="Informações legais" className="font-ui flex flex-wrap justify-center gap-x-7 gap-y-3 text-sm font-bold">
          <Link className="travel-paper-link text-muted-foreground transition-colors hover:text-foreground" to="/privacy">
            Privacidade
          </Link>
          <Link className="travel-paper-link text-muted-foreground transition-colors hover:text-foreground" to="/terms">
            Termos de uso
          </Link>
          <Link className="travel-paper-link text-muted-foreground transition-colors hover:text-foreground" to="/pricing">
            Preço
          </Link>
        </nav>

        <p className="font-ui text-sm font-medium text-muted-foreground md:text-right">
          © {CURRENT_YEAR} Minerva Travel · Projeto em piloto
        </p>
      </div>
    </div>
  </footer>
);

export default SiteFooter;
