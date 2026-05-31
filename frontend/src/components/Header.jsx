
import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Menu, X, Heart } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Airplane, Flower } from './DecorativeElements.jsx';

const Header = () => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const location = useLocation();
  
  const isActive = (path) => location.pathname === path;
  
  const navLinks = [
    { path: '/', label: 'Início' },
    { path: '/create', label: 'Criar Guia' }
  ];
  
  return (
    <header className="sticky top-0 z-50 bg-background/90 backdrop-blur-md border-b border-primary/10">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative">
        <div className="flex items-center justify-between h-20">
          
          {/* Logo with Decorative Element */}
          <Link to="/" className="flex items-center gap-3 group">
            <div className="relative w-12 h-12 bg-secondary/10 rounded-2xl flex items-center justify-center group-hover:scale-105 transition-transform duration-300">
              <Airplane className="w-8 h-8 text-secondary" />
              <Flower className="absolute -bottom-2 -right-2 w-6 h-6 text-primary scale-0 group-hover:scale-100 transition-transform duration-300" />
            </div>
            <span className="text-2xl font-serif font-bold text-foreground tracking-tight">
              Aventuras em <span className="text-primary">Família</span>
            </span>
          </Link>
          
          {/* Desktop Navigation */}
          <nav className="hidden md:flex items-center gap-2">
            {navLinks.map((link) => (
              <Link
                key={link.path}
                to={link.path}
                className={`px-5 py-2.5 rounded-full text-sm font-medium transition-all duration-200 ${
                  isActive(link.path)
                    ? 'bg-primary text-primary-foreground shadow-md'
                    : 'text-foreground/80 hover:bg-muted hover:text-foreground'
                }`}
              >
                {link.label}
              </Link>
            ))}
          </nav>
          
          {/* Mobile Menu Button */}
          <Button
            variant="ghost"
            size="icon"
            className="md:hidden rounded-full text-foreground/80 hover:bg-muted"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          >
            {mobileMenuOpen ? (
              <X className="w-6 h-6" />
            ) : (
              <Menu className="w-6 h-6" />
            )}
          </Button>
        </div>
        
        {/* Mobile Navigation */}
        {mobileMenuOpen && (
          <nav className="md:hidden py-4 absolute top-20 left-0 w-full bg-background border-b border-primary/10 shadow-lg px-4 space-y-2">
            {navLinks.map((link) => (
              <Link
                key={link.path}
                to={link.path}
                onClick={() => setMobileMenuOpen(false)}
                className={`block px-5 py-3 rounded-2xl text-base font-medium transition-all duration-200 ${
                  isActive(link.path)
                    ? 'bg-primary/10 text-primary'
                    : 'text-foreground/80 hover:bg-muted'
                }`}
              >
                {link.label}
              </Link>
            ))}
          </nav>
        )}
      </div>
    </header>
  );
};

export default Header;
