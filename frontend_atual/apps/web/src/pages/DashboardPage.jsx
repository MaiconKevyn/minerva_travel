import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Helmet } from 'react-helmet';
import { Link } from 'react-router-dom';
import {
  AlertCircle,
  BookOpen,
  CalendarDays,
  ChevronDown,
  Download,
  Loader2,
  MapPin,
  RefreshCw,
  Settings,
  Trash2,
} from 'lucide-react';
import Header from '@/components/Header.jsx';
import { Suitcase } from '@/components/DecorativeElements.jsx';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/contexts/AuthContext.jsx';
import {
  deleteGuide,
  downloadGuidePdf,
  getGuide,
  listGuides,
} from '@/utils/minerva-api.js';
import { toast } from 'sonner';

const guideStatusConfig = {
  queued: { label: 'Na fila', className: 'bg-muted text-muted-foreground' },
  running: { label: 'Em geração', className: 'bg-secondary/15 text-secondary' },
  succeeded: { label: 'Pronto', className: 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-300' },
  failed: { label: 'Falhou', className: 'bg-destructive/10 text-destructive' },
  cancelled: { label: 'Cancelado', className: 'bg-muted text-muted-foreground' },
};

const statusForGuide = (status) => guideStatusConfig[status] || {
  label: 'Status desconhecido',
  className: 'bg-muted text-muted-foreground',
};

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

  const loadGuideList = useCallback(async ({ signal } = {}) => {
    setLoading(true);
    setLoadError('');
    try {
      const records = await listGuides({ signal });
      if (!signal?.aborted) setGuides(records);
    } catch (error) {
      if (error.name !== 'AbortError' && !signal?.aborted) {
        setLoadError(error.message || 'Não foi possível carregar seus guias.');
      }
    } finally {
      if (!signal?.aborted) setLoading(false);
    }
  }, []);

  const requestGuideList = useCallback(() => {
    listAbortController.current?.abort();
    const controller = new AbortController();
    listAbortController.current = controller;
    loadGuideList({ signal: controller.signal }).finally(() => {
      if (listAbortController.current === controller) {
        listAbortController.current = null;
      }
    });
  }, [loadGuideList]);

  useEffect(() => {
    requestGuideList();
    return () => listAbortController.current?.abort();
  }, [requestGuideList]);

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

  return (
    <>
      <Helmet>
        <title>Meu Painel - Minerva Travel</title>
      </Helmet>

      <div className="min-h-screen bg-background flex flex-col transition-colors duration-200">
        <Header />

        <main id="main-content" tabIndex={-1} className="flex-1 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 w-full">
          <div className="flex items-center gap-4 mb-12">
            <div className="w-16 h-16 bg-primary/20 rounded-full flex items-center justify-center">
              <span className="text-3xl font-serif text-primary" aria-hidden="true">
                {user?.name?.charAt(0)?.toUpperCase() || 'F'}
              </span>
            </div>
            <div>
              <h1 className="text-3xl md:text-4xl font-serif font-bold text-foreground">
                Olá, {user?.name || 'Viajante'}!
              </h1>
              <p className="text-muted-foreground font-medium">Pronto para a próxima aventura?</p>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            <aside className="lg:col-span-1 space-y-8" aria-label="Dados da conta">
              <div className="bg-card dark:bg-slate-800 rounded-[32px] p-6 shadow-md border-2 border-border/50 dark:border-slate-700 relative overflow-hidden transition-colors duration-200">
                <div aria-hidden="true">
                  <Suitcase className="absolute -bottom-4 -right-4 w-24 h-24 text-accent opacity-10" />
                </div>

                <h2 className="text-xl font-bold font-serif flex items-center gap-2 text-foreground mb-6">
                  <Settings className="w-5 h-5 text-muted-foreground" aria-hidden="true" />
                  Seus dados
                </h2>

                <dl className="space-y-4">
                  <div>
                    <dt className="text-xs font-bold text-muted-foreground uppercase">Nome</dt>
                    <dd className="font-medium text-foreground">{user?.name || 'Não informado'}</dd>
                  </div>
                  <div>
                    <dt className="text-xs font-bold text-muted-foreground uppercase">Email</dt>
                    <dd className="font-medium text-foreground break-words">{user?.email || 'Não informado'}</dd>
                  </div>
                </dl>
              </div>
            </aside>

            <section className="lg:col-span-2" aria-labelledby="dashboard-guides-title">
              <div className="flex items-center justify-between gap-4 mb-6">
                <h2 id="dashboard-guides-title" className="text-2xl font-serif font-bold text-foreground">
                  Seus Livros de Viagem
                </h2>
                <Button asChild className="rounded-full bg-secondary hover:bg-secondary/90 text-white shadow-md">
                  <Link to="/create">Novo Guia</Link>
                </Button>
              </div>

              {loading ? (
                <div
                  role="status"
                  aria-live="polite"
                  className="bg-card dark:bg-slate-800 rounded-[32px] p-12 shadow-sm border border-border/50 flex flex-col items-center justify-center space-y-4 transition-colors duration-200"
                >
                  <Loader2 className="w-10 h-10 animate-spin text-primary/50" aria-hidden="true" />
                  <p className="text-muted-foreground font-medium">Buscando suas histórias...</p>
                </div>
              ) : loadError ? (
                <div
                  role="alert"
                  className="bg-card dark:bg-slate-800 rounded-[32px] p-10 shadow-sm border border-destructive/30 flex flex-col items-center text-center gap-4"
                >
                  <AlertCircle className="w-10 h-10 text-destructive" aria-hidden="true" />
                  <div>
                    <h3 className="text-xl font-bold font-serif text-foreground">Não foi possível abrir sua biblioteca</h3>
                    <p className="mt-2 text-muted-foreground font-medium">{loadError}</p>
                  </div>
                  <Button type="button" variant="outline" onClick={requestGuideList} className="rounded-full">
                    <RefreshCw className="w-4 h-4" aria-hidden="true" />
                    Tentar novamente
                  </Button>
                </div>
              ) : guides.length === 0 ? (
                <div className="bg-card dark:bg-slate-800 rounded-[32px] p-12 shadow-sm border-2 border-dashed border-border flex flex-col items-center justify-center text-center space-y-4 transition-colors duration-200">
                  <div className="w-20 h-20 bg-muted rounded-full flex items-center justify-center mb-2">
                    <BookOpen className="w-10 h-10 text-muted-foreground/50" aria-hidden="true" />
                  </div>
                  <h3 className="text-xl font-bold font-serif text-foreground">O livro está em branco!</h3>
                  <p className="text-muted-foreground font-medium max-w-sm">
                    Você ainda não criou nenhum guia. Que tal planejar a próxima aventura?
                  </p>
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
                        className="group bg-card dark:bg-slate-800 rounded-3xl p-6 shadow-sm border border-border/50 dark:border-slate-700 hover:shadow-lg hover:border-primary/30 transition-all duration-300 flex flex-col h-full"
                      >
                        <div className="flex-1">
                          <div className="flex items-start justify-between gap-3 mb-3">
                            <div className="flex items-center gap-2">
                              <MapPin className="w-5 h-5 text-primary" aria-hidden="true" />
                              <span className="text-sm font-bold text-primary tracking-wider uppercase">
                                Viagem em família
                              </span>
                            </div>
                            <span className={`rounded-full px-3 py-1 text-xs font-bold ${status.className}`}>
                              {status.label}
                            </span>
                          </div>

                          <h3 className="text-2xl font-serif font-bold mb-2 text-foreground group-hover:text-primary transition-colors">
                            {guide.title || 'Guia sem título'}
                          </h3>
                          {destinations.length > 0 && (
                            <p className="text-muted-foreground font-medium mb-4 line-clamp-2">
                              Destinos: {destinations.join(', ')}
                            </p>
                          )}
                        </div>

                        <div className="mt-6 pt-4 border-t border-border space-y-4">
                          <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
                            <CalendarDays className="w-4 h-4" aria-hidden="true" />
                            Criado em {formatDate(guide.created_at)}
                          </div>

                          <div className="flex flex-wrap gap-2">
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
                            className="mt-5 rounded-2xl bg-muted/50 p-4 text-sm"
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
