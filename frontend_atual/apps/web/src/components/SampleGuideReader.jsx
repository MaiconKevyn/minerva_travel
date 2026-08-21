import { GuideLockup } from '@/components/GuideLockup.jsx';
import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  ArrowLeft,
  ArrowRight,
  BookOpen,
  ChevronDown,
  ChevronUp,
  Expand,
  MoveHorizontal,
  MousePointer2,
  Sparkles,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { useIsMobile } from '@/hooks/use-mobile.jsx';

const SAMPLE_PAGES = [
  ['Capa da Família Knopp', 'A capa personalizada com os destinos e o mês da viagem'],
  ['Nosso roteiro', 'A sequência ilustrada das paradas da família'],
  ['Descubra Paris', 'Uma apresentação da cidade e curiosidades para as crianças'],
  ['Torre Eiffel', 'O ponto turístico com curiosidade, missão e campo Já visitei'],
  ['Investigador da Torre Eiffel', 'Uma missão diferente para cada criança durante o passeio'],
  ['Caça aos detalhes da Torre Eiffel', 'Uma lista de descobertas para observar no local'],
  ['Torre Eiffel para colorir', 'O monumento em traço limpo, pronto para ganhar novas cores'],
  ['Cartão-postal da Torre Eiffel', 'Espaço para registrar e enviar uma lembrança da viagem'],
  ['Passaporte de Paris', 'Lugar para guardar ingressos, carimbos e o que mais encantou'],
  ['Diário da Torre Eiffel', 'Perguntas e linhas para escrever sobre o dia'],
  ['Museu do Louvre', 'Curiosidades, missão e o campo Já visitei'],
  ['Investigador do Museu do Louvre', 'Pistas personalizadas para explorar o museu'],
  ['Caça aos detalhes do Museu do Louvre', 'Um convite para olhar a arquitetura com atenção'],
  ['Museu do Louvre para colorir', 'O museu e sua pirâmide em uma página para pintar'],
  ['Cartão-postal do Museu do Louvre', 'Uma lembrança que a criança escreve durante a viagem'],
  ['Passaporte de Paris', 'Mais espaço para colar bilhetes e registrar descobertas'],
  ['Diário do Museu do Louvre', 'Memórias e palavras novas aprendidas no passeio'],
  ['Minha melhor memória', 'A página obrigatória para desenhar, escrever e assinar'],
  ['Hora de voltar para casa', 'O encerramento da aventura e uma lembrança para contar'],
].map(([title, description], index) => ({
  number: index + 1,
  title,
  description,
  image: `/sample-guide/page-${String(index + 1).padStart(2, '0')}.webp`,
}));

const LAST_PAGE_INDEX = SAMPLE_PAGES.length - 1;
const FEATURED_PAGE_INDEXES = [0, 1, 10, 13, 17];

const spreadStartForPage = (pageIndex) => {
  if (pageIndex <= 0) return 0;
  return pageIndex % 2 === 0 ? pageIndex - 1 : pageIndex;
};

const visiblePageIndexes = (activePage, isMobile) => {
  if (isMobile) return [activePage];
  if (activePage === 0) return [null, 0];
  const start = spreadStartForPage(activePage);
  return [start, start + 1 <= LAST_PAGE_INDEX ? start + 1 : null];
};

const pageRangeLabel = (indexes) => {
  const pageNumbers = indexes.filter((index) => index !== null).map((index) => index + 1);
  if (pageNumbers.length === 1 && pageNumbers[0] === 1) return 'Capa · página 1 de 19';
  if (pageNumbers.length === 1) return `Página ${pageNumbers[0]} de 19`;
  return `Páginas ${pageNumbers[0]} e ${pageNumbers[1]} de 19`;
};

// O Tailwind so emite as regras de `@layer components` cujas classes ele
// encontra ESCRITAS POR INTEIRO no codigo. Montar o nome com template
// (`--${side}`) fazia o scanner nao achar nada, e as regras sumiam do CSS
// compilado: a folha ficava sem `left` e sem `transform-origin`, girava pelo
// proprio centro e por cima da metade errada do livro. Por isso os nomes
// completos moram aqui.
const PAGE_SIDE_CLASS = {
  left: 'sample-guide-page--left',
  right: 'sample-guide-page--right',
};

const LEAF_SIDE_CLASS = {
  left: 'sample-guide-leaf--left',
  right: 'sample-guide-leaf--right',
};

