import React, { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { Menu, X } from 'lucide-react';
import { Airplane } from './DecorativeElements.jsx';
import { useAuth } from '@/contexts/AuthContext.jsx';
import ThemeToggle from '@/components/ThemeToggle.jsx';

const mobileMenuId = 'primary-mobile-navigation';

/**
 * A navbar do mockup: uma pílula de papel-creme flutuando sobre a areia, com
 * o avião num selo terracota, os links em Baloo e um único botão azul. Nada
 * de barra colada de borda a borda — o site inteiro é uma mesa de papel.
 */
const Header = () => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();
  const { isAuthenticated, user, logout } = useAuth();

  const isActive = (path) => location.pathname === path && !location.hash;

  const navLinks = [
    { path: '/', label: 'Início' },
    { path: '/#atividades', label: 'Atividades', hash: true },
    { path: '/pricing', label: 'Preço' },
  ];

  const handleLogout = () => {
    logout();
    navigate('/');
    setMobileMenuOpen(false);
  };

  const linkClass = (active) =>
    `relative px-3 py-2 text-[1.02rem] font-semibold leading-none transition-colors duration-200 lg:px-4 ${
      active
        ? 'text-primary after:absolute after:-bottom-1.5 after:left-3 after:right-3 after:h-[3px] after:rounded-full after:bg-[hsl(var(--star))]'
        : 'text-muted-foreground hover:text-secondary'
    }`;

  return (
    <header className="sticky top-3 z-50 px-3 sm:top-5">
      <div className="relative mx-auto w-fit max-w-full">
        <div className="nav-pill gap-1 py-2 pl-2.5 pr-2 sm:gap-2 sm:pl-3">
          {/* Logo */}
          <Link
            to="/"
            aria-label="Guia de Memórias — página inicial"
            className="group flex items-center gap-2.5 pr-1 sm:gap-3"
          >
            <span
              aria-hidden="true"
              className="flex h-10 w-10 items-center justify-center rounded-full bg-primary transition-transform duration-200 group-hover:-rotate-6 sm:h-11 sm:w-11"
            >
              <Airplane className="h-6 w-6 text-[hsl(var(--paper))] sm:h-7 sm:w-7" />
            </span>
            <span className="whitespace-nowrap text-xl font-display font-bold leading-none text-primary sm:text-[1.45rem]">
              Guia de Memórias
            </span>
          </Link>

          {/* Desktop navigation */}
          <nav aria-label="Navegação principal" className="hidden items-center md:flex">
            {navLinks.map((link) => (
              <Link
                key={link.path}
                to={link.path}
                aria-current={isActive(link.path) ? 'page' : undefined}
                className={linkClass(isActive(link.path))}
              >
                {link.label}
              </Link>
            ))}

            {isAuthenticated ? (
              <>
                <Link
                  to="/dashboard"
                  aria-current={isActive('/dashboard') ? 'page' : undefined}
                  className={linkClass(isActive('/dashboard'))}
                >
                  {user?.name?.split(' ')[0] || 'Meu painel'}
                </Link>
                <button
                  type="button"
                  onClick={handleLogout}
                  className="px-3 py-2 text-[1.02rem] font-semibold leading-none text-muted-foreground transition-colors hover:text-destructive lg:px-4"
                >
                  Sair
                </button>
              </>
            ) : (
              <Link
                to="/login"
                aria-current={isActive('/login') ? 'page' : undefined}
                className={linkClass(isActive('/login'))}
              >
                Entrar
              </Link>
            )}

            <ThemeToggle />

            <Link
              to="/create"
              className="ml-1.5 whitespace-nowrap rounded-full bg-cobalt px-6 py-3 text-[1.02rem] font-bold leading-none text-cobalt-foreground shadow-[0_8px_18px_-10px_hsl(217_56%_30%/0.6)] transition-all duration-200 hover:-translate-y-0.5 hover:bg-cobalt/90"
            >
              Criar meu guia
            </Link>
          </nav>

          {/* Mobile controls */}
          <div className="ml-auto flex items-center gap-1 md:hidden">
            <ThemeToggle />
            <button
              type="button"
              className="flex h-10 w-10 items-center justify-center rounded-full text-foreground/80 transition-colors hover:bg-muted"
              onClick={() => setMobileMenuOpen((isOpen) => !isOpen)}
              aria-label={mobileMenuOpen ? 'Fechar menu principal' : 'Abrir menu principal'}
              aria-expanded={mobileMenuOpen}
              aria-controls={mobileMenuId}
            >
              {mobileMenuOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
            </button>
          </div>
        </div>

        {/* Mobile navigation: um cartão de papel que desce da pílula. */}
        {mobileMenuOpen && (
          <nav
            id={mobileMenuId}
            aria-label="Navegação principal móvel"
            className="absolute left-1/2 top-[calc(100%+0.6rem)] w-[min(92vw,22rem)] -translate-x-1/2 space-y-4 rounded-3xl bg-[hsl(var(--paper))] p-5 shadow-[0_18px_44px_-18px_hsl(30_27%_13%/0.4)] md:hidden dark:bg-card"
          >
            <div className="space-y-1">
              {navLinks.map((link) => (
                <Link
                  key={link.path}
                  to={link.path}
                  onClick={() => setMobileMenuOpen(false)}
                  aria-current={isActive(link.path) ? 'page' : undefined}
                  className={`block rounded-xl px-4 py-3 text-base font-semibold transition-colors duration-200 ${
                    isActive(link.path)
                      ? 'bg-[hsl(var(--blush))] text-primary'
                      : 'text-foreground/80 hover:bg-muted'
                  }`}
                >
                  {link.label}
                </Link>
              ))}
            </div>

            <div className="w-full border-t border-secondary/15"></div>

            {isAuthenticated ? (
              <div className="space-y-1">
                <Link
                  to="/dashboard"
                  onClick={() => setMobileMenuOpen(false)}
                  aria-current={isActive('/dashboard') ? 'page' : undefined}
                  className="block rounded-xl bg-[hsl(var(--mint))] px-4 py-3 text-base font-semibold text-secondary"
                >
                  Meu painel
                </Link>
                <button
                  type="button"
                  onClick={handleLogout}
                  className="w-full rounded-xl px-4 py-3 text-left text-base font-semibold text-destructive transition-colors hover:bg-destructive/10"
                >
                  Sair da conta
                </button>
              </div>
            ) : (
              <Link
                to="/login"
                onClick={() => setMobileMenuOpen(false)}
                aria-current={isActive('/login') ? 'page' : undefined}
                className="block rounded-xl px-4 py-3 text-center text-base font-semibold text-foreground/80 transition-colors hover:bg-muted"
              >
                Entrar
              </Link>
            )}

            <Link
              to="/create"
              onClick={() => setMobileMenuOpen(false)}
              className="block rounded-full bg-cobalt px-5 py-3.5 text-center text-base font-bold text-cobalt-foreground shadow-[0_8px_18px_-10px_hsl(217_56%_30%/0.6)]"
            >
              Criar meu guia
            </Link>
          </nav>
        )}
      </div>
    </header>
  );
};

export default Header;
