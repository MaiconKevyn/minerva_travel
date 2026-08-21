import React from 'react';

/**
 * O vocabulário tipográfico do guia, trazido para o site.
 *
 * O livro tem uma gramática própria — sobrelinha em caixa alta espaçada,
 * título em Zilla Slab e uma linha curta correndo em arco — desenhada pelo
 * compositor de páginas no backend. O site usava rótulos retos de landing
 * page; estes componentes fazem as seções falarem a língua das folhas.
 */

// A curvatura vem do livro: raio ~625 sobre um vão de 440 dá o mesmo gesto
// que o compositor desenha (raio 430 sobre ~1024 de folha). A primeira
// versão usava raio ~944 e o arco sumia — parecia texto torto, não arco.
const ARC_WIDTH = 480;
const ARC_HEIGHT = 80;
const ARC_CHORD = 440;
const ARC_RISE = 40;
const ARC_RADIUS = Math.round((ARC_RISE ** 2 + (ARC_CHORD / 2) ** 2) / (2 * ARC_RISE));
const ARC_FONT_MAX = 19;
// SVG não desenha glifo além do fim do caminho: um texto comprido era CORTADO
// nas duas pontas, em silêncio. O corpo encolhe até o texto caber no arco.
function arcFontSize(text) {
  const budget = ARC_CHORD / (text.length * 1.3);
  return Math.min(ARC_FONT_MAX, Math.max(11, budget));
}

/**
 * Uma linha curta de caixa alta correndo em arco, como "PARIS, FRANÇA" sob o
 * título de uma página. `direction="up"` é o arco da capa (ápice para cima,
 * como "GUIA DE MEMÓRIAS"); `direction="down"` é o sorriso sob o título.
 *
 * O texto precisa ser CURTO (até ~24 caracteres): o SVG não desenha glifos
 * além do fim do caminho, então uma frase comprida seria cortada em silêncio.
 */
export function ArchedText({ children, direction = 'down', className = '' }) {
  const inset = (ARC_WIDTH - ARC_CHORD) / 2;
  const path =
    direction === 'up'
      ? `M ${inset} 66 A ${ARC_RADIUS} ${ARC_RADIUS} 0 0 1 ${ARC_WIDTH - inset} 66`
      : `M ${inset} 24 A ${ARC_RADIUS} ${ARC_RADIUS} 0 0 0 ${ARC_WIDTH - inset} 24`;
  const pathId = React.useId();
  const fontSize = arcFontSize(children);

  return (
    <svg
      viewBox={`0 0 ${ARC_WIDTH} ${ARC_HEIGHT}`}
      className={`mx-auto block w-full max-w-[480px] ${className}`}
      role="img"
      aria-label={children}
    >
      <defs>
        <path id={pathId} d={path} fill="none" />
      </defs>
      <text
        className="font-serif"
        fill="currentColor"
        fontSize={fontSize}
        fontWeight="600"
        letterSpacing="0.22em"
      >
        <textPath href={`#${pathId}`} startOffset="50%" textAnchor="middle">
          {children.toUpperCase()}
        </textPath>
      </text>
    </svg>
  );
}

/**
 * A estrelinha mostarda que marca as notas de leitura nas páginas ilustradas.
 * Mesma proporção do compositor: raio interno a 42% do externo.
 */
export function GuideStar({ className = 'h-5 w-5' }) {
  const points = [];
  for (let i = 0; i < 10; i += 1) {
    const radius = i % 2 === 0 ? 10 : 4.2;
    const angle = -Math.PI / 2 + (i * Math.PI) / 5;
    points.push(`${12 + radius * Math.cos(angle)},${12 + radius * Math.sin(angle)}`);
  }
  return (
    <svg viewBox="0 0 24 24" className={`shrink-0 ${className}`} aria-hidden="true">
      <polygon points={points.join(' ')} fill="hsl(var(--star))" />
    </svg>
  );
}

/**
 * O cabeçalho de seção no brasão do guia: sobrelinha reta em caixa alta
 * espaçada, título em Zilla Slab e, quando faz sentido, a linha em arco.
 */
export function GuideLockup({ overline, title, arched, id, className = '' }) {
  return (
    <div className={`mx-auto max-w-2xl text-center ${className}`}>
      {overline ? (
        <div className="flex justify-center">
          <p className="travel-label rotate-[-0.7deg]">{overline}</p>
        </div>
      ) : null}
      <h2 id={id} className="mt-4 text-3xl font-serif font-bold leading-[1.05] tracking-[-0.025em] text-secondary sm:text-5xl">
        {title}
      </h2>
      {arched ? (
        <div className="mt-2 text-primary">
          <ArchedText direction="down">{arched}</ArchedText>
        </div>
      ) : null}
    </div>
  );
}