const BookPage = ({ pageIndex, side, canTurn, onTurn, priority = false }) => {
  if (pageIndex === null) {
    return (
      <div className="sample-guide-page sample-guide-page--blank" aria-hidden="true">
        <BookOpen className="h-10 w-10" />
        <p>Abra o livro e comece a aventura.</p>
      </div>
    );
  }

  const page = SAMPLE_PAGES[pageIndex];
  const image = (
    <img
      src={page.image}
      alt={`Página ${page.number} do guia de exemplo: ${page.title}. ${page.description}.`}
      width="720"
      height="1080"
      loading={priority ? 'eager' : 'lazy'}
      draggable="false"
      className="h-full w-full object-contain"
    />
  );

  if (!canTurn) {
    return <div className={`sample-guide-page ${PAGE_SIDE_CLASS[side]}`}>{image}</div>;
  }

  return (
    <button
      type="button"
      onClick={onTurn}
      className={`sample-guide-page ${PAGE_SIDE_CLASS[side]} sample-guide-page--turnable`}
      aria-label={side === 'left' ? 'Folhear para as páginas anteriores' : 'Folhear para as próximas páginas'}
    >
      {image}
    </button>
  );
};

const BookViewport = ({
  activePage,
  turn,
  isMobile,
  onNext,
  onPrevious,
  onTurnEnd,
  expanded = false,
}) => {
  const touchStartX = useRef(null);
  const swiped = useRef(false);
  // A folha continua existindo para quem pediu menos movimento — sem ela o
  // spread ficaria meio origem, meio destino durante a troca. Ela so assenta
  // na hora, em vez de girar.
  const turnSeconds = useMemo(
    () =>
      typeof window !== 'undefined'
        && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
        ? 0
        : 0.72,
    [],
  );

  // Durante a virada, a metade que a folha ainda nao cobriu continua mostrando
  // a pagina de ORIGEM, e a metade que ela acabou de liberar ja mostra o
  // DESTINO. E o que faz a folha parecer descolar de uma pilha em vez de
  // trocar o livro inteiro.
  const { baseIndexes, leaf } = useMemo(() => {
    if (!turn) {
      return { baseIndexes: visiblePageIndexes(activePage, isMobile), leaf: null };
    }
    const from = visiblePageIndexes(turn.from, isMobile);
    const to = visiblePageIndexes(turn.to, isMobile);
    if (isMobile) {
      return {
        baseIndexes: to,
        leaf: { side: turn.direction > 0 ? 'right' : 'left', front: from[0], back: to[0] },
      };
    }
    return turn.direction > 0
      ? {
          baseIndexes: [from[0], to[1]],
          leaf: { side: 'right', front: from[1], back: to[0] },
        }
      : {
          baseIndexes: [to[0], from[1]],
          leaf: { side: 'left', front: from[0], back: to[1] },
        };
  }, [activePage, isMobile, turn]);

  const handleTouchStart = (event) => {
    touchStartX.current = event.changedTouches[0]?.clientX ?? null;
    swiped.current = false;
  };

  const handleTouchEnd = (event) => {
    if (touchStartX.current === null) return;
    const endX = event.changedTouches[0]?.clientX ?? touchStartX.current;
    const distance = endX - touchStartX.current;
    touchStartX.current = null;
    if (Math.abs(distance) < 45) return;
    swiped.current = true;
    if (distance < 0) onNext();
    else onPrevious();
  };

  const handlePageTurn = (callback) => {
    if (swiped.current) {
      swiped.current = false;
      return;
    }
    callback();
  };

  return (
    <div
      className={`sample-guide-stage ${expanded ? 'sample-guide-stage--expanded' : ''}`}
      onTouchStart={handleTouchStart}
      onTouchEnd={handleTouchEnd}
    >
      <div className={isMobile ? 'sample-guide-book sample-guide-book--single' : 'sample-guide-book'}>
        <div className={isMobile ? 'sample-guide-single' : 'sample-guide-spread'}>
          {baseIndexes.map((pageIndex, position) => {
            const side = isMobile ? 'right' : position === 0 ? 'left' : 'right';
            const canTurn = turn
              ? false
              : side === 'left'
                ? activePage > 0
                : pageIndex !== null && pageIndex < LAST_PAGE_INDEX;
            const goTo = side === 'left' ? onPrevious : onNext;
            return (
              <BookPage
                key={`${side}-${pageIndex ?? 'blank'}`}
                pageIndex={pageIndex}
                side={side}
                canTurn={canTurn}
                onTurn={() => handlePageTurn(goTo)}
                priority={pageIndex === 0}
              />
            );
          })}
        </div>

        {leaf ? (
          <motion.div
            className={`sample-guide-leaf ${LEAF_SIDE_CLASS[leaf.side]}`}
            // O `z` nao e enfeite. Num contexto preserve-3d o z-index NAO
            // ordena: quem ordena e a posicao em Z. Folha e base estavam ambas
            // em Z=0, coplanares, e o navegador pintava metade da folha atras
            // da pagina de baixo — era a metade que "sumia" ao girar.
            initial={{ rotateY: 0, z: 2 }}
            animate={{ rotateY: leaf.side === 'right' ? -180 : 180, z: 2 }}
            // Papel tem peso: sai devagar, ganha velocidade e assenta sem
            // repique. Duracao alta o bastante para o olho ler o giro.
            transition={{ duration: turnSeconds, ease: [0.36, 0, 0.16, 1] }}
            onAnimationComplete={onTurnEnd}
          >
            <div className="sample-guide-leaf-face sample-guide-leaf-face--front">
              <BookPage pageIndex={leaf.front} side={leaf.side} canTurn={false} onTurn={() => {}} />
            </div>
            <div className="sample-guide-leaf-face sample-guide-leaf-face--back">
              <BookPage
                pageIndex={leaf.back}
                side={leaf.side === 'right' ? 'left' : 'right'}
                canTurn={false}
                onTurn={() => {}}
              />
            </div>
            {/* A sombra some nas pontas e enche no meio do giro: e ela que da
                a impressao de volume, porque a folha em si e plana. */}
            <motion.div
              className="sample-guide-leaf-shade"
              aria-hidden="true"
              initial={{ opacity: 0 }}
              animate={{ opacity: [0, 0.38, 0] }}
              transition={{ duration: turnSeconds, times: [0, 0.5, 1], ease: 'easeInOut' }}
            />
          </motion.div>
        ) : null}
      </div>
    </div>
  );
};

