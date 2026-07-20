import React, { useEffect, useMemo, useState } from 'react';
import {
  Check,
  Clock3,
  Eye,
  GripVertical,
  ImagePlus,
  Loader2,
  LockKeyhole,
  MoveDown,
  MoveUp,
  Pencil,
  Plus,
  Puzzle,
  Trash2,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from '@/components/ui/sheet';
import {
  LANDMARK_ACTIVITY_OPTIONS,
  MAX_OPTIONAL_ACTIVITIES_PER_GUIDE,
  MAX_OPTIONAL_ACTIVITIES_PER_LANDMARK,
} from '@/utils/landmark-activities.js';

const FINAL_PAGE_KINDS = new Set(['best_memory', 'homecoming']);

const GuideActivityPanel = ({
  session,
  busyAction,
  errorMessage,
  onAdd,
  onMove,
  onRemove,
}) => {
  const [open, setOpen] = useState(false);
  const [mode, setMode] = useState('catalog');
  const [selectedLandmarkId, setSelectedLandmarkId] = useState('');
  const [previewActivity, setPreviewActivity] = useState(null);
  const [draggedPageId, setDraggedPageId] = useState('');
  const [announcement, setAnnouncement] = useState('');

  const landmarks = useMemo(
    () => session.pages.filter((page) => page.kind === 'landmark'),
    [session.pages],
  );
  const activities = useMemo(
    () => session.pages.filter((page) => page.kind === 'landmark_activity'),
    [session.pages],
  );

  useEffect(() => {
    if (!landmarks.some((page) => page.metadata?.landmark_selection_id === selectedLandmarkId)) {
      setSelectedLandmarkId(landmarks[0]?.metadata?.landmark_selection_id || '');
    }
  }, [landmarks, selectedLandmarkId]);

  const selectedLandmark = landmarks.find(
    (page) => page.metadata?.landmark_selection_id === selectedLandmarkId,
  );
  const activitiesForSelected = activities.filter(
    (page) => page.metadata?.landmark_selection_id === selectedLandmarkId,
  );

  const legalAnchors = (activityPage) => {
    const linkedPageIndex = session.pages.findIndex(
      (page) => page.id === activityPage.metadata?.linked_landmark_page_id,
    );
    if (linkedPageIndex < 0) return [];
    return session.pages.filter((page, index) => (
      page.id !== activityPage.id
      && index >= linkedPageIndex
      && !FINAL_PAGE_KINDS.has(page.kind)
    ));
  };

  const handleMove = async (page, afterPageId) => {
    if (!afterPageId || afterPageId === page.id) return;
    await onMove(page.id, afterPageId);
    const anchor = session.pages.find((item) => item.id === afterPageId);
    setAnnouncement(`${page.title} movida para depois de ${anchor?.title || 'outra página'}.`);
  };

  const moveRelative = (page, direction) => {
    const currentIndex = session.pages.findIndex((item) => item.id === page.id);
    if (currentIndex < 0) return;
    if (direction === 'down') {
      const next = session.pages[currentIndex + 1];
      if (next && legalAnchors(page).some((anchor) => anchor.id === next.id)) {
        handleMove(page, next.id);
      }
      return;
    }
    const currentAnchor = session.pages[currentIndex - 1];
    const pagesWithoutActivity = session.pages.filter((item) => item.id !== page.id);
    const anchorIndex = pagesWithoutActivity.findIndex((item) => item.id === currentAnchor?.id);
    const previousAnchor = pagesWithoutActivity[anchorIndex - 1];
    if (previousAnchor && legalAnchors(page).some((anchor) => anchor.id === previousAnchor.id)) {
      handleMove(page, previousAnchor.id);
    }
  };

  const handleDropAfter = (anchorPage) => {
    const activityPage = activities.find((page) => page.id === draggedPageId);
    if (
      activityPage
      && legalAnchors(activityPage).some((candidate) => candidate.id === anchorPage.id)
    ) {
      handleMove(activityPage, anchorPage.id);
    }
    setDraggedPageId('');
  };

  return (
    <>
      <Sheet open={open} onOpenChange={setOpen}>
        <SheetTrigger asChild>
          <Button
            type="button"
            variant="outline"
            className="mb-5 w-full rounded-2xl border-primary/30 py-6 font-bold text-primary"
          >
            <ImagePlus className="mr-2 h-5 w-5" aria-hidden="true" />
            Adicionar atividades
          </Button>
        </SheetTrigger>
        <SheetContent
          side="right"
          className="w-full overflow-y-auto p-0 [&>button]:z-20 sm:max-w-2xl"
        >
          <SheetHeader className="sticky top-0 z-10 border-b bg-background/95 px-6 py-5 pr-14 backdrop-blur">
            <SheetTitle className="font-serif text-2xl">Atividades do guia</SheetTitle>
            <SheetDescription>
              Veja uma página real de exemplo, adicione sem gerar e escolha onde ela ficará no PDF.
            </SheetDescription>
          </SheetHeader>

          <div className="space-y-6 p-5 sm:p-6">
            <div className="grid grid-cols-2 rounded-2xl bg-muted p-1" aria-label="Seções do painel">
              <button
                type="button"
                onClick={() => setMode('catalog')}
                aria-pressed={mode === 'catalog'}
                className={`rounded-xl px-3 py-2 text-sm font-bold transition ${
                  mode === 'catalog' ? 'bg-background text-primary shadow-sm' : 'text-muted-foreground'
                }`}
              >
                Escolher atividades
              </button>
              <button
                type="button"
                onClick={() => setMode('order')}
                aria-pressed={mode === 'order'}
                className={`rounded-xl px-3 py-2 text-sm font-bold transition ${
                  mode === 'order' ? 'bg-background text-primary shadow-sm' : 'text-muted-foreground'
                }`}
              >
                Organizar páginas ({activities.length})
              </button>
            </div>

            {errorMessage && (
              <p className="rounded-2xl bg-destructive/10 p-4 text-sm font-bold text-destructive" role="alert">
                {errorMessage}
              </p>
            )}
            <p className="sr-only" aria-live="polite">{announcement}</p>

            {mode === 'catalog' ? (
              <div className="space-y-5">
                <div>
                  <label htmlFor="activity-landmark" className="text-sm font-bold text-foreground">
                    Para qual ponto turístico?
                  </label>
                  <select
                    id="activity-landmark"
                    value={selectedLandmarkId}
                    onChange={(event) => setSelectedLandmarkId(event.target.value)}
                    className="mt-2 h-12 w-full rounded-xl border border-input bg-background px-3 text-sm font-bold text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                  >
                    {landmarks.map((page) => (
                      <option key={page.id} value={page.metadata?.landmark_selection_id}>
                        {page.title}{page.metadata?.country ? ` — ${page.metadata.country}` : ''}
                      </option>
                    ))}
                  </select>
                  <p className="mt-2 text-xs font-medium text-muted-foreground">
                    {activitiesForSelected.length}/{MAX_OPTIONAL_ACTIVITIES_PER_LANDMARK} atividades neste ponto ·{' '}
                    {activities.length}/{MAX_OPTIONAL_ACTIVITIES_PER_GUIDE} no guia
                  </p>
                </div>

                <div className="grid gap-5 sm:grid-cols-2">
                  {LANDMARK_ACTIVITY_OPTIONS.map((activity) => {
                    const existingPage = activitiesForSelected.find(
                      (page) => page.metadata?.activity_type === activity.type,
                    );
                    const pointLimitReached = (
                      activitiesForSelected.length >= MAX_OPTIONAL_ACTIVITIES_PER_LANDMARK
                    );
                    const guideLimitReached = activities.length >= MAX_OPTIONAL_ACTIVITIES_PER_GUIDE;
                    const disabled = (
                      !selectedLandmark
                      || Boolean(existingPage)
                      || pointLimitReached
                      || guideLimitReached
                      || Boolean(busyAction)
                    );
                    return (
                      <article key={activity.type} className="overflow-hidden rounded-3xl border bg-card shadow-sm">
                        <button
                          type="button"
                          onClick={() => setPreviewActivity(activity)}
                          className="group relative block aspect-[2/3] w-full overflow-hidden bg-muted text-left"
                          aria-label={`Ver exemplo completo de ${activity.label}`}
                        >
                          <img
                            src={activity.preview}
                            alt={`Página real de exemplo: ${activity.label}`}
                            className="h-full w-full object-cover object-top transition duration-300 group-hover:scale-[1.02]"
                          />
                          <span className="absolute left-3 top-3 rounded-full bg-foreground/90 px-3 py-1 text-[11px] font-bold uppercase tracking-wide text-background">
                            Exemplo real
                          </span>
                          <span className="absolute bottom-3 right-3 inline-flex items-center rounded-full bg-background/95 px-3 py-2 text-xs font-bold text-foreground shadow">
                            <Eye className="mr-1.5 h-4 w-4" aria-hidden="true" /> Ver página
                          </span>
                        </button>
                        <div className="space-y-3 p-4">
                          <div>
                            <h3 className="font-serif text-lg font-bold text-foreground">{activity.label}</h3>
                            <p className="mt-1 text-sm leading-relaxed text-muted-foreground">
                              {activity.description}
                            </p>
                          </div>
                          <div className="flex flex-wrap gap-2 text-[11px] font-bold text-muted-foreground">
                            <span className="rounded-full bg-muted px-2.5 py-1">{activity.ageLabel}</span>
                            <span className="inline-flex items-center rounded-full bg-muted px-2.5 py-1">
                              <Clock3 className="mr-1 h-3 w-3" aria-hidden="true" /> {activity.durationLabel}
                            </span>
                            <span className="inline-flex items-center rounded-full bg-muted px-2.5 py-1">
                              <Pencil className="mr-1 h-3 w-3" aria-hidden="true" /> {activity.materialLabel}
                            </span>
                          </div>
                          <Button
                            type="button"
                            disabled={disabled}
                            onClick={() => onAdd(selectedLandmarkId, activity.type)}
                            className="w-full rounded-full font-bold"
                          >
                            {busyAction === `add:${activity.type}` ? (
                              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                            ) : existingPage ? (
                              <Check className="mr-2 h-4 w-4" />
                            ) : (
                              <Plus className="mr-2 h-4 w-4" />
                            )}
                            {existingPage
                              ? 'Já está no guia'
                              : pointLimitReached
                                ? 'Limite deste ponto atingido'
                                : guideLimitReached
                                  ? 'Limite do guia atingido'
                                  : 'Adicionar ao guia'}
                          </Button>
                        </div>
                      </article>
                    );
                  })}
                </div>
                <p className="rounded-2xl bg-primary/5 p-4 text-sm font-medium text-muted-foreground">
                  Adicionar cria apenas o bloco da página. A imagem só será produzida quando você
                  abrir essa página e clicar em “Gerar página”.
                </p>
              </div>
            ) : (
              <div className="space-y-4">
                <div>
                  <h3 className="font-serif text-xl font-bold text-foreground">Ordem do guia</h3>
                  <p className="mt-1 text-sm text-muted-foreground">
                    Arraste uma atividade ou escolha “Inserir depois de”. As páginas com cadeado
                    mantêm a ordem narrativa; a numeração abaixo será a ordem exata do PDF.
                  </p>
                </div>

                <ol className="space-y-2">
                  {session.pages.map((page, index) => {
                    const isActivity = page.kind === 'landmark_activity';
                    const activityAnchors = isActivity ? legalAnchors(page) : [];
                    const canMoveUp = isActivity && index > 0 && (() => {
                      const pagesWithout = session.pages.filter((item) => item.id !== page.id);
                      const currentAnchor = session.pages[index - 1];
                      const currentAnchorIndex = pagesWithout.findIndex(
                        (item) => item.id === currentAnchor?.id,
                      );
                      const previous = pagesWithout[currentAnchorIndex - 1];
                      return activityAnchors.some((anchor) => anchor.id === previous?.id);
                    })();
                    const canMoveDown = isActivity && activityAnchors.some(
                      (anchor) => anchor.id === session.pages[index + 1]?.id,
                    );
                    const isDropAnchor = draggedPageId && activities.some(
                      (activity) => (
                        activity.id === draggedPageId
                        && legalAnchors(activity).some((anchor) => anchor.id === page.id)
                      ),
                    );
                    return (
                      <li
                        key={page.id}
                        onDragOver={(event) => {
                          if (isDropAnchor) event.preventDefault();
                        }}
                        onDrop={() => handleDropAfter(page)}
                        className={`rounded-2xl border p-3 transition ${
                          isDropAnchor ? 'border-primary/50 hover:bg-primary/10' : 'border-border/70'
                        }`}
                      >
                        <div className="flex items-start gap-3">
                          <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-muted text-sm font-bold text-foreground">
                            {page.position}
                          </span>
                          {isActivity ? (
                            <button
                              type="button"
                              draggable={!busyAction}
                              onDragStart={() => setDraggedPageId(page.id)}
                              onDragEnd={() => setDraggedPageId('')}
                              className="mt-1 cursor-grab rounded-md text-primary focus:outline-none focus:ring-2 focus:ring-primary"
                              aria-label={`Arrastar ${page.title}`}
                            >
                              <GripVertical className="h-5 w-5" />
                            </button>
                          ) : (
                            <LockKeyhole className="mt-1 h-4 w-4 shrink-0 text-muted-foreground" aria-label="Posição narrativa fixa" />
                          )}
                          <div className="min-w-0 flex-1">
                            <p className="font-bold text-foreground">{page.title}</p>
                            <p className="text-xs font-medium text-muted-foreground">
                              {isActivity
                                ? `Atividade de ${page.metadata?.landmark_name || 'ponto turístico'}`
                                : 'Página narrativa fixa'}
                            </p>
                            {isActivity && (
                              <div className="mt-3 space-y-2">
                                <label htmlFor={`move-${page.id}`} className="sr-only">
                                  Inserir {page.title} depois de
                                </label>
                                <select
                                  id={`move-${page.id}`}
                                  value={session.pages[index - 1]?.id || ''}
                                  onChange={(event) => handleMove(page, event.target.value)}
                                  disabled={Boolean(busyAction)}
                                  className="h-9 w-full rounded-lg border bg-background px-2 text-xs font-bold text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                                >
                                  {activityAnchors.map((anchor) => (
                                    <option key={anchor.id} value={anchor.id}>
                                      Inserir depois de: pág. {anchor.position} — {anchor.title}
                                    </option>
                                  ))}
                                </select>
                                <div className="flex flex-wrap gap-2">
                                  <Button
                                    type="button"
                                    size="sm"
                                    variant="outline"
                                    disabled={!canMoveUp || Boolean(busyAction)}
                                    onClick={() => moveRelative(page, 'up')}
                                    aria-label={`Mover ${page.title} uma posição para cima`}
                                  >
                                    <MoveUp className="mr-1 h-4 w-4" /> Subir
                                  </Button>
                                  <Button
                                    type="button"
                                    size="sm"
                                    variant="outline"
                                    disabled={!canMoveDown || Boolean(busyAction)}
                                    onClick={() => moveRelative(page, 'down')}
                                    aria-label={`Mover ${page.title} uma posição para baixo`}
                                  >
                                    <MoveDown className="mr-1 h-4 w-4" /> Descer
                                  </Button>
                                  <Button
                                    type="button"
                                    size="sm"
                                    variant="ghost"
                                    disabled={Boolean(busyAction) || page.status === 'generating'}
                                    onClick={() => onRemove(page)}
                                    className="text-destructive hover:text-destructive"
                                  >
                                    {busyAction === `remove:${page.id}` ? (
                                      <Loader2 className="mr-1 h-4 w-4 animate-spin" />
                                    ) : (
                                      <Trash2 className="mr-1 h-4 w-4" />
                                    )}
                                    Remover
                                  </Button>
                                </div>
                              </div>
                            )}
                          </div>
                        </div>
                      </li>
                    );
                  })}
                </ol>

                {activities.length === 0 && (
                  <div className="rounded-3xl border-2 border-dashed p-8 text-center">
                    <Puzzle className="mx-auto h-10 w-10 text-muted-foreground" />
                    <p className="mt-3 font-bold text-foreground">Nenhuma atividade opcional</p>
                    <Button type="button" variant="link" onClick={() => setMode('catalog')}>
                      Escolher uma atividade
                    </Button>
                  </div>
                )}
              </div>
            )}
          </div>
        </SheetContent>
      </Sheet>

      <Dialog open={Boolean(previewActivity)} onOpenChange={(value) => !value && setPreviewActivity(null)}>
        <DialogContent className="max-h-[94vh] max-w-3xl overflow-y-auto p-4 sm:p-6">
          <DialogHeader>
            <DialogTitle className="font-serif text-2xl">{previewActivity?.label}</DialogTitle>
            <DialogDescription>
              Exemplo sintético de página completa. O guia final será adaptado ao ponto escolhido.
            </DialogDescription>
          </DialogHeader>
          {previewActivity && (
            <img
              src={previewActivity.preview}
              alt={`Exemplo completo da atividade ${previewActivity.label}`}
              className="mx-auto max-h-[76vh] w-auto rounded-2xl border bg-white object-contain shadow-sm"
            />
          )}
        </DialogContent>
      </Dialog>
    </>
  );
};

export default GuideActivityPanel;
