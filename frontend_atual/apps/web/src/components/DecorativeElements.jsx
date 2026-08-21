import React from 'react';

/**
 * Pequenos motivos desenhados como giz e lápis.
 *
 * Eles são deliberadamente imperfeitos: o produto não usa pictogramas
 * geométricos como decoração. Ícones funcionais continuam vindo do Lucide;
 * estes SVGs aparecem apenas como matéria editorial do caderno.
 */

export const Flower = ({ className = 'h-12 w-12 text-primary', style }) => (
  <svg viewBox="0 0 100 100" className={className} style={style} aria-hidden="true">
    <g fill="currentColor" opacity="0.92">
      <ellipse cx="50" cy="25" rx="15" ry="23" transform="rotate(-4 50 25)" />
      <ellipse cx="72" cy="47" rx="15" ry="23" transform="rotate(78 72 47)" />
      <ellipse cx="50" cy="72" rx="15" ry="23" transform="rotate(5 50 72)" />
      <ellipse cx="27" cy="49" rx="15" ry="23" transform="rotate(-77 27 49)" />
      <circle cx="50" cy="49" r="12" fill="hsl(var(--paper))" />
    </g>
    <path d="M39 19c9-8 22-6 29 2M22 49c-2 10 5 20 15 24" fill="none" stroke="hsl(var(--paper))" strokeLinecap="round" strokeWidth="2" opacity="0.35" />
  </svg>
);

export const Airplane = ({ className = 'h-12 w-12 text-secondary', style }) => (
  <svg viewBox="0 0 100 100" className={className} style={style} aria-hidden="true">
    <path
      d="M87 23c-3-4-8-4-12-1L48 43 23 35l-8 8 20 14-10 9-13-1-6 7 19 8 18-13 14 17 9-5-8-27 29-20c4-3 4-6 0-9Z"
      fill="currentColor"
    />
    <path d="m49 44 9 8 29-20" fill="none" stroke="hsl(var(--paper))" strokeLinecap="round" strokeWidth="3" opacity="0.4" />
  </svg>
);

export const Suitcase = ({ className = 'h-12 w-12 text-accent', style }) => (
  <svg viewBox="0 0 100 100" className={className} style={style} aria-hidden="true">
    <path d="M17 37c0-7 5-11 12-11h43c8 0 12 5 12 12v39c0 7-5 11-12 11H29c-8 0-12-5-12-12V37Z" fill="currentColor" />
    <path d="M37 27v-7c0-6 5-9 13-9s13 3 13 9v7" fill="none" stroke="currentColor" strokeLinecap="round" strokeWidth="7" />
    <path d="M32 34v47M69 34v47" fill="none" stroke="hsl(var(--paper))" strokeLinecap="round" strokeWidth="4" opacity="0.38" />
    <path d="m42 53 7 4 7-4v12l-7 4-7-4Z" fill="hsl(var(--star))" />
  </svg>
);

export const Sun = ({ className = 'h-12 w-12 text-[hsl(var(--star))]', style }) => (
  <svg viewBox="0 0 100 100" className={className} style={style} aria-hidden="true">
    <circle cx="50" cy="50" r="22" fill="currentColor" />
    <g stroke="currentColor" strokeLinecap="round" strokeWidth="7">
      <path d="M50 8v13M50 79v13M8 50h13M79 50h13" />
      <path d="m20 20 9 9m42 42 9 9M20 80l9-9m42-42 9-9" />
    </g>
  </svg>
);

export const LeafSprig = ({ className = 'h-24 w-24 text-accent', style }) => (
  <svg viewBox="0 0 160 160" className={className} style={style} aria-hidden="true">
    <path d="M25 140C54 101 85 66 137 27" fill="none" stroke="currentColor" strokeLinecap="round" strokeWidth="7" />
    <g fill="currentColor">
      <path d="M49 113C27 113 18 98 24 78c21 0 33 12 25 35Z" />
      <path d="M70 88C48 84 42 67 51 49c21 4 30 19 19 39Z" />
      <path d="M96 63C78 54 76 37 88 23c19 8 24 25 8 40Z" />
      <path d="M76 102c6-21 23-27 42-18-5 21-22 30-42 18Z" />
      <path d="M103 76c8-20 26-24 43-13-7 20-25 27-43 13Z" />
      <path d="M125 48c5-17 19-23 34-15-3 17-18 25-34 15Z" />
    </g>
  </svg>
);

export const CompassRose = ({ className = 'h-24 w-24 text-secondary', style }) => (
  <svg viewBox="0 0 160 160" className={className} style={style} aria-hidden="true">
    <circle cx="80" cy="80" r="58" fill="none" stroke="currentColor" strokeDasharray="3 8" strokeLinecap="round" strokeWidth="3" opacity="0.55" />
    <path d="m80 17 13 50 50 13-50 13-13 50-13-50-50-13 50-13Z" fill="currentColor" opacity="0.82" />
    <circle cx="80" cy="80" r="11" fill="hsl(var(--paper))" />
    <text x="80" y="13" fill="currentColor" fontFamily="Zilla Slab, serif" fontSize="15" fontWeight="700" textAnchor="middle">N</text>
  </svg>
);

export const RouteDoodle = ({ className = 'h-24 w-48 text-secondary', style }) => (
  <svg viewBox="0 0 240 110" className={className} style={style} aria-hidden="true">
    <path d="M12 86C49 15 76 101 118 55c23-25 34-45 63-38 18 4 29 20 47 14" fill="none" stroke="currentColor" strokeDasharray="1 13" strokeLinecap="round" strokeWidth="7" opacity="0.68" />
    <circle cx="12" cy="86" r="8" fill="hsl(var(--primary))" />
    <path d="m218 20 14 11-17 4" fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="5" />
  </svg>
);

export const MapPinDoodle = ({ className = 'h-16 w-16 text-primary', style }) => (
  <svg viewBox="0 0 100 100" className={className} style={style} aria-hidden="true">
    <path d="M50 91S22 63 22 39C22 21 34 10 51 10s28 12 28 29c0 24-29 52-29 52Z" fill="currentColor" />
    <circle cx="50" cy="39" r="12" fill="hsl(var(--paper))" />
  </svg>
);

export const PassportStamp = ({ className = 'h-24 w-24 text-primary', style }) => (
  <svg viewBox="0 0 140 140" className={className} style={style} aria-hidden="true">
    <circle cx="70" cy="70" r="56" fill="none" stroke="currentColor" strokeDasharray="4 5" strokeWidth="5" />
    <circle cx="70" cy="70" r="42" fill="none" stroke="currentColor" strokeWidth="2" opacity="0.65" />
    <path d="m39 76 18 12 42-43" fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="9" />
  </svg>
);
