import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Check,
  CircleCheck,
  CreditCard,
  Download,
  ImageIcon,
  Loader2,
  Mail,
  RefreshCcw,
  BookOpen,
} from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import {
  approveBuilderPage,
  builderGenerationRetryDelaySeconds,
  createGuideCheckout,
  createIdempotencyKey,
  downloadGuidePdf,
  fetchBuilderAssetObjectUrl,
  fetchGuideBuilderSession,
  formatPrice,
  generateBuilderPageAttempt,
  getBuilderPayment,
  getGuideProduct,
  getGuideJob,
  isRetryableBuilderGenerationError,
  mercadoPagoReturnPayment,
  queueGuideBuilderGeneration,
  refreshGuidePayment,
} from '@/utils/minerva-api.js';

const MAX_COVER_ATTEMPTS = 4;
const MAX_REVISION_LENGTH = 600;
const sleep = (milliseconds) => new Promise((resolve) => window.setTimeout(resolve, milliseconds));

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

const jobStageLabel = (stage) => ({
  queued: 'Na fila de criação',
  validating: 'Conferindo o roteiro',
  preparing_assets: 'Preparando as ilustrações',
  generating_cover: 'Preparando a capa',
  generating_content: 'Ilustrando as páginas do guia',
  rendering_pdf: 'Montando o PDF',
  persisting: 'Salvando o guia',
  finalizing: 'Enviando o e-mail',
  complete: 'Concluído',
}[stage] || 'Criando o guia');

