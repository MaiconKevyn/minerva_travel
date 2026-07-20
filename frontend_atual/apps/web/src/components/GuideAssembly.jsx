import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { motion } from 'framer-motion';
import {
  AlertCircle,
  Check,
  CircleCheck,
  Download,
  ImageIcon,
  Loader2,
  RefreshCcw,
  Sparkles,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import { Textarea } from '@/components/ui/textarea';
import {
  approveBuilderPage,
  completeGuideBuilder,
  createIdempotencyKey,
  downloadGuidePdf,
  fetchBuilderAssetObjectUrl,
  fetchGuideBuilderSession,
  builderGenerationRetryDelaySeconds,
  generateBuilderPdf,
  generateBuilderPageAttempt,
  isRetryableBuilderGenerationError,
  selectBuilderPageAttempt,
} from '@/utils/minerva-api.js';
import { toast } from 'sonner';

const STATUS_LABELS = {
  ready: 'Pronta para gerar',
  generating: 'Gerando',
  awaiting_approval: 'Aguardando sua aprovação',
  approved: 'Aprovada',
  error: 'Precisa tentar novamente',
};

const MAX_REVISION_INSTRUCTION_LENGTH = 600;
const MAX_GENERATION_ATTEMPTS = 4;

const PAGE_KIND_LABELS = {
  cover: 'Capa',
  trip_summary: 'Resumo do roteiro',
  destination_intro: 'Destino e curiosidades',
  landmark: 'Ponto turístico',
  landmark_activity: 'Atividade',
  best_memory: 'Página obrigatória',
  homecoming: 'Encerramento obrigatório',
};

const saveBlob = (blob, filename) => {
  const objectUrl = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = objectUrl;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(objectUrl);
};

const formatRetryDelay = (seconds) => {
  if (seconds < 60) return `${seconds} segundo${seconds === 1 ? '' : 's'}`;
  const minutes = Math.ceil(seconds / 60);
  return `${minutes} minuto${minutes === 1 ? '' : 's'}`;
};

const waitForRetry = (delayMs, signal) => new Promise((resolve, reject) => {
  const abort = () => {
    window.clearTimeout(timer);
    const error = new Error('Geração cancelada.');
    error.name = 'AbortError';
    reject(error);
  };
  const timer = window.setTimeout(() => {
    signal.removeEventListener('abort', abort);
    resolve();
  }, delayMs);
  signal.addEventListener('abort', abort, { once: true });
  if (signal.aborted) abort();
});

const GuideAssembly = ({ session: initialSession }) => {
  const [session, setSession] = useState(initialSession);
  const [selectedPageId, setSelectedPageId] = useState(
    initialSession.active_page_id || initialSession.pages[0]?.id || '',
  );
  const [assetUrls, setAssetUrls] = useState({});
  const [assetLoadErrors, setAssetLoadErrors] = useState({});
  const [pageBusyActions, setPageBusyActions] = useState({});
  const [pageErrors, setPageErrors] = useState({});
  const [pageRetryNotices, setPageRetryNotices] = useState({});
  const [revisionInstructions, setRevisionInstructions] = useState({});
  const [includeFamilyByPage, setIncludeFamilyByPage] = useState({});
  const [busyAction, setBusyAction] = useState('');
  const [actionError, setActionError] = useState('');
  const [completion, setCompletion] = useState(null);
  const [pdfExport, setPdfExport] = useState(null);
  const objectUrlsRef = useRef(new Set());
  const hydratedAssetUrlsRef = useRef(new Set());
  const generationKeysRef = useRef({});
  const generationAbortControllersRef = useRef(new Map());

  const hydrateAssets = useCallback(async (nextSession) => {
    const urls = [...new Set(
      nextSession.pages.flatMap((page) => page.attempts.map((attempt) => attempt.asset_url)),
    )].filter((url) => !hydratedAssetUrlsRef.current.has(url));
    urls.forEach((url) => hydratedAssetUrlsRef.current.add(url));
    const failures = [];
    const loaded = await Promise.all(
      urls.map(async (url) => {
        try {
          const objectUrl = await fetchBuilderAssetObjectUrl(url);
          objectUrlsRef.current.add(objectUrl);
          return [url, objectUrl];
        } catch (error) {
          console.error('Erro ao carregar página gerada:', error);
          hydratedAssetUrlsRef.current.delete(url);
          failures.push(url);
          return null;
        }
      }),
    );
    setAssetUrls((current) => {
      const next = { ...current };
      loaded.filter(Boolean).forEach(([url, objectUrl]) => {
        if (next[url]) {
          URL.revokeObjectURL(objectUrl);
          objectUrlsRef.current.delete(objectUrl);
        } else {
          next[url] = objectUrl;
        }
      });
      return next;
    });
    setAssetLoadErrors((current) => {
      const next = { ...current };
      loaded.filter(Boolean).forEach(([url]) => delete next[url]);
      failures.forEach((url) => {
        next[url] = 'Não foi possível carregar esta imagem. Tente gerar novamente.';
      });
      return next;
    });
  }, []);

  useEffect(() => {
    const objectUrls = objectUrlsRef.current;
    const hydratedAssetUrls = hydratedAssetUrlsRef.current;
    const generationAbortControllers = generationAbortControllersRef.current;
    hydrateAssets(initialSession);
    return () => {
      objectUrls.forEach((url) => URL.revokeObjectURL(url));
      objectUrls.clear();
      hydratedAssetUrls.clear();
      generationAbortControllers.forEach((controller) => controller.abort());
      generationAbortControllers.clear();
    };
  }, [hydrateAssets, initialSession]);

  const activePage = useMemo(
    () => session.pages.find((page) => page.id === selectedPageId)
      || session.pages.find((page) => page.id === session.active_page_id)
      || session.pages[0]
      || null,
    [selectedPageId, session],
  );
  const activePageBusyAction = activePage ? pageBusyActions[activePage.id] || '' : '';
  const activePageError = activePage ? pageErrors[activePage.id] || '' : '';
  const activePageRetryNotice = activePage ? pageRetryNotices[activePage.id] || '' : '';
  const revisionInstruction = activePage ? revisionInstructions[activePage.id] || '' : '';
  const includeFamily = activePage ? includeFamilyByPage[activePage.id] || false : false;
  const selectedAttempt = activePage?.attempts.find(
    (attempt) => attempt.id === activePage.selected_attempt_id,
  );
  const selectedImageUrl = selectedAttempt ? assetUrls[selectedAttempt.asset_url] : '';
  const selectedAssetError = selectedAttempt
    ? assetLoadErrors[selectedAttempt.asset_url]
    : '';

  useEffect(() => {
    if (!session.pages.some((page) => page.id === selectedPageId)) {
      setSelectedPageId(session.active_page_id || session.pages[0]?.id || '');
    }
  }, [selectedPageId, session.active_page_id, session.pages]);

  const applySession = useCallback(async (nextSession) => {
    setSession((current) => (
      Number(nextSession.revision || 0) > Number(current.revision || 0)
        ? nextSession
        : current
    ));
    await hydrateAssets(nextSession);
    return nextSession;
  }, [hydrateAssets]);

  const updateSession = async (operation) => {
    const nextSession = await operation();
    return applySession(nextSession);
  };

  useEffect(() => {
    if (!session.pages.some((page) => page.status === 'generating')) return undefined;
    let cancelled = false;
    const refresh = async () => {
      try {
        const latest = await fetchGuideBuilderSession(session.session_id);
        if (!cancelled) await applySession(latest);
      } catch (error) {
        console.error('Erro ao atualizar páginas em geração:', error);
      }
    };
    const timer = window.setInterval(refresh, 2500);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [applySession, session.pages, session.session_id]);

  const setPageBusy = (pageId, action) => {
    setPageBusyActions((current) => {
      const next = { ...current };
      if (action) next[pageId] = action;
      else delete next[pageId];
      return next;
    });
  };

  const setPageError = (pageId, message) => {
    setPageErrors((current) => ({ ...current, [pageId]: message }));
  };

  const setPageRetryNotice = (pageId, message) => {
    setPageRetryNotices((current) => {
      const next = { ...current };
      if (message) next[pageId] = message;
      else delete next[pageId];
      return next;
    });
  };

  const handleGenerate = async () => {
    if (
      !activePage
      || pageBusyActions[activePage.id]
      || activePage.status === 'generating'
      || activePage.approved_at
    ) return;
    const page = activePage;
    setPageBusy(page.id, 'generate');
    setPageError(page.id, '');
    const key = generationKeysRef.current[page.id] || createIdempotencyKey();
    generationKeysRef.current[page.id] = key;
    const requestedRevision = (revisionInstructions[page.id] || '').trim();
    const controller = new AbortController();
    generationAbortControllersRef.current.set(page.id, controller);
    try {
      let failedAttempts = 0;
      while (failedAttempts < MAX_GENERATION_ATTEMPTS) {
        try {
          await updateSession(() =>
            generateBuilderPageAttempt(
              session.session_id,
              page.id,
              key,
              requestedRevision,
              page.kind === 'landmark' && Boolean(includeFamilyByPage[page.id]),
              { signal: controller.signal },
            ),
          );
          break;
        } catch (error) {
          failedAttempts += 1;
          if (
            controller.signal.aborted
            || failedAttempts >= MAX_GENERATION_ATTEMPTS
            || !isRetryableBuilderGenerationError(error)
          ) throw error;
          const delaySeconds = builderGenerationRetryDelaySeconds(error, failedAttempts);
          setPageRetryNotice(
            page.id,
            `Limite temporário. Nova tentativa automática em ${formatRetryDelay(delaySeconds)} `
              + `(${failedAttempts + 1} de ${MAX_GENERATION_ATTEMPTS}).`,
          );
          await waitForRetry(delaySeconds * 1000, controller.signal);
          setPageRetryNotice(page.id, 'Tentando gerar esta página novamente...');
        }
      }
      delete generationKeysRef.current[page.id];
      setRevisionInstructions((current) => ({ ...current, [page.id]: '' }));
      toast.success(`${page.title} gerada. Confira todos os textos antes de aprovar.`);
    } catch (error) {
      if (error.name !== 'AbortError') {
        setPageError(page.id, error.message || 'Não foi possível gerar esta página.');
      }
    } finally {
      if (generationAbortControllersRef.current.get(page.id) === controller) {
        generationAbortControllersRef.current.delete(page.id);
      }
      setPageRetryNotice(page.id, '');
      setPageBusy(page.id, '');
    }
  };

  const handleSelect = async (attemptId) => {
    if (
      !activePage
      || pageBusyActions[activePage.id]
      || activePage.status === 'generating'
      || activePage.approved_at
    ) return;
    const page = activePage;
    setPageBusy(page.id, 'select');
    setPageError(page.id, '');
    try {
      await updateSession(() =>
        selectBuilderPageAttempt(session.session_id, page.id, attemptId),
      );
    } catch (error) {
      setPageError(page.id, error.message || 'Não foi possível escolher esta versão.');
    } finally {
      setPageBusy(page.id, '');
    }
  };

  const handleApprove = async () => {
    if (
      !activePage?.selected_attempt_id
      || pageBusyActions[activePage.id]
      || activePage.status === 'generating'
      || activePage.approved_at
    ) return;
    const page = activePage;
    setPageBusy(page.id, 'approve');
    setPageError(page.id, '');
    try {
      const nextSession = await updateSession(() =>
        approveBuilderPage(
          session.session_id,
          page.id,
          page.selected_attempt_id,
        ),
      );
      setSelectedPageId(nextSession.active_page_id || page.id);
      toast.success(`${page.title} aprovada.`);
    } catch (error) {
      setPageError(page.id, error.message || 'Não foi possível aprovar esta página.');
    } finally {
      setPageBusy(page.id, '');
    }
  };

  const handleComplete = async () => {
    setBusyAction('complete');
    setActionError('');
    try {
      setCompletion(await completeGuideBuilder(session.session_id));
    } catch (error) {
      setActionError(error.message || 'Não foi possível concluir a revisão.');
    } finally {
      setBusyAction('');
    }
  };

  const handlePdfExport = async () => {
    setBusyAction('pdf');
    setActionError('');
    try {
      const readyPdf = await generateBuilderPdf(session.session_id);
      setPdfExport(readyPdf);
      const { blob, filename } = await downloadGuidePdf(readyPdf.download_url);
      saveBlob(blob, readyPdf.filename || filename);
      toast.success('PDF gerado. O download foi iniciado.');
    } catch (error) {
      setActionError(error.message || 'Não foi possível gerar e baixar o PDF.');
    } finally {
      setBusyAction('');
    }
  };

  const pageAssetUrl = (page) => {
    const attempt = page.attempts.find((item) => item.id === page.selected_attempt_id);
    return attempt ? assetUrls[attempt.asset_url] : '';
  };

  if (completion) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        className="mx-auto w-full max-w-6xl space-y-8 py-10 text-center"
      >
        <CircleCheck className="mx-auto h-16 w-16 text-secondary" />
        <div className="space-y-3">
          <h2 className="text-4xl font-serif font-bold text-foreground">Páginas aprovadas!</h2>
          <p className="mx-auto max-w-2xl text-lg font-medium text-muted-foreground">
            Estas são as imagens finais escolhidas. Gere o PDF para reuni-las na mesma sequência,
            com uma imagem ocupando cada página.
          </p>
        </div>
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {session.pages.map((page) => (
            <figure key={page.id} className="rounded-3xl border bg-card p-3 shadow-sm">
              <img
                src={pageAssetUrl(page)}
                alt={page.title}
                className="aspect-[2/3] w-full rounded-2xl bg-muted object-contain"
              />
              <figcaption className="px-2 py-3 font-bold text-foreground">{page.title}</figcaption>
            </figure>
          ))}
        </div>
        <div className="mx-auto max-w-xl rounded-3xl border-2 border-secondary/30 bg-card p-6 shadow-sm">
          {pdfExport && (
            <p className="mb-3 font-bold text-secondary" role="status">
              PDF pronto com {pdfExport.page_count} páginas.
            </p>
          )}
          {actionError && (
            <p className="mb-3 font-bold text-destructive" role="alert">
              {actionError}
            </p>
          )}
          <Button
            type="button"
            onClick={handlePdfExport}
            disabled={busyAction === 'pdf'}
            className="w-full rounded-full py-6 text-base font-bold"
          >
            {busyAction === 'pdf' ? (
              <Loader2 className="mr-2 h-5 w-5 animate-spin" />
            ) : (
              <Download className="mr-2 h-5 w-5" />
            )}
            {busyAction === 'pdf'
              ? 'Gerando PDF...'
              : pdfExport
                ? 'Baixar PDF novamente'
                : 'Gerar PDF e baixar'}
          </Button>
        </div>
      </motion.div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      className="mx-auto grid w-full max-w-6xl gap-6 py-10 lg:grid-cols-[280px_minmax(0,1fr)]"
    >
      <aside className="h-fit rounded-[2rem] border-2 border-border/70 bg-card p-5 shadow-sm">
        <p className="mb-4 text-xs font-bold uppercase tracking-[0.22em] text-muted-foreground">
          Páginas do guia
        </p>
        <ol className="space-y-3">
          {session.pages.map((page) => {
            const isSelected = page.id === activePage?.id;
            const isRecommended = page.id === session.active_page_id;
            const pageBusyAction = pageBusyActions[page.id];
            return (
              <li key={page.id}>
                <button
                  type="button"
                  onClick={() => setSelectedPageId(page.id)}
                  aria-current={isSelected ? 'page' : undefined}
                  className={`w-full rounded-2xl border px-4 py-3 text-left transition-colors ${
                    isSelected
                      ? 'border-primary bg-primary/5 shadow-sm'
                      : 'border-border/60 hover:border-primary/40 hover:bg-muted/40'
                  }`}
                >
                  <div className="flex items-start gap-3">
                    <span className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-sm font-bold ${
                      page.status === 'approved' ? 'bg-secondary text-white' : 'bg-muted text-foreground'
                    }`}>
                      {page.status === 'approved' ? (
                        <Check className="h-4 w-4" />
                      ) : pageBusyAction === 'generate' || page.status === 'generating' ? (
                        <Loader2 className="h-4 w-4 animate-spin text-primary" />
                      ) : (
                        page.position
                      )}
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className="font-bold text-foreground">{page.title}</p>
                      <p className="mt-1 text-[11px] font-bold uppercase tracking-wide text-primary">
                        {page.kind === 'landmark_activity' && page.metadata?.activity_label
                          ? page.metadata.activity_label
                          : PAGE_KIND_LABELS[page.kind]}
                      </p>
                      <p className="mt-1 text-xs font-medium text-muted-foreground">
                        {pageBusyAction === 'generate'
                          ? STATUS_LABELS.generating
                          : STATUS_LABELS[page.status]}
                      </p>
                      {isRecommended && page.status !== 'approved' && (
                        <p className="mt-1 text-[10px] font-bold uppercase tracking-wide text-secondary">
                          Próxima pendente
                        </p>
                      )}
                    </div>
                  </div>
                </button>
              </li>
            );
          })}
        </ol>
      </aside>

      <section className="space-y-6">
        <div className="space-y-3 text-center lg:text-left">
          <h2 className="text-3xl font-serif font-bold text-foreground md:text-4xl">
            Gere e confira na ordem que preferir
          </h2>
          <p className="text-lg font-medium text-muted-foreground">
            Clique em qualquer página do guia. Você pode iniciar outra geração enquanto uma já
            está em andamento; a sequência final continuará seguindo a numeração ao lado.
          </p>
        </div>

        {session.is_complete ? (
          <section className="rounded-[2rem] border-2 border-secondary/40 bg-card p-8 text-center shadow-sm">
            <CircleCheck className="mx-auto mb-4 h-12 w-12 text-secondary" />
            <h3 className="text-2xl font-serif font-bold text-foreground">Todas as páginas estão aprovadas</h3>
            <p className="mx-auto mt-2 max-w-xl text-muted-foreground">
              Continue para revisar a sequência final e gerar o PDF para download.
            </p>
            {actionError && <p className="mt-4 font-bold text-destructive">{actionError}</p>}
            <Button
              type="button"
              onClick={handleComplete}
              disabled={busyAction === 'complete'}
              className="mt-6 rounded-full px-10 py-6 text-base font-bold"
            >
              {busyAction === 'complete' ? <Loader2 className="mr-2 h-5 w-5 animate-spin" /> : <Sparkles className="mr-2 h-5 w-5" />}
              Ver páginas aprovadas
            </Button>
          </section>
        ) : activePage ? (
          <section className="rounded-[2rem] border-2 border-border/70 bg-card p-4 shadow-sm sm:p-6">
            <div className="mb-5 flex flex-col justify-between gap-3 sm:flex-row sm:items-start">
              <div>
                <p className="text-xs font-bold uppercase tracking-[0.2em] text-primary">
                  Página {activePage.position} de {session.pages.length}
                </p>
                <h3 className="mt-1 text-2xl font-serif font-bold text-foreground">{activePage.title}</h3>
                <div className="mt-2 flex flex-wrap gap-2 text-xs font-bold">
                  <span className="rounded-full bg-primary/10 px-3 py-1 text-primary">
                    {activePage.kind === 'landmark_activity' && activePage.metadata?.activity_label
                      ? activePage.metadata.activity_label
                      : PAGE_KIND_LABELS[activePage.kind]}
                  </span>
                  {activePage.kind === 'landmark_activity' && activePage.metadata?.landmark_name && (
                    <span className="rounded-full bg-muted px-3 py-1 text-muted-foreground">
                      Ligada a {activePage.metadata.landmark_name}
                    </span>
                  )}
                  {activePage.kind === 'destination_intro' && activePage.metadata?.country && (
                    <span className="rounded-full bg-muted px-3 py-1 text-muted-foreground">
                      País: {activePage.metadata.country}
                    </span>
                  )}
                </div>
              </div>
              <span className="rounded-full bg-muted px-4 py-2 text-xs font-bold text-muted-foreground">
                {activePage.attempts_left} versões disponíveis
              </span>
            </div>

            <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_260px]">
              <div className="overflow-hidden rounded-3xl border border-border/70 bg-muted/50">
                {selectedAttempt && selectedImageUrl ? (
                  <img
                    src={selectedImageUrl}
                    alt={`Versão escolhida de ${activePage.title}`}
                    className="mx-auto aspect-[2/3] max-h-[72vh] w-full bg-white object-contain"
                  />
                ) : (
                  <div className="flex min-h-[520px] flex-col items-center justify-center gap-4 px-6 text-center text-muted-foreground">
                    {activePageBusyAction === 'generate' || activePage.status === 'generating' ? (
                      <>
                        <Loader2 className="h-10 w-10 animate-spin text-primary" />
                        <p className="font-bold text-foreground">Gerando a página completa...</p>
                        <p className="max-w-sm text-sm">A ilustração e os textos serão produzidos juntos pela IA.</p>
                      </>
                    ) : (
                      <>
                        <ImageIcon className="h-12 w-12" />
                        <p className="font-bold text-foreground">Nenhuma imagem gerada ainda</p>
                        <p className="max-w-sm text-sm">Clique em “Gerar página” quando estiver pronto.</p>
                      </>
                    )}
                  </div>
                )}
              </div>

              <div className="space-y-5 text-left">
                <div className="rounded-2xl bg-muted/60 p-4">
                  <p className="text-xs font-bold uppercase tracking-[0.16em] text-muted-foreground">
                    Confira na imagem
                  </p>
                  <ul className="mt-3 space-y-2">
                    {activePage.required_copy.map((copy) => (
                      <li key={copy} className="flex gap-2 text-sm font-medium text-foreground">
                        <Check className="mt-0.5 h-4 w-4 shrink-0 text-secondary" />
                        <span>{copy}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                {activePage.attempts.length > 0 && (
                  <div>
                    <p className="mb-3 text-sm font-bold text-foreground">Versões geradas</p>
                    <div className="grid grid-cols-2 gap-3">
                      {activePage.attempts.map((attempt, index) => {
                        const selected = attempt.id === activePage.selected_attempt_id;
                        return (
                          <button
                            key={attempt.id}
                            type="button"
                            disabled={
                              Boolean(activePageBusyAction)
                              || activePage.status === 'generating'
                              || Boolean(activePage.approved_at)
                            }
                            onClick={() => handleSelect(attempt.id)}
                            className={`relative overflow-hidden rounded-2xl border-4 ${
                              selected ? 'border-primary' : 'border-transparent hover:border-primary/40'
                            }`}
                          >
                            {assetUrls[attempt.asset_url] ? (
                              <img
                                src={assetUrls[attempt.asset_url]}
                                alt={`Versão ${index + 1}`}
                                className="aspect-[2/3] w-full bg-white object-cover"
                              />
                            ) : (
                              <span className="flex aspect-[2/3] items-center justify-center bg-muted text-muted-foreground">
                                <Loader2 className="h-5 w-5 animate-spin" aria-label="Carregando imagem" />
                              </span>
                            )}
                            <span className="absolute bottom-1 left-1 rounded-full bg-black/70 px-2 py-1 text-[10px] font-bold text-white">
                              Versão {index + 1}
                            </span>
                            {activePage.kind === 'landmark' && (
                              <span className="absolute bottom-1 right-1 rounded-full bg-black/70 px-2 py-1 text-[10px] font-bold text-white">
                                {attempt.include_family ? 'Com família' : 'Sem família'}
                              </span>
                            )}
                            {selected && (
                              <span className="absolute right-1 top-1 flex h-7 w-7 items-center justify-center rounded-full bg-primary text-white">
                                <Check className="h-4 w-4" />
                              </span>
                            )}
                          </button>
                        );
                      })}
                    </div>
                  </div>
                )}

                {selectedAttempt && !activePage.approved_at && (
                  <div className="rounded-2xl border border-primary/20 bg-primary/5 p-4">
                    <label
                      htmlFor={`revision-${activePage.id}`}
                      className="text-sm font-bold text-foreground"
                    >
                      O que você quer mudar nesta versão?
                    </label>
                    <Textarea
                      id={`revision-${activePage.id}`}
                      value={revisionInstruction}
                      onChange={(event) => setRevisionInstructions((current) => ({
                        ...current,
                        [activePage.id]: event.target.value,
                      }))}
                      maxLength={MAX_REVISION_INSTRUCTION_LENGTH}
                      disabled={
                        Boolean(activePageBusyAction) || activePage.status === 'generating'
                      }
                      placeholder="Ex.: mude para um estilo 3D, use tons azuis e deixe o título menor."
                      className="mt-2 min-h-28 resize-y bg-background"
                    />
                    <div className="mt-2 flex items-start justify-between gap-3 text-xs text-muted-foreground">
                      <p>
                        Se deixar vazio, criaremos uma alternativa visivelmente diferente.
                      </p>
                      <span className="shrink-0" aria-live="polite">
                        {revisionInstruction.length}/{MAX_REVISION_INSTRUCTION_LENGTH}
                      </span>
                    </div>
                  </div>
                )}

                {activePage.kind === 'landmark' && !activePage.approved_at && (
                  <div className="rounded-2xl border border-secondary/25 bg-secondary/5 p-4">
                    <div className="flex items-center justify-between gap-4">
                      <div>
                        <label
                          htmlFor={`include-family-${activePage.id}`}
                          className="text-sm font-bold text-foreground"
                        >
                          Incluir família
                        </label>
                        <p className="mt-1 text-xs text-muted-foreground">
                          Desativado por padrão. Ative para usar a foto e a capa aprovada como referência.
                        </p>
                      </div>
                      <Switch
                        id={`include-family-${activePage.id}`}
                        checked={includeFamily}
                        onCheckedChange={(checked) => setIncludeFamilyByPage((current) => ({
                          ...current,
                          [activePage.id]: checked,
                        }))}
                        disabled={
                          Boolean(activePageBusyAction) || activePage.status === 'generating'
                        }
                        aria-label="Incluir família"
                      />
                    </div>
                  </div>
                )}

                {activePageRetryNotice && (
                  <div
                    className="flex gap-3 rounded-2xl bg-amber-500/10 p-4 text-sm font-bold text-amber-800 dark:text-amber-200"
                    role="status"
                    aria-live="polite"
                  >
                    <Loader2 className="h-5 w-5 shrink-0 animate-spin" />
                    <p>{activePageRetryNotice}</p>
                  </div>
                )}

                {(activePageError || activePage.error || selectedAssetError) && (
                  <div className="flex gap-3 rounded-2xl bg-destructive/10 p-4 text-sm font-bold text-destructive">
                    <AlertCircle className="h-5 w-5 shrink-0" />
                    <p>{activePageError || activePage.error || selectedAssetError}</p>
                  </div>
                )}

                {activePage.approved_at ? (
                  <div className="rounded-2xl bg-secondary/10 p-4 text-sm font-bold text-secondary">
                    <CircleCheck className="mr-2 inline h-5 w-5" />
                    Página aprovada. Você pode abrir qualquer outra página na lista.
                  </div>
                ) : (
                  <div className="space-y-3">
                    <Button
                      type="button"
                      variant={selectedAttempt ? 'outline' : 'default'}
                      disabled={
                        Boolean(activePageBusyAction)
                        || activePage.status === 'generating'
                        || activePage.attempts_left <= 0
                      }
                      onClick={handleGenerate}
                      className="w-full rounded-full py-6 font-bold"
                    >
                      {activePageBusyAction === 'generate' ? (
                        <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                      ) : selectedAttempt ? (
                        <RefreshCcw className="mr-2 h-5 w-5" />
                      ) : (
                        <Sparkles className="mr-2 h-5 w-5" />
                      )}
                      {activePageBusyAction === 'generate'
                        ? activePageRetryNotice
                          ? 'Aguardando nova tentativa...'
                          : 'Gerando esta página...'
                        : selectedAttempt && revisionInstruction.trim()
                          ? 'Gerar versão com ajustes'
                          : selectedAttempt
                            ? 'Gerar outra versão'
                            : 'Gerar página'}
                    </Button>
                    <Button
                      type="button"
                      disabled={
                        !selectedAttempt
                        || !selectedImageUrl
                        || Boolean(activePageBusyAction)
                        || activePage.status === 'generating'
                      }
                      onClick={handleApprove}
                      className="w-full rounded-full bg-secondary py-6 font-bold text-white hover:bg-secondary/90"
                    >
                      {activePageBusyAction === 'approve' ? <Loader2 className="mr-2 h-5 w-5 animate-spin" /> : <Check className="mr-2 h-5 w-5" />}
                      Aprovar página
                    </Button>
                    {(activePageBusyAction === 'generate' || activePage.status === 'generating') && (
                      <p className="text-center text-xs font-medium text-muted-foreground" role="status">
                        Você pode abrir outra página e iniciar uma nova geração enquanto aguarda.
                      </p>
                    )}
                  </div>
                )}
              </div>
            </div>
          </section>
        ) : null}
      </section>
    </motion.div>
  );
};

export default GuideAssembly;
