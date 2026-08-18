import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { AnimatePresence, motion } from 'framer-motion';
import {
  ArrowLeft,
  ArrowRight,
  BookOpen,
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
      fetchPriority={priority ? 'high' : 'auto'}
      draggable="false"
      className="h-full w-full object-contain"
    />
  );

  if (!canTurn) {
    return <div className={`sample-guide-page sample-guide-page--${side}`}>{image}</div>;
  }

  return (
    <button
      type="button"
      onClick={onTurn}
      className={`sample-guide-page sample-guide-page--${side} sample-guide-page--turnable`}
      aria-label={side === 'left' ? 'Folhear para as páginas anteriores' : 'Folhear para as próximas páginas'}
    >
      {image}
    </button>
  );
};

const BookViewport = ({ activePage, direction, isMobile, onNext, onPrevious, expanded = false }) => {
  const indexes = useMemo(
    () => visiblePageIndexes(activePage, isMobile),
    [activePage, isMobile],
  );
  const touchStartX = useRef(null);
  const swiped = useRef(false);

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
      <AnimatePresence initial={false} mode="wait" custom={direction}>
        <motion.div
          key={`${isMobile ? 'page' : 'spread'}-${activePage}`}
          custom={direction}
          variants={{
            enter: (turnDirection) => ({
              opacity: 0,
              rotateY: turnDirection > 0 ? 12 : -12,
              x: turnDirection > 0 ? 28 : -28,
            }),
            center: { opacity: 1, rotateY: 0, x: 0 },
            exit: (turnDirection) => ({
              opacity: 0,
              rotateY: turnDirection > 0 ? -12 : 12,
              x: turnDirection > 0 ? -22 : 22,
            }),
          }}
          initial="enter"
          animate="center"
          exit="exit"
          transition={{ duration: 0.34, ease: [0.22, 1, 0.36, 1] }}
          className={isMobile ? 'sample-guide-single' : 'sample-guide-spread'}
        >
          {indexes.map((pageIndex, position) => {
            const side = isMobile ? 'right' : position === 0 ? 'left' : 'right';
            const canTurn = side === 'left'
              ? activePage > 0
              : pageIndex !== null && pageIndex < LAST_PAGE_INDEX;
            const turn = side === 'left' ? onPrevious : onNext;
            return (
              <BookPage
                key={`${side}-${pageIndex ?? 'blank'}`}
                pageIndex={pageIndex}
                side={side}
                canTurn={canTurn}
                onTurn={() => handlePageTurn(turn)}
                priority={pageIndex === 0}
              />
            );
          })}
        </motion.div>
      </AnimatePresence>
    </div>
  );
};

const SampleGuideReader = () => {
  const isMobile = useIsMobile();
  const [activePage, setActivePage] = useState(0);
  const [direction, setDirection] = useState(1);
  const visibleIndexes = useMemo(
    () => visiblePageIndexes(activePage, isMobile),
    [activePage, isMobile],
  );
  const lastVisiblePage = Math.max(...visibleIndexes.filter((index) => index !== null));
  const canGoNext = lastVisiblePage < LAST_PAGE_INDEX;

  const goToPage = (pageIndex) => {
    const nextPage = Math.min(LAST_PAGE_INDEX, Math.max(0, pageIndex));
    setDirection(nextPage >= activePage ? 1 : -1);
    setActivePage(isMobile ? nextPage : spreadStartForPage(nextPage));
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
    const nextIndexes = isMobile
      ? [activePage + 1]
      : visiblePageIndexes(activePage === 0 ? 1 : activePage + 2, false);
    nextIndexes
      .filter((index) => index !== null && index <= LAST_PAGE_INDEX)
      .forEach((index) => {
        const image = new Image();
        image.src = SAMPLE_PAGES[index].image;
      });
  }, [activePage, isMobile]);

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
      className="parchment-wash scroll-mt-20 border-t border-border/50 bg-card py-20 sm:py-24"
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
          <p className="text-sm font-bold uppercase tracking-[0.2em] text-secondary">
            Um guia completo de verdade
          </p>
          <h2
            id="guia-exemplo-title"
            className="mt-3 text-3xl font-serif font-bold text-foreground sm:text-4xl lg:text-5xl"
          >
            Folheie a aventura antes de criar a sua
          </h2>
          <p className="mt-4 text-lg font-medium leading-relaxed text-muted-foreground">
            São 19 páginas reais, da capa à volta para casa. Clique nas folhas, use as setas ou
            deslize no celular para conhecer o livro inteiro.
          </p>
          <div className="mt-5 flex items-center justify-center gap-2 text-sm font-bold text-primary">
            {isMobile ? (
              <MoveHorizontal className="h-4 w-4" aria-hidden="true" />
            ) : (
              <MousePointer2 className="h-4 w-4" aria-hidden="true" />
            )}
            {isMobile
              ? 'Deslize a página ou use os botões para folhear'
              : 'Passe o mouse no canto e clique para folhear'}
          </div>
        </motion.div>

        <div
          className="mt-12 rounded-[2rem] border-2 border-border/60 bg-background/75 p-3 shadow-[0_28px_80px_-36px_rgba(74,55,30,0.55)] backdrop-blur sm:p-6 lg:p-8"
          tabIndex={0}
          onKeyDown={handleKeyboard}
          aria-label="Leitor do guia de exemplo. Use as setas esquerda e direita para folhear."
        >
          <div className="mb-5 flex items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10 text-primary">
                <BookOpen className="h-5 w-5" aria-hidden="true" />
              </span>
              <div>
                <p className="font-serif text-lg font-bold text-foreground">Família Knopp em Paris</p>
                <p className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Guia demonstrativo</p>
              </div>
            </div>

            <Dialog>
              <DialogTrigger asChild>
                <Button
                  type="button"
                  variant="outline"
                  className="rounded-full border-2"
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
                  direction={direction}
                  isMobile={isMobile}
                  onNext={goNext}
                  onPrevious={goPrevious}
                  expanded
                />
                {controls}
              </DialogContent>
            </Dialog>
          </div>

          <BookViewport
            activePage={activePage}
            direction={direction}
            isMobile={isMobile}
            onNext={goNext}
            onPrevious={goPrevious}
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
                    className="h-full w-full object-cover"
                  />
                  <span>{page.number}</span>
                </button>
              );
            })}
          </div>
        </div>

        <div className="mt-9 flex flex-col items-center justify-center gap-4 text-center sm:flex-row">
          <p className="max-w-lg font-medium text-muted-foreground">
            O roteiro, os lugares e as atividades mudam. O cuidado com cada página permanece.
          </p>
          <Button asChild size="lg" className="group rounded-full px-7 py-6 font-bold">
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
