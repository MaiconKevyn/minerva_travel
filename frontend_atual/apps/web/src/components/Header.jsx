
import React, { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { Menu, X, User } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Airplane, RouteDoodle } from './DecorativeElements.jsx';
import { useAuth } from '@/contexts/AuthContext.jsx';
import ThemeToggle from '@/components/ThemeToggle.jsx';

const mobileMenuId = 'primary-mobile-navigation';

const Header = () => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();
  const { isAuthenticated, user, logout } = useAuth();

  const isActive = (path) => location.pathname === path;

  const navLinks = [
    { path: '/', label: 'Início' },
    { path: '/pricing', label: 'Preço' },
    { path: '/create', label: 'Criar Guia' }
  ];

  const handleLogout = () => {
    logout();
    navigate('/');
    setMobileMenuOpen(false);
  };

  return (
    <header className="travel-page storybook-paper sticky top-0 z-50 border-b border-foreground/10 bg-background/95 shadow-[0_8px_28px_-26px_hsl(var(--foreground))] backdrop-blur-md">
      <div className="guide-shell relative">
        <div className="flex h-[4.5rem] items-center justify-between sm:h-[5.35rem]">

          {/* Logo with Decorative Element */}
          <Link
            to="/"
            aria-label="Minerva Travel — página inicial"
            className="group flex items-center gap-3"
          >
            <div
              aria-hidden="true"
              className="relative flex h-11 w-11 rotate-[-2deg] items-center justify-center rounded-[0.8rem_1.2rem_0.9rem_1.35rem] border-2 border-secondary/25 bg-[hsl(var(--mint))] shadow-[0_3px_0_hsl(var(--secondary)/0.16)] transition-transform duration-300 group-hover:-rotate-6 sm:h-12 sm:w-12"
            >
              <Airplane className="h-8 w-8 text-secondary" />
            </div>
            <span className="flex flex-col leading-none">
              <span className="text-lg font-serif font-bold tracking-[-0.02em] text-secondary sm:text-[1.35rem]">
                Guia de Memórias
              </span>
              <span className="font-ui mt-1 text-[0.58rem] font-bold uppercase tracking-[0.2em] text-primary sm:text-[0.62rem]">
                por Minerva Travel
              </span>
            </span>
          </Link>

          <RouteDoodle className="pointer-events-none absolute left-[15.5rem] top-2 hidden h-12 w-28 text-secondary/20 xl:block" />

          {/* Desktop Navigation */}
          <nav aria-label="Navegação principal" className="font-ui hidden items-center gap-3 md:flex">
            <div className="flex items-center gap-1">
              {navLinks.map((link) => (
                <Link
                  key={link.path}
                  to={link.path}
                  aria-current={isActive(link.path) ? 'page' : undefined}
                  className={`relative px-4 py-2 text-sm font-bold transition-colors duration-200 lg:px-5 ${
                    isActive(link.path)
                      ? 'text-primary after:absolute after:bottom-0 after:left-3 after:right-3 after:h-[3px] after:-rotate-1 after:rounded-full after:bg-[hsl(var(--star))]'
                      : 'text-foreground/75 hover:text-secondary'
                  }`}
                >
                  {link.label}
                </Link>
              ))}
            </div>

            <div className="mx-1 h-8 border-l-2 border-dotted border-secondary/25 lg:mx-2"></div>

            <ThemeToggle />

            {isAuthenticated ? (
              <div className="ml-1 flex items-center gap-2 lg:gap-3">
                <Link
                  to="/dashboard"
                  aria-current={isActive('/dashboard') ? 'page' : undefined}
                  className="flex items-center gap-2 text-sm font-bold text-secondary transition-colors hover:text-primary"
                >
                  <div className="flex h-8 w-8 items-center justify-center rounded-full border border-secondary/20 bg-accent/20 text-accent-foreground">
                    <User className="w-4 h-4" />
                  </div>
                  {user?.name || user?.email?.split('@')[0]}
                </Link>
                <Button variant="ghost" onClick={handleLogout} className="rounded-full font-bold hover:bg-destructive/10 hover:text-destructive">
                  Sair
                </Button>
              </div>
            ) : (
              <div className="ml-1 flex items-center gap-2">
                <Button variant="ghost" asChild className="rounded-full font-bold">
                  <Link to="/login">Entrar</Link>
                </Button>
                <Button asChild className="travel-cta px-5 font-bold">
                  <Link to="/signup">Criar Conta</Link>
                </Button>
              </div>
            )}
          </nav>

          {/* Mobile Menu Button */}
          <div className="flex items-center gap-1 md:hidden">
            <ThemeToggle />
            <Button
              variant="ghost"
              size="icon"
              className="rounded-full text-foreground/80 hover:bg-muted"
              onClick={() => setMobileMenuOpen((isOpen) => !isOpen)}
              aria-label={mobileMenuOpen ? 'Fechar menu principal' : 'Abrir menu principal'}
              aria-expanded={mobileMenuOpen}
              aria-controls={mobileMenuId}
            >
              {mobileMenuOpen ? (
                <X className="w-6 h-6" />
              ) : (
                <Menu className="w-6 h-6" />
              )}
            </Button>
          </div>
        </div>

        {/* Mobile Navigation */}
        {mobileMenuOpen && (
          <nav
            id={mobileMenuId}
            aria-label="Navegação principal móvel"
            className="travel-page storybook-paper absolute left-0 top-[4.5rem] w-full space-y-4 border-b border-foreground/10 bg-background px-4 py-5 pb-7 shadow-xl sm:top-[5.35rem] md:hidden"
          >
            <div className="space-y-2">
              {navLinks.map((link) => (
                <Link
                  key={link.path}
                  to={link.path}
                  onClick={() => setMobileMenuOpen(false)}
                  aria-current={isActive(link.path) ? 'page' : undefined}
                  className={`font-ui block rounded-xl px-5 py-3 text-base font-bold transition-all duration-200 ${
                    isActive(link.path)
                      ? 'bg-primary/10 text-primary'
                      : 'text-foreground/80 hover:bg-muted'
                  }`}
                >
                  {link.label}
                </Link>
              ))}
            </div>

            <div className="w-full border-t-2 border-dotted border-secondary/20"></div>

            {isAuthenticated ? (
              <div className="space-y-2">
                <Link
                  to="/dashboard"
                  onClick={() => setMobileMenuOpen(false)}
                  aria-current={isActive('/dashboard') ? 'page' : undefined}
                  className="font-ui block rounded-xl bg-accent/10 px-5 py-3 text-base font-bold text-accent-foreground"
                >
                  Meu Painel
                </Link>
                <button
                  type="button"
                  onClick={handleLogout}
                  className="font-ui w-full rounded-xl px-5 py-3 text-left text-base font-bold text-destructive transition-colors hover:bg-destructive/10"
                >
                  Sair da Conta
                </button>
              </div>
            ) : (
              <div className="flex flex-col gap-2">
                <Link
                  to="/login"
                  onClick={() => setMobileMenuOpen(false)}
                  aria-current={isActive('/login') ? 'page' : undefined}
                  className="font-ui block rounded-xl border-2 border-secondary/20 px-5 py-3 text-center text-base font-bold"
                >
                  Entrar
                </Link>
                <Link
                  to="/signup"
                  onClick={() => setMobileMenuOpen(false)}
                  aria-current={isActive('/signup') ? 'page' : undefined}
                  className="travel-cta font-ui block px-5 py-3 text-center text-base font-bold"
                >
                  Criar Conta
                </Link>
              </div>
            )}
          </nav>
        )}
      </div>
    </header>
  );
};

export default Header;