const SampleGuideReader = () => {
  const isMobile = useIsMobile();
  const [activePage, setActivePage] = useState(0);
  const [readerOpen, setReaderOpen] = useState(false);
  // A pagina so muda quando a folha termina de girar. Trocar antes era o que
  // fazia o livro piscar no meio da virada.
  const [turn, setTurn] = useState(null);
  const visibleIndexes = useMemo(
    () => visiblePageIndexes(activePage, isMobile),
    [activePage, isMobile],
  );
  const lastVisiblePage = Math.max(...visibleIndexes.filter((index) => index !== null));
  const canGoNext = lastVisiblePage < LAST_PAGE_INDEX;

  const goToPage = (pageIndex) => {
    if (turn) return;
    const bounded = Math.min(LAST_PAGE_INDEX, Math.max(0, pageIndex));
    const nextPage = isMobile ? bounded : spreadStartForPage(bounded);
    if (nextPage === activePage) return;
    setTurn({ from: activePage, to: nextPage, direction: nextPage > activePage ? 1 : -1 });
  };

  const finishTurn = () => {
    setTurn((current) => {
      if (current) setActivePage(current.to);
      return null;
    });
  };

  const goNext = () => {
    if (!canGoNext) return;
    goToPage(isMobile ? activePage + 1 : activePage === 0 ? 1 : activePage + 2);
  };

  const goPrevious = () => {
    if (activePage <= 0) return;
    goToPage(isMobile ? activePage - 1 : activePage <= 1 ? 0 : activePage - 2);
  };

  useEffect(() => {
    if (!readerOpen) return;
    const nextIndexes = isMobile
      ? [activePage + 1]
      : visiblePageIndexes(activePage === 0 ? 1 : activePage + 2, false);
    nextIndexes
      .filter((index) => index !== null && index <= LAST_PAGE_INDEX)
      .forEach((index) => {
        const image = new Image();
        image.src = SAMPLE_PAGES[index].image;
      });
  }, [activePage, isMobile, readerOpen]);

  const openReaderAt = (pageIndex) => {
    setTurn(null);
    setActivePage(isMobile ? pageIndex : spreadStartForPage(pageIndex));
    setReaderOpen(true);
  };

  const handleKeyboard = (event) => {
    if (event.key === 'ArrowRight') {
      event.preventDefault();
      goNext();
    }
    if (event.key === 'ArrowLeft') {
      event.preventDefault();
      goPrevious();
    }
    if (event.key === 'Home') {
      event.preventDefault();
      goToPage(0);
    }
    if (event.key === 'End') {
      event.preventDefault();
      goToPage(LAST_PAGE_INDEX);
    }
  };

  const controls = (
    <div className="flex flex-wrap items-center justify-center gap-3">
      <Button
        type="button"
        variant="outline"
        onClick={goPrevious}
        disabled={activePage === 0}
        className="rounded-full border-2 px-5"
      >
        <ArrowLeft className="mr-2 h-4 w-4" aria-hidden="true" />
        Anterior
      </Button>
      <p className="min-w-44 text-center text-sm font-bold text-foreground" role="status" aria-live="polite">
        {pageRangeLabel(visibleIndexes)}
      </p>
      <Button
        type="button"
        onClick={goNext}
        disabled={!canGoNext}
        className="rounded-full px-5"
      >
        Próxima
        <ArrowRight className="ml-2 h-4 w-4" aria-hidden="true" />
      </Button>
    </div>
  );

  return (
    <section
      id="guia-exemplo"
      className="travel-page storybook-paper scroll-mt-20 border-t border-secondary/10 py-20 sm:py-24"
      aria-labelledby="guia-exemplo-title"
    >
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <motion.div
          initial={{ opacity: 0, y: 18 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-70px' }}
          transition={{ duration: 0.5 }}
          className="mx-auto max-w-3xl text-center"
        >
          <GuideLockup
            id="guia-exemplo-title"
            overline="Um guia completo de verdade"
            title="Folheie a aventura antes de criar a sua"
            arched="Família Knopp em Paris"
          />
          <p className="editorial-copy mt-4 text-foreground/70">
            Veja cinco páginas-chave agora. O livro tem 19 páginas reais, da capa à volta para
            casa, e você pode abrir tudo quando quiser.
          </p>
        </motion.div>

        <div
          className="travel-card travel-card-blue mt-10 p-4 sm:p-6 lg:p-8"
          {...(readerOpen
            ? {
                tabIndex: 0,
                onKeyDown: handleKeyboard,
                'aria-label': 'Leitor do guia de exemplo. Use as setas esquerda e direita para folhear.',
              }
            : {})}
        >
          <div className={`flex items-center justify-between gap-3 ${readerOpen ? 'mb-5' : 'mb-6'}`}>
            <div className="flex items-center gap-3">
              <span className="flex h-10 w-10 -rotate-2 items-center justify-center rounded-[0.7rem_1rem_0.8rem_1.1rem] bg-primary/10 text-primary">
                <BookOpen className="h-5 w-5" aria-hidden="true" />
              </span>
              <div>
                <p className="font-serif text-lg font-bold text-foreground">Família Knopp em Paris</p>
                <p className="font-ui text-xs font-bold uppercase tracking-wider text-muted-foreground">Guia demonstrativo</p>
              </div>
            </div>

            {readerOpen ? (
              <Dialog>
                <DialogTrigger asChild>
                  <Button
                    type="button"
                    variant="outline"
                    className="font-ui min-h-11 rounded-full border-2 font-bold"
                    aria-label="Ampliar o guia"
                  >
                    <Expand className="h-4 w-4 sm:mr-2" aria-hidden="true" />
                    <span className="hidden sm:inline">Ampliar</span>
                  </Button>
                </DialogTrigger>
                <DialogContent className="h-[94vh] max-w-[min(96vw,1180px)] overflow-y-auto rounded-[1.75rem] border-2 p-4 sm:p-6">
                  <DialogHeader className="pr-10 text-left">
                    <DialogTitle className="font-serif text-2xl">Guia demonstrativo completo</DialogTitle>
                    <DialogDescription>{pageRangeLabel(visibleIndexes)}</DialogDescription>
                  </DialogHeader>
                  <BookViewport
                    activePage={activePage}
                    turn={turn}
                    isMobile={isMobile}
                    onNext={goNext}
                    onPrevious={goPrevious}
                    onTurnEnd={finishTurn}
                    expanded
                  />
                  {controls}
                </DialogContent>
              </Dialog>
            ) : null}
          </div>

          {!readerOpen ? (
            <>
              <div className="flex snap-x gap-3 overflow-x-auto pb-3 sm:grid sm:grid-cols-5 sm:overflow-visible" aria-label="Páginas em destaque do guia">
                {FEATURED_PAGE_INDEXES.map((pageIndex) => {
                  const page = SAMPLE_PAGES[pageIndex];
                  return (
                    <button
                      key={page.image}
                      type="button"
                      onClick={() => openReaderAt(pageIndex)}
                      className="group w-36 shrink-0 snap-start rounded-xl border-2 border-secondary/15 bg-background/65 p-2 text-left transition hover:-translate-y-1 hover:border-primary/45 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-ring/35 sm:w-auto"
                      aria-label={`Abrir o guia na página ${page.number}: ${page.title}`}
                    >
                      <img
                        src={page.image}
                        alt=""
                        width="180"
                        height="270"
                        loading="lazy"
                        decoding="async"
                        className="aspect-[2/3] w-full rounded-lg object-cover shadow-sm"
                      />
                      <span className="font-ui mt-2 block text-xs font-bold uppercase tracking-wide text-primary">
                        Página {page.number}
                      </span>
                      <span className="mt-1 block text-sm font-bold leading-tight text-foreground group-hover:text-secondary">
                        {page.title}
                      </span>
                    </button>
                  );
                })}
              </div>
              <Button
                type="button"
                variant="outline"
                onClick={() => openReaderAt(0)}
                aria-expanded="false"
                aria-controls="sample-guide-full-reader"
                className="font-ui mx-auto mt-5 flex min-h-11 rounded-full border-2 px-6 font-bold"
              >
                <BookOpen className="mr-2 h-4 w-4" aria-hidden="true" />
                Abrir as 19 páginas
                <ChevronDown className="ml-2 h-4 w-4" aria-hidden="true" />
              </Button>
            </>
          ) : (
            <div id="sample-guide-full-reader">
              <div className="font-ui mb-5 flex items-center justify-center gap-2 text-sm font-bold text-primary">
                {isMobile ? (
                  <MoveHorizontal className="h-4 w-4" aria-hidden="true" />
                ) : (
                  <MousePointer2 className="h-4 w-4" aria-hidden="true" />
                )}
                {isMobile
                  ? 'Deslize a página ou use os botões para folhear'
                  : 'Clique no canto da página ou use as setas'}
              </div>

              <BookViewport
                activePage={activePage}
                turn={turn}
                isMobile={isMobile}
                onNext={goNext}
                onPrevious={goPrevious}
                onTurnEnd={finishTurn}
              />

              <div className="mt-6">{controls}</div>

              <div className="sample-guide-thumbnails mt-6" aria-label="Escolha uma página do guia">
                {SAMPLE_PAGES.map((page) => {
                  const selected = visibleIndexes.includes(page.number - 1);
                  return (
                    <button
                      key={page.image}
                      type="button"
                      onClick={() => goToPage(page.number - 1)}
                      className="sample-guide-thumbnail"
                      aria-label={`Ir para a página ${page.number}: ${page.title}`}
                      aria-current={selected ? 'page' : undefined}
                      title={page.title}
                    >
                      <img
                        src={page.image}
                        alt=""
                        width="72"
                        height="108"
                        loading="lazy"
                        decoding="async"
                        className="h-full w-full object-cover"
                      />
                      <span>{page.number}</span>
                    </button>
                  );
                })}
              </div>

              <Button
                type="button"
                variant="ghost"
                onClick={() => setReaderOpen(false)}
                disabled={Boolean(turn)}
                aria-expanded="true"
                aria-controls="sample-guide-full-reader"
                className="font-ui mx-auto mt-6 flex min-h-11 rounded-full px-6 font-bold"
              >
                Recolher guia
                <ChevronUp className="ml-2 h-4 w-4" aria-hidden="true" />
              </Button>
            </div>
          )}
        </div>

        <div className="mt-9 flex flex-col items-center justify-center gap-4 text-center sm:flex-row">
          <p className="editorial-copy max-w-lg text-foreground/70">
            O roteiro, os lugares e as atividades mudam. O cuidado com cada página permanece.
          </p>
          <Button asChild size="lg" className="travel-cta group h-auto px-7 py-4 font-bold">
            <Link to="/create">
              <Sparkles className="mr-2 h-5 w-5" aria-hidden="true" />
              Criar o guia da minha família
              <ArrowRight className="ml-2 h-5 w-5 transition-transform group-hover:translate-x-1" aria-hidden="true" />
            </Link>
          </Button>
        </div>
      </div>
    </section>
  );
};

export default SampleGuideReader;
