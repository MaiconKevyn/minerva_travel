import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Helmet } from 'react-helmet';
import { Link } from 'react-router-dom';
import {
  AlertCircle,
  ArrowRight,
  BookOpen,
  CalendarDays,
  ChevronDown,
  CircleCheck,
  Clock3,
  Download,
  Loader2,
  Mail,
  MapPin,
  RefreshCw,
  Settings,
  Trash2,
} from 'lucide-react';
import Header from '@/components/Header.jsx';
import GuideCover from '@/components/GuideCover.jsx';
import {
  CompassRose,
  LeafSprig,
  RouteDoodle,
  Suitcase,
} from '@/components/DecorativeElements.jsx';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/contexts/AuthContext.jsx';
import {
  deleteGuide,
  downloadGuidePdf,
  getGuide,
  listGuideJobs,
  listGuides,
} from '@/utils/minerva-api.js';
import { toast } from 'sonner';

const guideStatusConfig = {
  queued: { label: 'Na fila', className: 'bg-muted text-muted-foreground' },
  running: { label: 'Em andamento', className: 'bg-secondary/15 text-secondary' },
  succeeded: { label: 'Pronto', className: 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-300' },
  failed: { label: 'Falhou', className: 'bg-destructive/10 text-destructive' },
  cancelled: { label: 'Cancelado', className: 'bg-muted text-muted-foreground' },
};

const statusForGuide = (status) => guideStatusConfig[status] || {
  label: 'Status desconhecido',
  className: 'bg-muted text-muted-foreground',
};

const jobStageLabel = (stage) => ({
  queued: 'Aguardando para começar',
  validating: 'Conferindo o roteiro',
  preparing_assets: 'Preparando as ilustrações',
  generating_content: 'Criando as páginas do livro',
  rendering_pdf: 'Montando o PDF',
  persisting: 'Salvando na sua biblioteca',
  finalizing: 'Finalizando a entrega',
}[stage] || 'Criando o guia');

const destinationNames = (destinations = []) => destinations
  .map((destination) => {
    if (typeof destination === 'string') return destination.trim();
    return String(
      destination?.place || destination?.display_title || destination?.city || destination?.name || '',
    ).trim();
  })
  .filter(Boolean);

const formatDate = (value) => {
  if (!value) return 'Não informado';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return 'Não informado';
  return new Intl.DateTimeFormat('pt-BR', { dateStyle: 'medium' }).format(date);
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

const DashboardPage = () => {
  const { user } = useAuth();
  const [guides, setGuides] = useState([]);
  const [generationJobs, setGenerationJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [selectedGuideId, setSelectedGuideId] = useState(null);
  const [selectedGuide, setSelectedGuide] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState('');
  const [downloadingGuideId, setDownloadingGuideId] = useState(null);
  const [deletingGuideId, setDeletingGuideId] = useState(null);
  const [confirmDeleteGuideId, setConfirmDeleteGuideId] = useState(null);
  const listAbortController = useRef(null);
  const detailAbortController = useRef(null);

  const loadGuideList = useCallback(async ({ signal, background = false } = {}) => {
    if (!background) {
      setLoading(true);
      setLoadError('');
    }
    try {
      const [records, jobs] = await Promise.all([
        listGuides({ signal }),
        listGuideJobs({ signal }),
      ]);
      if (!signal?.aborted) {
        const completedIds = new Set(records.map((record) => record.id));
        setGuides(records);
        setGenerationJobs(jobs.filter((job) => (
          job.guide_preview
          && !completedIds.has(job.id)
          && ['queued', 'running', 'failed'].includes(job.status)
        )));
      }
    } catch (error) {
      if (!background && error.name !== 'AbortError' && !signal?.aborted) {
        setLoadError(error.message || 'Não foi possível carregar seus guias.');
      }
    } finally {
      if (!background && !signal?.aborted) setLoading(false);
    }
  }, []);

  const requestGuideList = useCallback((background = false) => {
    listAbortController.current?.abort();
    const controller = new AbortController();
    listAbortController.current = controller;
    loadGuideList({ signal: controller.signal, background }).finally(() => {
      if (listAbortController.current === controller) {
        listAbortController.current = null;
      }
    });
  }, [loadGuideList]);

  useEffect(() => {
    requestGuideList();
    return () => listAbortController.current?.abort();
  }, [requestGuideList]);

  useEffect(() => {
    if (!generationJobs.some((job) => ['queued', 'running'].includes(job.status))) {
      return undefined;
    }
    const timer = window.setInterval(() => requestGuideList(true), 5000);
    return () => window.clearInterval(timer);
  }, [generationJobs, requestGuideList]);

  useEffect(() => () => detailAbortController.current?.abort(), []);

  const closeGuideDetails = () => {
    detailAbortController.current?.abort();
    detailAbortController.current = null;
    setSelectedGuideId(null);
    setSelectedGuide(null);
    setDetailError('');
    setDetailLoading(false);
  };

  const loadGuideDetails = async (guideId) => {
    detailAbortController.current?.abort();
    const controller = new AbortController();
    detailAbortController.current = controller;
    setSelectedGuideId(guideId);
    setSelectedGuide(null);
    setDetailError('');
    setDetailLoading(true);

    try {
      const record = await getGuide(guideId, { signal: controller.signal });
      if (!controller.signal.aborted) setSelectedGuide(record);
    } catch (error) {
      if (error.name !== 'AbortError' && !controller.signal.aborted) {
        setDetailError(error.message || 'Não foi possível carregar os detalhes.');
      }
    } finally {
      if (!controller.signal.aborted) setDetailLoading(false);
      if (detailAbortController.current === controller) {
        detailAbortController.current = null;
      }
    }
  };

  const toggleGuideDetails = (guideId) => {
    if (selectedGuideId === guideId) {
      closeGuideDetails();
      return;
    }
    loadGuideDetails(guideId);
  };

  const handleDownload = async (guide) => {
    if (!guide.download_url) {
      toast.error('Este guia não possui um download disponível.');
      return;
    }

    setDownloadingGuideId(guide.id);
    try {
      const { blob, filename } = await downloadGuidePdf(guide.download_url);
      saveBlob(blob, filename);
      toast.success('Download iniciado.');
    } catch (error) {
      toast.error(error.message || 'Não foi possível baixar o guia.');
    } finally {
      setDownloadingGuideId(null);
    }
  };

  const handleDelete = async (guide) => {
    setDeletingGuideId(guide.id);
    try {
      const deleted = await deleteGuide(guide.id);
      if (!deleted) throw new Error('A API não confirmou a exclusão.');
      setGuides((current) => current.filter((item) => item.id !== guide.id));
      if (selectedGuideId === guide.id) closeGuideDetails();
      setConfirmDeleteGuideId(null);
      toast.success('Guia excluído com sucesso.');
    } catch (error) {
      toast.error(error.message || 'Não foi possível excluir o guia.');
    } finally {
      setDeletingGuideId(null);
    }
  };

  const readyGuideCount = guides.filter((guide) => guide.status === 'succeeded').length;
  const activeJobCount = generationJobs.filter((job) => (
    ['queued', 'running'].includes(job.status)
  )).length;
  const hasFailedJob = generationJobs.some((job) => job.status === 'failed');
  const nextAction = loading
    ? 'Organizando a estante'
    : activeJobCount > 0
      ? 'Acompanhe a criação'
      : hasFailedJob
        ? 'Revise a criação interrompida'
        : readyGuideCount > 0
          ? 'Planeje outra viagem'
          : 'Crie o primeiro guia';

  return (
    <>
      <Helmet>
        <title>Meu Painel - Minerva Travel</title>
      </Helmet>

      <div className="min-h-screen bg-background flex flex-col transition-colors duration-200">
        <Header />

        <main id="main-content" tabIndex={-1} className="travel-page storybook-paper relative flex-1 overflow-hidden px-4 py-10 sm:px-6 lg:px-8 lg:py-14">
          <CompassRose className="page-corner -right-6 top-20 rotate-12" />
          <LeafSprig className="page-corner -bottom-12 -left-8 -rotate-12 text-secondary" />

          <div className="guide-shell relative z-10">
            <section
              className="travel-card storybook-sky relative overflow-hidden p-6 sm:p-8 lg:p-10"
              aria-labelledby="dashboard-welcome-title"
            >
              <Suitcase className="pointer-events-none absolute -bottom-7 -right-5 h-32 w-32 rotate-6 text-accent opacity-20 sm:h-40 sm:w-40" />
              <div className="relative flex flex-col items-start justify-between gap-7 lg:flex-row lg:items-center">
                <div className="flex min-w-0 items-center gap-3 sm:gap-5">
                  <div className="flex h-14 w-14 shrink-0 -rotate-2 items-center justify-center rounded-[1rem_1.35rem_0.9rem_1.2rem] border-2 border-primary/20 bg-[hsl(var(--blush))] shadow-sm sm:h-20 sm:w-20">
                    <span className="font-serif text-2xl text-primary sm:text-4xl" aria-hidden="true">
                      {user?.name?.charAt(0)?.toUpperCase() || 'F'}
                    </span>
                  </div>
                  <div className="min-w-0">
                    <span className="travel-label mb-2 -rotate-1">Diário da família</span>
                    <h1 id="dashboard-welcome-title" className="font-serif text-2xl font-bold text-secondary sm:text-4xl md:text-5xl">
                      Olá, {user?.name || 'Viajante'}!
                    </h1>
                    <p className="editorial-copy mt-2 max-w-xl text-sm text-foreground/70 sm:text-base">
                      Seus livros, lembranças e próximas aventuras moram aqui.
                    </p>
                  </div>
                </div>
                <Button asChild className="travel-cta w-full shrink-0 px-6 font-bold sm:w-auto">
                  <Link to="/create">
                    Criar novo guia
                    <ArrowRight className="h-4 w-4" aria-hidden="true" />
                  </Link>
                </Button>
              </div>
            </section>

            <section className="mt-5 grid gap-4 sm:grid-cols-3" aria-label="Resumo da biblioteca">
              <article className="travel-card flex items-center gap-4 p-5">
                <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-emerald-500/15 text-emerald-700">
                  <CircleCheck className="h-5 w-5" aria-hidden="true" />
                </span>
                <div>
                  <p className="text-2xl font-black text-secondary">{loading ? '—' : readyGuideCount}</p>
                  <p className="text-sm font-bold text-muted-foreground">Na estante</p>
                </div>
              </article>
              <article className="travel-card flex items-center gap-4 p-5">
                <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-secondary/15 text-secondary">
                  <Clock3 className="h-5 w-5" aria-hidden="true" />
                </span>
                <div>
                  <p className="text-2xl font-black text-secondary">{loading ? '—' : activeJobCount}</p>
                  <p className="text-sm font-bold text-muted-foreground">Em criação</p>
                </div>
              </article>
              <article className="travel-card storybook-blush flex items-center gap-4 p-5">
                <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-primary/15 text-primary">
                  <ArrowRight className="h-5 w-5" aria-hidden="true" />
                </span>
                <div className="min-w-0">
                  <p className="text-xs font-black uppercase tracking-[0.12em] text-primary">Próximo passo</p>
                  <p className="mt-1 font-serif text-base font-bold text-foreground">{nextAction}</p>
                </div>
              </article>
            </section>

            <details className="travel-card storybook-mint group mt-5 overflow-hidden px-5 py-1">
              <summary className="flex min-h-12 cursor-pointer list-none items-center justify-between gap-4 py-3 font-bold text-secondary marker:content-none">
                <span className="flex items-center gap-2">
                  <Settings className="h-4 w-4" aria-hidden="true" />
                  Dados da conta
                </span>
                <ChevronDown className="h-4 w-4 transition-transform group-open:rotate-180" aria-hidden="true" />
              </summary>
              <dl className="space-y-4">
                <div className="grid gap-1 border-t border-secondary/10 pt-4 sm:grid-cols-[7rem_1fr]">
                  <dt className="text-xs font-bold uppercase text-muted-foreground">Nome</dt>
                  <dd className="font-medium text-foreground">{user?.name || 'Não informado'}</dd>
                </div>
                <div className="grid gap-1 pb-4 sm:grid-cols-[7rem_1fr]">
                  <dt className="text-xs font-bold uppercase text-muted-foreground">Email</dt>
                  <dd className="break-words font-medium text-foreground">{user?.email || 'Não informado'}</dd>
                </div>
              </dl>
            </details>

            <section className="mt-12" aria-labelledby="dashboard-guides-title">
              <div className="relative mb-6 flex flex-col items-start justify-between gap-4 sm:flex-row sm:items-end">
                <RouteDoodle className="pointer-events-none absolute -top-12 right-20 hidden h-16 w-36 text-secondary/25 sm:block" />
                <div>
                  <span className="travel-label mb-2 -rotate-1">Livros da família</span>
                  <h2 id="dashboard-guides-title" className="font-serif text-2xl font-bold text-secondary sm:text-3xl">
                    Sua estante de viagens
                  </h2>
                </div>
                <p className="flex max-w-md items-center gap-2 text-sm font-medium text-muted-foreground">
                  <Mail className="h-4 w-4 shrink-0 text-primary" aria-hidden="true" />
                  Quando um guia ficar pronto, também avisaremos pelo seu e-mail.
                </p>
              </div>

              {!loading && !loadError && generationJobs.length > 0 && (
                <section className="mb-8" aria-labelledby="dashboard-generating-title">
                  <div className="mb-4 flex items-end justify-between gap-4">
                    <div>
                      <h3 id="dashboard-generating-title" className="text-xl font-serif font-bold text-foreground">
                        Guias em criação
                      </h3>
                      <p className="mt-1 text-sm font-medium text-muted-foreground">
                        Pode fechar esta página: a criação continua e avisaremos por e-mail.
                      </p>
                    </div>
                  </div>
                  <div className="grid grid-cols-1 gap-5 md:grid-cols-2">
                    {generationJobs.map((job) => {
                      const preview = job.guide_preview;
                      const status = statusForGuide(job.status);
                      const destinations = destinationNames(preview.destinations);
                      const progress = Math.min(100, Math.max(0, Number(job.progress) || 0));
                      const readyPages = Math.max(0, Number(preview.approved_page_count) || 0);
                      const totalPages = Math.max(0, Number(preview.page_count) || 0);
                      return (
                        <article
                          key={job.id}
                          className="travel-card storybook-sky p-5"
                        >
                          <div className="flex gap-4">
                            <GuideCover coverUrl={preview.cover_url} title={preview.title} />
                            <div className="min-w-0 flex-1">
                              <div className="flex items-start justify-between gap-2">
                                <p className="text-xs font-black uppercase tracking-[0.14em] text-secondary">
                                  Preview aprovado
                                </p>
                                <span className={`rounded-full px-3 py-1 text-xs font-bold ${status.className}`}>
                                  {status.label}
                                </span>
                              </div>
                              <h4 className="mt-2 font-serif text-lg font-bold text-foreground">
                                {preview.title || 'Guia de viagem'}
                              </h4>
                              {destinations.length > 0 && (
                                <p className="mt-1 line-clamp-2 text-sm font-medium text-muted-foreground">
                                  {destinations.join(', ')}
                                </p>
                              )}
                              <p className="mt-3 text-sm font-bold text-foreground" role="status" aria-live="polite">
                                {jobStageLabel(job.stage)}
                              </p>
                            </div>
                          </div>
                          <div
                            className="mt-5 h-2 overflow-hidden rounded-full bg-background/80"
                            role="progressbar"
                            aria-label={`Progresso de ${preview.title || 'guia de viagem'}`}
                            aria-valuemin={0}
                            aria-valuemax={100}
                            aria-valuenow={progress}
                          >
                            <div
                              className="h-full rounded-full bg-secondary transition-all duration-500"
                              style={{ width: `${progress}%` }}
                            />
                          </div>
                          <div className="mt-2 flex items-center justify-between gap-3 text-xs font-bold text-muted-foreground">
                            <span>{progress}% concluído</span>
                            <span>
                              {totalPages > 0
                                ? `${readyPages} de ${totalPages} páginas prontas`
                                : 'Páginas sendo montadas'}
                            </span>
                          </div>
                          {job.status === 'failed' && (
                            <p className="mt-4 rounded-2xl bg-destructive/10 p-3 text-sm font-bold text-destructive" role="alert">
                              {job.error?.message || 'A criação foi interrompida. Abra o guia para tentar novamente.'}
                            </p>
                          )}
                        </article>
                      );
                    })}
                  </div>
                </section>
              )}

              {loading ? (
                <div
                  role="status"
                  aria-live="polite"
                  className="grid grid-cols-1 gap-6 md:grid-cols-2"
                >
                  <span className="sr-only">Buscando suas histórias...</span>
                  <div className="travel-card animate-pulse p-5" aria-hidden="true">
                    <div className="flex gap-4">
                      <div className="aspect-[3/4] w-20 rounded-xl bg-secondary/10" />
                      <div className="flex-1 space-y-3 pt-2">
                        <div className="h-3 w-24 rounded-full bg-primary/10" />
                        <div className="h-5 w-4/5 rounded-full bg-secondary/10" />
                        <div className="h-3 w-2/3 rounded-full bg-secondary/10" />
                      </div>
                    </div>
                    <div className="mt-5 h-11 rounded-full bg-secondary/10" />
                  </div>
                  <div className="travel-card hidden animate-pulse p-5 md:block" aria-hidden="true">
                    <div className="flex gap-4">
                      <div className="aspect-[3/4] w-20 rounded-xl bg-secondary/10" />
                      <div className="flex-1 space-y-3 pt-2">
                        <div className="h-3 w-24 rounded-full bg-primary/10" />
                        <div className="h-5 w-4/5 rounded-full bg-secondary/10" />
                        <div className="h-3 w-2/3 rounded-full bg-secondary/10" />
                      </div>
                    </div>
                    <div className="mt-5 h-11 rounded-full bg-secondary/10" />
                  </div>
                </div>
              ) : loadError ? (
                <div
                  role="alert"
                  className="travel-card flex flex-col items-center gap-4 border-destructive/30 p-10 text-center"
                >
                  <AlertCircle className="w-10 h-10 text-destructive" aria-hidden="true" />
                  <div>
                    <h3 className="text-xl font-bold font-serif text-foreground">Não foi possível abrir sua biblioteca</h3>
                    <p className="mt-2 text-muted-foreground font-medium">{loadError}</p>
                  </div>
                  <Button type="button" variant="outline" onClick={() => requestGuideList()} className="rounded-full">
                    <RefreshCw className="w-4 h-4" aria-hidden="true" />
                    Tentar novamente
                  </Button>
                </div>
              ) : guides.length === 0 ? (
                <div className="travel-card storybook-blush flex flex-col items-center justify-center space-y-4 border-2 border-dashed border-primary/25 px-5 py-10 text-center sm:p-12">
                  <div className="mb-2 flex h-20 w-20 -rotate-3 items-center justify-center rounded-[1.2rem_1.6rem_1rem_1.5rem] bg-[hsl(var(--paper))]">
                    <BookOpen className="w-10 h-10 text-muted-foreground/50" aria-hidden="true" />
                  </div>
                  <h3 className="text-xl font-bold font-serif text-foreground">O livro está em branco!</h3>
                  <p className="text-muted-foreground font-medium max-w-sm">
                    {generationJobs.length > 0
                      ? 'Seu primeiro livro ainda está sendo criado e aparecerá aqui quando estiver pronto.'
                      : 'Você ainda não criou nenhum guia. Que tal planejar a próxima aventura?'}
                  </p>
                  {generationJobs.length === 0 && (
                    <Button asChild className="travel-cta mt-2 px-6 font-bold">
                      <Link to="/create">
                        Criar meu primeiro guia
                        <ArrowRight className="h-4 w-4" aria-hidden="true" />
                      </Link>
                    </Button>
                  )}
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {guides.map((guide) => {
                    const status = statusForGuide(guide.status);
                    const destinations = destinationNames(guide.destinations);
                    const detailsOpen = selectedGuideId === guide.id;
                    const detailsId = `guide-details-${guide.id}`;
                    const deleteConfirmationId = `guide-delete-confirmation-${guide.id}`;
                    const isDownloading = downloadingGuideId === guide.id;
                    const isDeleting = deletingGuideId === guide.id;
                    const isConfirmingDelete = confirmDeleteGuideId === guide.id;

                    return (
                      <article
                        key={guide.id}
                        className="travel-card group flex h-full flex-col p-4 transition-all duration-300 hover:-translate-y-1 hover:border-primary/30 hover:shadow-lg sm:p-6"
                      >
                        {/* A capa é o produto: cada item da lista é um livro,
                            não um registro de texto. */}
                        <div className="flex flex-1 gap-4">
                          <GuideCover coverUrl={guide.cover_url} title={guide.title} />

                          <div className="min-w-0 flex-1">
                            <div className="mb-3 flex items-start justify-between gap-3">
                              <div className="flex items-center gap-2">
                                <MapPin className="h-4 w-4 text-primary" aria-hidden="true" />
                                <span className="text-xs font-bold uppercase tracking-wider text-primary">
                                  Viagem em família
                                </span>
                              </div>
                              <span className={`rounded-full px-3 py-1 text-xs font-bold ${status.className}`}>
                                {status.label}
                              </span>
                            </div>

                            <h3 className="mb-2 text-lg font-serif font-bold text-foreground transition-colors group-hover:text-primary xl:text-xl">
                              {guide.title || 'Guia sem título'}
                            </h3>
                            {destinations.length > 0 && (
                              <p className="line-clamp-2 text-sm font-medium text-muted-foreground">
                                Destinos: {destinations.join(', ')}
                              </p>
                            )}
                          </div>
                        </div>

                        <div className="mt-6 space-y-4 border-t-2 border-dashed border-secondary/20 pt-4">
                          <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
                            <CalendarDays className="w-4 h-4" aria-hidden="true" />
                            Criado em {formatDate(guide.created_at)}
                          </div>

                          <div className="flex flex-wrap gap-2">
                            {guide.download_url && (
                              <Button
                                type="button"
                                size="sm"
                                onClick={() => handleDownload(guide)}
                                disabled={isDownloading}
                                className="rounded-full bg-secondary text-white hover:bg-secondary/90"
                              >
                                {isDownloading ? (
                                  <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" />
                                ) : (
                                  <Download className="w-4 h-4" aria-hidden="true" />
                                )}
                                Baixar PDF
                              </Button>
                            )}

                            <Button
                              type="button"
                              variant="outline"
                              size="sm"
                              onClick={() => toggleGuideDetails(guide.id)}
                              aria-expanded={detailsOpen}
                              aria-controls={detailsId}
                              className="rounded-full"
                            >
                              {detailsOpen ? 'Ocultar detalhes' : 'Ver detalhes'}
                              <ChevronDown
                                className={`w-4 h-4 transition-transform ${detailsOpen ? 'rotate-180' : ''}`}
                                aria-hidden="true"
                              />
                            </Button>

                            <Button
                              type="button"
                              variant="ghost"
                              size="sm"
                              disabled={isDeleting}
                              onClick={() => setConfirmDeleteGuideId(
                                isConfirmingDelete ? null : guide.id,
                              )}
                              aria-expanded={isConfirmingDelete}
                              aria-controls={deleteConfirmationId}
                              className="rounded-full text-destructive hover:bg-destructive/10 hover:text-destructive"
                            >
                              {isDeleting ? (
                                <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" />
                              ) : (
                                <Trash2 className="w-4 h-4" aria-hidden="true" />
                              )}
                              Excluir
                            </Button>
                          </div>

                          {isConfirmingDelete && (
                            <div
                              id={deleteConfirmationId}
                              role="group"
                              aria-label={`Confirmar exclusão de ${guide.title || 'guia sem título'}`}
                              className="rounded-2xl border border-destructive/30 bg-destructive/5 p-4"
                            >
                              <p className="text-sm font-bold text-foreground">Excluir definitivamente?</p>
                              <p className="mt-1 text-sm text-muted-foreground">
                                O guia e seus arquivos serão removidos. Esta ação não pode ser desfeita.
                              </p>
                              <div className="mt-3 flex flex-wrap gap-2">
                                <Button
                                  type="button"
                                  variant="outline"
                                  size="sm"
                                  disabled={isDeleting}
                                  onClick={() => setConfirmDeleteGuideId(null)}
                                  className="rounded-full"
                                >
                                  Cancelar
                                </Button>
                                <Button
                                  type="button"
                                  size="sm"
                                  disabled={isDeleting}
                                  onClick={() => handleDelete(guide)}
                                  className="rounded-full bg-destructive text-destructive-foreground hover:bg-destructive/90"
                                >
                                  {isDeleting && (
                                    <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" />
                                  )}
                                  Excluir guia
                                </Button>
                              </div>
                            </div>
                          )}

                          {guide.status === 'succeeded' && !guide.download_url && (
                            <p className="text-sm font-medium text-muted-foreground">
                              O download deste guia não está mais disponível.
                            </p>
                          )}
                        </div>

                        {detailsOpen && (
                          <div
                            id={detailsId}
                            aria-live="polite"
                            className="storybook-mint mt-5 rounded-2xl border border-secondary/15 p-4 text-sm"
                          >
                            {detailLoading ? (
                              <div role="status" className="flex items-center gap-2 text-muted-foreground">
                                <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" />
                                Carregando detalhes...
                              </div>
                            ) : detailError ? (
                              <div role="alert" className="space-y-3">
                                <p className="font-medium text-destructive">{detailError}</p>
                                <Button
                                  type="button"
                                  variant="outline"
                                  size="sm"
                                  onClick={() => loadGuideDetails(guide.id)}
                                  className="rounded-full"
                                >
                                  <RefreshCw className="w-4 h-4" aria-hidden="true" />
                                  Tentar novamente
                                </Button>
                              </div>
                            ) : selectedGuide ? (
                              <dl className="space-y-3 text-foreground">
                                <div>
                                  <dt className="font-bold">Destinos</dt>
                                  <dd className="text-muted-foreground">
                                    {destinationNames(selectedGuide.destinations).join(', ') || 'Não informados'}
                                  </dd>
                                </div>
                                <div>
                                  <dt className="font-bold">Download disponível até</dt>
                                  <dd className="text-muted-foreground">{formatDate(selectedGuide.expires_at)}</dd>
                                </div>
                                {selectedGuide.cover_fallback_used && (
                                  <div>
                                    <dt className="font-bold">Capa</dt>
                                    <dd className="text-muted-foreground">
                                      Uma alternativa segura foi usada na composição da capa.
                                    </dd>
                                  </div>
                                )}
                              </dl>
                            ) : null}
                          </div>
                        )}
                      </article>
                    );
                  })}
                </div>
              )}
            </section>
          </div>
        </main>
      </div>
    </>
  );
};

export default DashboardPage;
