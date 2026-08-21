import React from 'react';
import { Link } from 'react-router-dom';
import { Airplane } from './DecorativeElements.jsx';

const CURRENT_YEAR = new Date().getFullYear();

const SiteFooter = () => (
  <footer className="travel-page storybook-paper mt-auto border-t border-secondary/15 py-10 transition-colors duration-200 sm:py-12">
    <div className="guide-shell">
      {/* O fecho da página: o adeus de quem despacha a família para a viagem. */}
      <p className="editorial-copy mb-8 text-center text-foreground/70">
        O guia vai na mochila. As memórias voltam com vocês.
      </p>
      <div className="grid items-center gap-7 text-center md:grid-cols-[1fr_auto_1fr] md:text-left">
        <Link
          to="/"
          aria-label="Guia de Memórias — página inicial"
          className="group mx-auto flex w-fit items-center gap-2.5 md:mx-0"
        >
          <span
            aria-hidden="true"
            className="flex h-10 w-10 items-center justify-center rounded-full bg-primary transition-transform duration-200 group-hover:-rotate-6"
          >
            <Airplane className="h-6 w-6 text-[hsl(var(--paper))]" />
          </span>
          <span className="flex flex-col leading-tight">
            <span className="font-display text-xl font-bold text-primary">Guia de Memórias</span>
            <span className="font-ui text-xs font-semibold text-muted-foreground">
              por Minerva Travel
            </span>
          </span>
        </Link>

        <nav aria-label="Informações legais" className="font-ui flex flex-wrap justify-center gap-x-7 gap-y-3 text-sm font-semibold">
          <Link className="text-muted-foreground transition-colors hover:text-foreground" to="/privacy">
            Privacidade
          </Link>
          <Link className="text-muted-foreground transition-colors hover:text-foreground" to="/terms">
            Termos de uso
          </Link>
          <Link className="text-muted-foreground transition-colors hover:text-foreground" to="/pricing">
            Preço
          </Link>
        </nav>

        <p className="font-ui text-sm font-medium text-muted-foreground md:text-right">
          © {CURRENT_YEAR} Minerva Travel
        </p>
      </div>
    </div>
  </footer>
);

export default SiteFooter;