const GuideAssembly = ({ session: initialSession }) => {
  const [session, setSession] = useState(initialSession);
  const [coverUrl, setCoverUrl] = useState('');
  const [revisionInstruction, setRevisionInstruction] = useState('');
  const [coverBusy, setCoverBusy] = useState('');
  const [coverError, setCoverError] = useState('');
  const [retryNotice, setRetryNotice] = useState('');
  const [job, setJob] = useState(null);
  const [jobBusy, setJobBusy] = useState(false);
  const [jobError, setJobError] = useState('');
  const [guideProduct, setGuideProduct] = useState(null);
  const [payment, setPayment] = useState(undefined);
  const [paymentBusy, setPaymentBusy] = useState(false);
  const [paymentError, setPaymentError] = useState('');
  const generationKeyRef = useRef('');
  const queueKeyRef = useRef('');

  const cover = useMemo(
    () => session.pages.find((page) => page.kind === 'cover') || null,
    [session.pages],
  );
  const selectedAttempt = cover?.attempts.find(
    (attempt) => attempt.id === cover.selected_attempt_id,
  ) || cover?.attempts.at(-1) || null;
  const generatedPageCount = Math.max(session.pages.length - 1, 0);
  const paymentRequired = guideProduct?.enabled === true;
  const paymentReady = Boolean(guideProduct && (!paymentRequired || payment?.status === 'paid'));

  const loadCover = useCallback(async (attempt) => {
    if (!attempt?.asset_url) {
      setCoverUrl('');
      return;
    }
    try {
      const nextUrl = await fetchBuilderAssetObjectUrl(attempt.asset_url);
      setCoverUrl(nextUrl);
    } catch (error) {
      setCoverError(error.message || 'Não foi possível carregar a capa.');
    }
  }, []);

  useEffect(() => {
    loadCover(selectedAttempt);
  }, [loadCover, selectedAttempt?.asset_url]);

  useEffect(() => () => {
    if (coverUrl) URL.revokeObjectURL(coverUrl);
  }, [coverUrl]);

  const refreshSession = useCallback(async () => {
    const latest = await fetchGuideBuilderSession(session.session_id);
    setSession(latest);
    return latest;
  }, [session.session_id]);

  const refreshPayment = useCallback(async ({ signal } = {}) => {
    const latest = await getBuilderPayment(session.session_id, { signal });
    setPayment(latest);
    return latest;
  }, [session.session_id]);

  useEffect(() => {
    const controller = new AbortController();
    setPaymentError('');
    getGuideProduct({ signal: controller.signal })
      .then(async (product) => {
        setGuideProduct(product);
        if (!product.enabled) {
          setPayment(null);
          return;
        }
        const latest = await refreshPayment({ signal: controller.signal });
        const returnedPayment = mercadoPagoReturnPayment();
        if (
          latest
          && returnedPayment?.localPaymentId === latest.payment_id
          && latest.status !== 'refunded'
        ) {
          const confirmed = await refreshGuidePayment(
            latest.payment_id,
            returnedPayment.providerPaymentId,
            { signal: controller.signal },
          );
          setPayment(confirmed);
        }
      })
      .catch((error) => {
        if (error.name !== 'AbortError') {
          setPaymentError(error.message || 'Não foi possível consultar o pagamento.');
        }
      });
    return () => controller.abort();
  }, [refreshPayment]);

  useEffect(() => {
    if (!paymentRequired || payment?.status !== 'pending') return undefined;
    const timer = window.setInterval(() => {
      refreshPayment().catch((error) => {
        setPaymentError(error.message || 'Não foi possível atualizar o pagamento.');
      });
    }, 5000);
    return () => window.clearInterval(timer);
  }, [payment?.status, paymentRequired, refreshPayment]);

  const handleCheckout = async () => {
    if (paymentBusy) return;
    if (payment?.checkout_url && payment.status === 'pending') {
      window.location.assign(payment.checkout_url);
      return;
    }
    setPaymentBusy(true);
    setPaymentError('');
    try {
      const latest = await createGuideCheckout(session.session_id, createIdempotencyKey());
      setPayment(latest);
      if (latest.status !== 'paid' && latest.checkout_url) {
        window.location.assign(latest.checkout_url);
      }
    } catch (error) {
      setPaymentError(error.message || 'Não foi possível abrir o Mercado Pago.');
    } finally {
      setPaymentBusy(false);
    }
  };

  const handleRefreshPayment = async () => {
    setPaymentBusy(true);
    setPaymentError('');
    try {
      await refreshPayment();
    } catch (error) {
      setPaymentError(error.message || 'Não foi possível atualizar o pagamento.');
    } finally {
      setPaymentBusy(false);
    }
  };

  useEffect(() => {
    const jobId = session.generation_job_id;
    if (!jobId) return undefined;
    let cancelled = false;
    let timer;
    const refreshJob = async () => {
      try {
        const latest = await getGuideJob(jobId);
        if (cancelled) return;
        setJob(latest);
        if (!['succeeded', 'failed', 'cancelled'].includes(latest.status)) {
          timer = window.setTimeout(refreshJob, 5000);
        }
      } catch (error) {
        if (!cancelled) setJobError(error.message || 'Não foi possível consultar a criação.');
      }
    };
    refreshJob();
    return () => {
      cancelled = true;
      if (timer) window.clearTimeout(timer);
    };
  }, [session.generation_job_id]);

  const handleGenerateCover = async () => {
    if (!cover || coverBusy || cover.approved_at || !paymentReady) return;
    setCoverBusy('generate');
    setCoverError('');
    const key = generationKeyRef.current || createIdempotencyKey();
    generationKeyRef.current = key;
    try {
      for (let attempt = 1; attempt <= MAX_COVER_ATTEMPTS; attempt += 1) {
        try {
          const latest = await generateBuilderPageAttempt(
            session.session_id,
            cover.id,
            key,
            revisionInstruction,
          );
          setSession(latest);
          generationKeyRef.current = '';
          setRevisionInstruction('');
          setRetryNotice('');
          toast.success('Preview da capa pronto para revisar.');
          return;
        } catch (error) {
          if (attempt === MAX_COVER_ATTEMPTS || !isRetryableBuilderGenerationError(error)) throw error;
          const delay = builderGenerationRetryDelaySeconds(error, attempt);
          setRetryNotice(`A OpenAI está ocupada. Nova tentativa automática em ${delay}s.`);
          await sleep(delay * 1000);
        }
      }
    } catch (error) {
      setCoverError(error.message || 'Não foi possível gerar o preview da capa.');
    } finally {
      setCoverBusy('');
      setRetryNotice('');
    }
  };

  const handleApproveCover = async () => {
    if (!cover?.selected_attempt_id || coverBusy || cover.approved_at) return;
    setCoverBusy('approve');
    setCoverError('');
    try {
      const latest = await approveBuilderPage(
        session.session_id,
        cover.id,
        cover.selected_attempt_id,
      );
      setSession(latest);
      toast.success('Capa aprovada. Agora podemos criar o guia completo.');
    } catch (error) {
      setCoverError(error.message || 'Não foi possível aprovar a capa.');
    } finally {
      setCoverBusy('');
    }
  };

  const handleQueueGuide = async () => {
    if (!cover?.approved_at || jobBusy || !paymentReady) return;
    setJobBusy(true);
    setJobError('');
    const key = queueKeyRef.current || createIdempotencyKey();
    queueKeyRef.current = key;
    try {
      const queued = await queueGuideBuilderGeneration(session.session_id, key);
      setJob({ id: queued.job_id, ...queued });
      await refreshSession();
      queueKeyRef.current = '';
      toast.success('Criação iniciada. Você já pode fechar esta página.');
    } catch (error) {
      setJobError(error.message || 'Não foi possível iniciar a criação do guia.');
    } finally {
      setJobBusy(false);
    }
  };

  const handleDownload = async () => {
    try {
      const ready = await downloadGuidePdf(job.result.download_url);
      saveBlob(ready.blob, job.result.filename || ready.filename);
    } catch (error) {
      setJobError(error.message || 'Não foi possível baixar o PDF.');
    }
  };

  const jobActive = job && ['queued', 'running'].includes(job.status);
  const jobSucceeded = job?.status === 'succeeded';
  const jobFailed = job && ['failed', 'cancelled'].includes(job.status);

  return (
    <div className="mx-auto w-full max-w-6xl px-4 py-8 sm:px-6">
      <div className="mb-8 text-center">
        <p className="travel-label">Última etapa</p>
        <h1 className="mt-2 font-display text-4xl font-bold text-secondary sm:text-5xl">
          Aprove a capa do seu guia
        </h1>
        <p className="mx-auto mt-3 max-w-2xl font-medium text-muted-foreground">
          Esta é a única página que você precisa revisar. Depois da aprovação, criamos as outras
          {` ${generatedPageCount} páginas`} e enviamos o link do PDF por e-mail.
        </p>
      </div>

      <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_minmax(320px,420px)]">
        <section className="overflow-hidden rounded-2xl border border-primary/15 bg-card shadow-sm">
          <div className="flex min-h-[560px] items-center justify-center bg-muted/35 p-4 sm:p-8">
            {coverUrl ? (
              <img src={coverUrl} alt="Preview da capa do guia" className="max-h-[720px] w-auto rounded-xl object-contain shadow-sm" />
            ) : coverBusy === 'generate' ? (
              <div className="max-w-sm text-center" role="status" aria-live="polite">
                <Loader2 className="mx-auto h-12 w-12 animate-spin text-primary" aria-hidden="true" />
                <p className="mt-5 text-xl font-bold text-foreground">Criando o preview da capa…</p>
                <p className="mt-2 text-sm text-muted-foreground">A ilustração, o nome da família e a data nascem juntos.</p>
              </div>
            ) : (
              <div className="max-w-sm text-center text-muted-foreground">
                <ImageIcon className="mx-auto h-16 w-16" aria-hidden="true" />
                <p className="mt-4 text-lg font-bold text-foreground">Sua capa aparecerá aqui</p>
                <p className="mt-2 text-sm">Gere o primeiro preview para conferir antes do guia completo.</p>
              </div>
            )}
          </div>
        </section>

        <aside className="space-y-5">
          {paymentRequired && payment?.status === 'paid' && (
            <div className="rounded-2xl border border-secondary/30 bg-[hsl(var(--mint))] p-4 text-foreground">
              <div className="flex items-center gap-3">
                <CircleCheck className="h-6 w-6 shrink-0 text-secondary" aria-hidden="true" />
                <div>
                  <p className="font-bold">Pagamento confirmado</p>
                  <p className="text-sm font-medium text-muted-foreground">
                    Seu crédito está vinculado a este guia.
                  </p>
                </div>
              </div>
            </div>
          )}

          {paymentRequired && payment?.status !== 'paid' && (
            <div className="rounded-2xl border border-primary/25 bg-primary/5 p-6 shadow-sm">
              <CreditCard className="h-10 w-10 text-primary" aria-hidden="true" />
              <h2 className="mt-4 font-display text-2xl font-bold text-foreground">
                {payment?.status === 'pending' ? 'Aguardando confirmação' : 'Pagamento necessário'}
              </h2>
              <p className="mt-2 text-sm font-medium text-muted-foreground">
                {payment?.status === 'pending'
                  ? 'Se você pagou por Pix, a confirmação pode levar alguns instantes. Esta tela atualiza automaticamente.'
                  : `Pague ${formatPrice(guideProduct.amount_minor, guideProduct.currency)} no ambiente seguro do Mercado Pago para liberar a criação.`}
              </p>
              <div className="mt-5 grid gap-3">
                <Button
                  type="button"
                  onClick={handleCheckout}
                  disabled={paymentBusy}
                  className="rounded-full py-6 font-bold"
                >
                  {paymentBusy ? (
                    <><Loader2 className="mr-2 h-5 w-5 animate-spin" /> Aguarde…</>
                  ) : (
                    <><CreditCard className="mr-2 h-5 w-5" /> {payment?.status === 'pending' ? 'Voltar ao Mercado Pago' : 'Pagar com Mercado Pago'}</>
                  )}
                </Button>
                {payment?.status === 'pending' && (
                  <Button
                    type="button"
                    variant="outline"
                    onClick={handleRefreshPayment}
                    disabled={paymentBusy}
                    className="rounded-full border-2 py-6 font-bold"
                  >
                    <RefreshCcw className="mr-2 h-5 w-5" /> Atualizar confirmação
                  </Button>
                )}
              </div>
              {paymentError && <p className="mt-4 text-sm font-bold text-destructive" role="alert">{paymentError}</p>}
            </div>
          )}

          {!guideProduct && (
            <div className="rounded-2xl border border-border bg-card p-4" role="status">
              <div className="flex items-center gap-3">
                <Loader2 className="h-5 w-5 animate-spin text-primary" aria-hidden="true" />
                <p className="text-sm font-bold text-foreground">Conferindo a liberação do guia…</p>
              </div>
              {paymentError && <p className="mt-3 text-sm font-bold text-destructive">{paymentError}</p>}
            </div>
          )}

          {!cover?.approved_at && (
            <div className="rounded-2xl border border-border bg-card p-6 shadow-sm">
              <h2 className="font-display text-2xl font-bold text-foreground">{selectedAttempt ? 'Quer mudar alguma coisa?' : 'Gerar a capa'}</h2>
              <p className="mt-2 text-sm font-medium text-muted-foreground">
                {selectedAttempt
                  ? 'Descreva o que deve mudar, inclusive o estilo. Se estiver boa, basta aprovar.'
                  : 'O primeiro preview usa a foto ou a descrição da família e os dados da viagem.'}
              </p>
              {selectedAttempt && (
                <Textarea
                  value={revisionInstruction}
                  onChange={(event) => setRevisionInstruction(event.target.value.slice(0, MAX_REVISION_LENGTH))}
                  placeholder="Ex.: use um estilo de livro infantil, deixe o fundo mais claro e mantenha as mesmas pessoas."
                  className="mt-4 min-h-28 resize-y rounded-xl"
                  disabled={Boolean(coverBusy)}
                />
              )}
              {retryNotice && <p className="mt-3 text-sm font-bold text-primary">{retryNotice}</p>}
              {coverError && <p className="mt-3 text-sm font-bold text-destructive" role="alert">{coverError}</p>}
              <div className="mt-5 grid gap-3">
                <Button
                  type="button"
                  onClick={handleGenerateCover}
                  disabled={!paymentReady || Boolean(coverBusy) || (selectedAttempt && !revisionInstruction.trim())}
                  className="rounded-full py-6 font-bold"
                >
                  {coverBusy === 'generate' ? (
                    <><Loader2 className="mr-2 h-5 w-5 animate-spin" /> Gerando preview…</>
                  ) : (
                    <><RefreshCcw className="mr-2 h-5 w-5" /> {selectedAttempt ? 'Gerar nova versão' : 'Gerar preview da capa'}</>
                  )}
                </Button>
                {selectedAttempt && (
                  <Button type="button" variant="outline" onClick={handleApproveCover} disabled={Boolean(coverBusy)} className="rounded-full border-2 py-6 font-bold">
                    {coverBusy === 'approve' ? (
                      <><Loader2 className="mr-2 h-5 w-5 animate-spin" /> Aprovando…</>
                    ) : (
                      <><Check className="mr-2 h-5 w-5" /> Aprovar esta capa</>
                    )}
                  </Button>
                )}
              </div>
            </div>
          )}

          {cover?.approved_at && !jobSucceeded && (
            <div className="rounded-2xl border border-secondary/25 bg-[hsl(var(--mint))] p-6 shadow-sm">
              <CircleCheck className="h-10 w-10 text-secondary" aria-hidden="true" />
              <h2 className="mt-4 font-display text-2xl font-bold text-foreground">Capa aprovada</h2>
              <p className="mt-2 text-sm font-medium text-muted-foreground">
                Com um clique, criaremos as páginas restantes na ordem certa, montaremos o PDF e enviaremos o link para o e-mail da sua conta.
              </p>
              {jobActive ? (
                <div className="mt-5 rounded-xl bg-card p-4" role="status" aria-live="polite">
                  <div className="flex items-center gap-3">
                    <Loader2 className="h-6 w-6 animate-spin text-primary" aria-hidden="true" />
                    <div>
                      <p className="font-bold text-foreground">{jobStageLabel(job.stage)}</p>
                      <p className="text-xs text-muted-foreground">Você pode fechar esta página com segurança.</p>
                    </div>
                  </div>
                  <div className="mt-4 h-2 overflow-hidden rounded-full bg-muted">
                    <div className="h-full rounded-full bg-primary transition-all" style={{ width: `${job.progress || 0}%` }} />
                  </div>
                </div>
              ) : (
                <Button type="button" onClick={handleQueueGuide} disabled={jobBusy} className="mt-5 w-full rounded-full py-7 text-base font-bold">
                  {jobBusy ? (
                    <><Loader2 className="mr-2 h-5 w-5 animate-spin" /> Iniciando…</>
                  ) : (
                    <><BookOpen className="mr-2 h-5 w-5" /> {jobFailed ? 'Tentar criar novamente' : 'Criar guia completo'}</>
                  )}
                </Button>
              )}
              <div className="mt-4 flex items-start gap-3 rounded-xl border border-secondary/20 bg-card p-4">
                <Mail className="mt-0.5 h-5 w-5 shrink-0 text-secondary" aria-hidden="true" />
                <p className="text-sm font-medium text-muted-foreground">Não é preciso esperar no site. A criação continua mesmo que você saia.</p>
              </div>
              {jobFailed && <p className="mt-4 text-sm font-bold text-destructive" role="alert">{job.error?.message || 'A criação foi interrompida. Você pode tentar novamente.'}</p>}
              {jobError && <p className="mt-4 text-sm font-bold text-destructive" role="alert">{jobError}</p>}
            </div>
          )}

          {jobSucceeded && (
            <div className="rounded-2xl border border-secondary/30 bg-[hsl(var(--mint))] p-6 shadow-sm">
              <CircleCheck className="h-11 w-11 text-secondary" aria-hidden="true" />
              <h2 className="mt-4 font-display text-2xl font-bold text-secondary">Guia pronto e enviado</h2>
              <p className="mt-2 text-sm font-medium text-muted-foreground">Enviamos por e-mail o link do PDF com {job.result?.page_count || session.pages.length} páginas. Agora é imprimir, pôr na mochila e partir.</p>
              <Button type="button" onClick={handleDownload} className="mt-5 w-full rounded-full py-6 font-bold">
                <Download className="mr-2 h-5 w-5" /> Baixar PDF agora
              </Button>
              {jobError && <p className="mt-3 text-sm font-bold text-destructive" role="alert">{jobError}</p>}
            </div>
          )}
        </aside>
      </div>
    </div>
  );
};

export default GuideAssembly;
