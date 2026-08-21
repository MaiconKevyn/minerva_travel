
import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import {
  Camera,
  CreditCard,
  FileText,
  Loader2,
  MapPin,
  Navigation,
  Sparkles,
  Star,
  Users,
  BookHeart,
  AlertCircle,
  PenLine,
  Plane,
  MessageCircleHeart,
  Puzzle,
  RefreshCcw,
  ShieldCheck,
} from 'lucide-react';
import { useConversationalGuide } from '@/contexts/ConversationalGuideContext.jsx';
import { Button } from '@/components/ui/button';
import {
  categoryLabelForAttraction,
  buildGuideItineraryPayload,
  createGuideCheckout,
  createGuideBuilder,
  createIdempotencyKey,
  fetchGuideBuilderSession,
  formatPrice,
  getGuideProduct,
  RESTAURANT_RECOMMENDATIONS_EXTRA,
  selectGuideLandmarks,
} from '@/utils/minerva-api.js';
import {
  deriveChildAges,
  deriveChildNames,
  guideDestinationSummaryItems,
  paceLabel,
  pluralize,
  PRIVACY_CONSENT_VERSION,
  serializeGuideDestinations,
} from '@/utils/guide-form.js';
import GuideAssembly from '@/components/GuideAssembly.jsx';
import {
  activityOptionForType,
  guideFlightVocabularyCountries,
} from '@/utils/landmark-activities.js';
import { toast } from 'sonner';

const Step5Review = () => {
  const {
    familyName,
    coverPhoto,
    coverPhotoUrl,
    destination,
    destinationsList,
    parsedData,
    selectedLandmarks,
    landmarkActivitySelections,
    childrenList,
    parentsList,
    expectedCoverFamilyMemberCount,
    photoProcessingConsent,
    privacyConsentAt,
    itineraryMode,
    itineraryPreferences,
    recommendedItinerary,
    restaurantRecommendationsExtra,
    flightVocabularyPages,
    coverBrief,
    setRestaurantRecommendationsExtra,
    year,
    builderSessionId,
    checkpointBuilderSession,
    clearBuilderSessionCheckpoint,
    setStep,
  } = useConversationalGuide();

  const [isGenerating, setIsGenerating] = useState(false);
  const [printConfirmed, setPrintConfirmed] = useState(false);
  const [builderSession, setBuilderSession] = useState(null);
  const [isRestoringSession, setIsRestoringSession] = useState(Boolean(builderSessionId));
  const [sessionRestoreError, setSessionRestoreError] = useState('');
  const [restoreAttempt, setRestoreAttempt] = useState(0);
  const [guideProduct, setGuideProduct] = useState(null);

  useEffect(() => {
    const controller = new AbortController();
    getGuideProduct({ signal: controller.signal })
      .then(setGuideProduct)
      .catch((error) => {
        if (error.name !== 'AbortError') {
          console.error('Não foi possível consultar o produto:', error);
        }
      });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    if (!builderSessionId || builderSession) {
      setIsRestoringSession(false);
      return undefined;
    }
    let active = true;
    setIsRestoringSession(true);
    setSessionRestoreError('');
    fetchGuideBuilderSession(builderSessionId)
      .then((session) => {
        if (active) setBuilderSession(session);
      })
      .catch((error) => {
        if (!active) return;
        if (error.status === 404) {
          toast.error('A montagem anterior expirou. Seu roteiro foi mantido; selecione a foto para continuar.');
          clearBuilderSessionCheckpoint({ returnToPhoto: true });
          return;
        }
        setSessionRestoreError(
          error.message || 'Não foi possível recuperar as páginas agora. Tente novamente.',
        );
      })
      .finally(() => {
        if (active) setIsRestoringSession(false);
      });
    return () => {
      active = false;
    };
  }, [
    builderSession,
    builderSessionId,
    clearBuilderSessionCheckpoint,
    restoreAttempt,
  ]);

  // Derive the rich data from the IDs
  const finalLandmarks = selectGuideLandmarks(parsedData.landmarks, selectedLandmarks);
  const flightVocabularyCountries = guideFlightVocabularyCountries(finalLandmarks);
  const childNamesList = deriveChildNames(childrenList);
  const childrenNames = childNamesList.join(', ');
  const childrenAges = deriveChildAges(childrenList);
  const destinationSummary = serializeGuideDestinations(destinationsList) || destination;
  const destinationSummaryItems = guideDestinationSummaryItems(destinationsList);
  const parentsNames = parentsList.join(', ');
  const recommendedDays = (recommendedItinerary?.days || [])
    .map((day) => ({
      ...day,
      landmarks: finalLandmarks.filter((landmark) => landmark.itinerary_day === day.day),
    }))
    .filter((day) => day.landmarks.length > 0);
  const extraLandmarks = finalLandmarks.filter((landmark) => !landmark.itinerary_day);

  const buildGuideData = () => {
    const itinerary = buildGuideItineraryPayload({
      itineraryMode,
      destinationsList,
      itineraryPreferences,
      recommendedDays,
      extraLandmarks,
    });
    return {
      title: `Família ${familyName}`,
      childrenNames,
      childrenAges,
      parentsNames,
      year,
      familyPhoto: coverPhoto, // Pass the actual File object
      expectedVisibleFamilyMemberCount: expectedCoverFamilyMemberCount,
      photoProcessingConsent,
      privacyConsentVersion: PRIVACY_CONSENT_VERSION,
      privacyConsentAt,
      landmarks: finalLandmarks,
      selectedLandmarks,
      landmarkActivitySelections,
      itinerary,
      restaurantRecommendationsExtra,
      flightVocabularyPages,
      coverBrief,
    };
  };

  const handleGenerate = async () => {
    setIsGenerating(true);
    const guideData = buildGuideData();
    try {
      const session = await createGuideBuilder(guideData);
      await checkpointBuilderSession(session.session_id);
      const product = guideProduct || await getGuideProduct();
      if (!product.enabled) {
        setBuilderSession(session);
        return;
      }
      const payment = await createGuideCheckout(session.session_id, createIdempotencyKey());
      if (payment.status === 'paid') {
        setBuilderSession(session);
        return;
      }
      if (payment.checkout_url) {
        window.location.assign(payment.checkout_url);
        return;
      }
      setBuilderSession(session);
    } catch (error) {
      console.error('Não foi possível iniciar a criação por páginas:', error);
      toast.error(error.message || 'Não foi possível iniciar as páginas do guia.');
    } finally {
      setIsGenerating(false);
    }
  };

  if (builderSession) {
    return <GuideAssembly session={builderSession} />;
  }

  if (isRestoringSession) {
    return (
      <div className="mx-auto flex min-h-[50vh] w-full max-w-2xl flex-col items-center justify-center px-6 text-center">
        <Loader2 className="mb-5 h-12 w-12 animate-spin text-primary" aria-hidden="true" />
        <h2 className="text-3xl font-display font-bold text-secondary">Recuperando suas páginas…</h2>
        <p className="mt-3 font-medium text-muted-foreground">
          As imagens, versões escolhidas e aprovações estão sendo carregadas do seu guia.
        </p>
      </div>
    );
  }

  if (sessionRestoreError) {
    return (
      <div className="mx-auto w-full max-w-2xl rounded-2xl border border-destructive/30 bg-card p-8 text-center shadow-sm">
        <AlertCircle className="mx-auto h-12 w-12 text-destructive" aria-hidden="true" />
        <h2 className="mt-4 text-3xl font-display font-bold text-secondary">
          Não conseguimos carregar as páginas
        </h2>
        <p className="mt-3 font-medium text-muted-foreground" role="alert">
          {sessionRestoreError}
        </p>
        <Button
          type="button"
          onClick={() => setRestoreAttempt((attempt) => attempt + 1)}
          className="mt-6 rounded-full px-8 py-6 font-bold"
        >
          <RefreshCcw className="mr-2 h-5 w-5" aria-hidden="true" />
          Tentar carregar novamente
        </Button>
      </div>
    );
  }

  // Group final landmarks by destination id
  const groupedLandmarks = finalLandmarks.reduce((acc, landmark) => {
    if (!acc[landmark.destination_id]) {
      acc[landmark.destination_id] = [];
    }
    acc[landmark.destination_id].push(landmark);
    return acc;
  }, {});
  const activitiesForLandmark = (landmark) => {
    const landmarkSelectionId = String(landmark.selection_id || landmark.id || '');
    return landmarkActivitySelections
      .filter((selection) => selection.landmark_selection_id === landmarkSelectionId)
      .map((selection) => activityOptionForType(selection.activity_type))
      .filter(Boolean);
  };

  const LandmarkActivities = ({ landmark }) => {
    const activities = activitiesForLandmark(landmark);
    if (activities.length === 0) return null;
    return (
      <div className="mt-2 flex flex-wrap gap-2" aria-label={`Atividades escolhidas para ${landmark.name}`}>
        {activities.map((activity) => (
          <span
            key={activity.type}
            className="inline-flex items-center gap-1 rounded-full bg-primary/10 px-2.5 py-1 text-xs font-bold text-primary"
          >
            <Puzzle className="h-3 w-3" aria-hidden="true" />
            {activity.label}
          </span>
        ))}
      </div>
    );
  };

  return (
    <div className="w-full max-w-4xl mx-auto space-y-12">
      <div className="text-center space-y-4">
        <h2 className="text-3xl md:text-4xl font-display font-bold text-secondary">
          Perfeito! Aqui está o resumo do seu roteiro
        </h2>
        <p className="editorial-copy text-lg text-muted-foreground">Revise as informações antes de gerarmos o guia ilustrado da família.</p>
      </div>

      <div className="rounded-2xl border border-border/50 bg-card p-5 shadow-sm sm:p-8 md:p-12">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-10">

          <div className="space-y-4">
            <h3 className="text-xl font-display font-bold flex items-center gap-2 text-primary">
              <Camera className="w-5 h-5" /> A Capa
            </h3>
            {coverPhotoUrl ? (
              <>
                <div className="aspect-[4/3] overflow-hidden rounded-xl shadow-sm">
                  <img src={coverPhotoUrl} alt="Capa do Guia" className="w-full h-full object-cover" />
                </div>
                {expectedCoverFamilyMemberCount > 0 && (
                  <p className="text-sm text-muted-foreground">
                    Pessoas esperadas na capa: {expectedCoverFamilyMemberCount}
                  </p>
                )}
              </>
            ) : (
              <div className="flex aspect-[4/3] items-center justify-center rounded-xl border border-dashed border-border bg-muted">
                <p className="text-muted-foreground font-medium">Sem foto de capa</p>
              </div>
            )}
          </div>

          <div className="space-y-8">
            <div>
              <h3 className="text-xl font-display font-bold flex items-center gap-2 text-secondary mb-3">
                <Users className="w-5 h-5" /> Protagonistas
              </h3>
              <p className="font-medium text-lg text-foreground">Família {familyName}</p>
              {(childrenNames || parentsNames) && (
                <div className="mt-2 text-sm text-muted-foreground space-y-1">
                  {parentsNames && <p>Pais: {parentsNames}</p>}
                  {childrenNames && (
                    <p>
                      Crianças: {childNamesList.map((name, index) => (
                        `${name}${childrenAges[index] ? ` (${childrenAges[index]} anos)` : ''}`
                      )).join(', ')}
                    </p>
                  )}
                </div>
              )}
            </div>

            <div>
              <h3 className="text-xl font-display font-bold flex items-center gap-2 text-secondary mb-3">
                <MapPin className="w-5 h-5" /> Roteiro da viagem
              </h3>
              {destinationSummaryItems.length > 0 ? (
                <ol className="space-y-3">
                  {destinationSummaryItems.map((item) => (
                    <li key={item.id} className="flex gap-3">
                      <span
                        className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-accent/15 text-xs font-bold text-accent-foreground"
                        aria-hidden="true"
                      >
                        {item.order}
                      </span>
                      <div className="text-sm">
                        <p className="font-bold text-foreground">{item.place}</p>
                        <p className="text-muted-foreground">
                          {[item.timing, item.daysLabel].filter(Boolean).join(' · ')}
                        </p>
                        {item.landmarks.length > 0 && (
                          <p className="text-muted-foreground">{item.landmarks.join(' · ')}</p>
                        )}
                      </div>
                    </li>
                  ))}
                </ol>
              ) : (
                <p className="font-medium text-base text-muted-foreground">{destinationSummary}</p>
              )}
              <p className="mt-3 text-sm text-muted-foreground">
                Ano da viagem: {year} · Ritmo {paceLabel(itineraryPreferences.pace).toLowerCase()}
                {itineraryPreferences.interests.length > 0
                  && ` · ${itineraryPreferences.interests.join(', ')}`}
              </p>
            </div>
          </div>
        </div>

        <div className="mt-12 pt-8 border-t border-border/50">
          <h3 className="mb-8 flex items-center gap-2 text-xl font-display font-bold text-primary sm:text-2xl">
            <Star className="w-6 h-6 text-[hsl(var(--star))]" /> O Roteiro Mágico
            <span className="font-data text-sm font-bold text-muted-foreground">
              {pluralize(finalLandmarks.length, 'local selecionado', 'locais selecionados')}
            </span>
          </h3>

          <div className="space-y-8">
            {recommendedDays.length > 0 ? recommendedDays.map(day => (
              <div key={day.day} className="rounded-2xl border border-border/60 bg-background p-6">
                <h4 className="text-lg font-bold text-foreground mb-2 flex items-center gap-2">
                  <Navigation className="w-4 h-4 text-secondary" />
                  {day.title}
                </h4>
                <p className="text-sm text-muted-foreground mb-4">{day.theme}</p>
                <ul className="space-y-4">
                  {day.landmarks.map(landmark => (
                    <li key={landmark.id} className="flex flex-col border-l-2 border-accent/30 pl-4 py-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <strong className="text-foreground font-bold">{landmark.name}</strong>
                        <span className="rounded-full bg-muted px-2 py-0.5 text-xs font-bold text-muted-foreground">
                          {categoryLabelForAttraction(landmark)}
                        </span>
                      </div>
                      <span className="text-muted-foreground text-sm leading-relaxed mt-1 line-clamp-2">
                        {landmark.description}
                      </span>
                      <LandmarkActivities landmark={landmark} />
                    </li>
                  ))}
                </ul>
              </div>
            )) : Object.keys(groupedLandmarks).map(destId => {
              const destObj = parsedData.destinations.find(d => d.id === destId);
              const items = groupedLandmarks[destId];
              if (!destObj) return null;

              return (
                <div key={destId} className="rounded-2xl border border-border/60 bg-background p-6">
                  <h4 className="text-lg font-bold text-foreground mb-4 flex items-center gap-2">
                    <Navigation className="w-4 h-4 text-secondary" />
                    {destObj.city}, {destObj.country}
                  </h4>
                  <ul className="space-y-4">
                    {items.map(landmark => (
                      <li key={landmark.id} className="flex flex-col border-l-2 border-accent/30 pl-4 py-1">
                        <div className="flex flex-wrap items-center gap-2">
                          <strong className="text-foreground font-bold">{landmark.name}</strong>
                          <span className="rounded-full bg-muted px-2 py-0.5 text-xs font-bold text-muted-foreground">
                            {categoryLabelForAttraction(landmark)}
                          </span>
                        </div>
                        <span className="text-muted-foreground text-sm leading-relaxed mt-1 line-clamp-2">
                          {landmark.description}
                        </span>
                        <LandmarkActivities landmark={landmark} />
                      </li>
                    ))}
                  </ul>
                </div>
              );
            })}
            {recommendedDays.length > 0 && extraLandmarks.length > 0 && (
              <div className="rounded-2xl border border-border/60 bg-background p-6">
                <h4 className="text-lg font-bold text-foreground mb-4 flex items-center gap-2">
                  <Navigation className="w-4 h-4 text-secondary" />
                  Outras escolhas
                </h4>
                <ul className="space-y-4">
                  {extraLandmarks.map(landmark => (
                    <li key={landmark.id} className="flex flex-col border-l-2 border-accent/30 pl-4 py-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <strong className="text-foreground font-bold">{landmark.name}</strong>
                        <span className="rounded-full bg-muted px-2 py-0.5 text-xs font-bold text-muted-foreground">
                          {categoryLabelForAttraction(landmark)}
                        </span>
                      </div>
                      <span className="text-muted-foreground text-sm leading-relaxed mt-1 line-clamp-2">
                        {landmark.description}
                      </span>
                      <LandmarkActivities landmark={landmark} />
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>

        {/* "O primeiro olá" é a única página que entra ligada por padrão: quem
            não a revê aqui só descobre que existe quando o guia já está pronto. */}
        {flightVocabularyPages && flightVocabularyCountries.length > 0 && (
          <div className="mt-8 rounded-2xl border border-primary/25 bg-[hsl(var(--blush))] p-5 sm:p-6">
            <div className="flex items-start gap-4">
              <MessageCircleHeart className="mt-1 h-7 w-7 shrink-0 text-primary" aria-hidden="true" />
              <div>
                <h3 className="text-xl font-display font-bold text-foreground">
                  O primeiro olá, no idioma de cada país
                </h3>
                <p className="mt-1 text-sm font-medium text-muted-foreground">
                  Uma página abrindo cada país:{' '}
                  {flightVocabularyCountries
                    .map((item) => `${item.country} (${item.language})`)
                    .join(', ')}
                  .
                </p>
              </div>
            </div>
          </div>
        )}

        <div className="mt-8 rounded-2xl border border-secondary/25 bg-[hsl(var(--mint))] p-5 sm:p-6">
          <div className="flex items-start gap-4">
            <BookHeart className="mt-1 h-7 w-7 shrink-0 text-secondary" aria-hidden="true" />
            <div>
              <h3 className="text-xl font-display font-bold text-foreground">Minha melhor memória</h3>
              <p className="mt-1 text-sm font-medium text-muted-foreground">
                Página obrigatória depois dos passeios, com espaço para registrar a descoberta
                favorita, fazer um desenho, assinar e datar.
              </p>
            </div>
          </div>
          <div className="mt-5 flex items-start gap-4 border-t border-secondary/20 pt-5">
            <Plane className="mt-1 h-7 w-7 shrink-0 text-secondary" aria-hidden="true" />
            <div>
              <h3 className="text-xl font-display font-bold text-foreground">
                Hora de voltar para casa
              </h3>
              <p className="mt-1 text-sm font-medium text-muted-foreground">
                Página final obrigatória com a família no retorno e espaço para a criança escrever
                o que quer contar quando chegar em casa.
              </p>
            </div>
          </div>
        </div>
      </div>

      <div className="rounded-2xl border border-border/50 bg-card p-5 shadow-sm sm:p-8">
        <label className="flex cursor-pointer flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div className="flex items-start gap-4">
            <input
              type="checkbox"
              checked={restaurantRecommendationsExtra}
              onChange={(event) => setRestaurantRecommendationsExtra(event.target.checked)}
              className="mt-1 h-5 w-5 accent-primary"
            />
            <div>
              <h3 className="text-xl font-display font-bold text-secondary">
                {RESTAURANT_RECOMMENDATIONS_EXTRA.label}
              </h3>
              <p className="mt-1 text-sm font-medium text-muted-foreground">
                {RESTAURANT_RECOMMENDATIONS_EXTRA.description}
              </p>
            </div>
          </div>
          <span className="pill-flag pill-flag--mint text-sm">
            {RESTAURANT_RECOMMENDATIONS_EXTRA.price_label}
          </span>
        </label>
      </div>

      {/* Última barreira antes da gráfica: o guia é impresso com estes textos
          exatos, então a família confere a grafia uma vez e assume o "confere". */}
      <div className="rounded-2xl border border-primary/25 bg-primary/[0.04] p-5 shadow-sm sm:p-8">
        <div className="flex items-start gap-4">
          <PenLine className="mt-1 h-7 w-7 shrink-0 text-primary" aria-hidden="true" />
          <div>
            <h3 className="text-xl font-display font-bold text-foreground sm:text-2xl">
              Assim vai impresso
            </h3>
            <p className="mt-1 text-sm font-medium text-muted-foreground">
              Estes textos são copiados letra por letra para as páginas do livro.
              Depois de gerar, corrigir um nome exige refazer as páginas.
            </p>
          </div>
        </div>

        <dl className="mt-6 space-y-4 text-sm">
          <div className="rounded-xl bg-card p-4">
            <dt className="font-semibold text-muted-foreground">Na capa</dt>
            <dd className="mt-1 font-serif text-lg font-bold text-foreground">
              Família {familyName || '—'}
              {year ? <span className="text-muted-foreground"> · {year}</span> : null}
            </dd>
          </div>

          {(childNamesList.length > 0 || parentsNames) && (
            <div className="rounded-xl bg-card p-4">
              <dt className="font-semibold text-muted-foreground">
                Nomes da família
              </dt>
              <dd className="mt-1 font-medium text-foreground">
                {[...parentsList.filter(Boolean), ...childNamesList].join(' · ')}
              </dd>
            </div>
          )}

          {destinationSummaryItems.length > 0 && (
            <div className="rounded-xl bg-card p-4">
              <dt className="font-semibold text-muted-foreground">
                Paradas e datas
              </dt>
              <dd className="mt-1 space-y-1">
                {destinationSummaryItems.map((item) => (
                  <p key={item.id} className="font-medium text-foreground">
                    {item.place}
                    {item.timing && <span className="text-muted-foreground"> — {item.timing}</span>}
                  </p>
                ))}
              </dd>
            </div>
          )}

          {finalLandmarks.length > 0 && (
            <div className="rounded-xl bg-card p-4">
              <dt className="font-semibold text-muted-foreground">
                Pontos turísticos
              </dt>
              <dd className="mt-1 font-medium text-foreground">
                {finalLandmarks.map((landmark) => landmark.name).join(' · ')}
              </dd>
            </div>
          )}
        </dl>

        <div className="mt-6 flex flex-col gap-4 border-t border-primary/15 pt-5 sm:flex-row sm:items-center sm:justify-between">
          <label className="flex cursor-pointer items-start gap-3 text-sm font-bold text-foreground">
            <input
              type="checkbox"
              checked={printConfirmed}
              onChange={(event) => setPrintConfirmed(event.target.checked)}
              className="mt-0.5 h-5 w-5 shrink-0 accent-primary"
            />
            Confere: é assim que os nomes devem aparecer no livro.
          </label>
          <div className="flex shrink-0 gap-2">
            <Button
              type="button"
              variant="outline"
              onClick={() => setStep(1)}
              className="rounded-full px-5 py-5 text-sm font-bold"
            >
              Corrigir roteiro
            </Button>
            <Button
              type="button"
              variant="outline"
              onClick={() => setStep(4)}
              className="rounded-full px-5 py-5 text-sm font-bold"
            >
              Corrigir nomes
            </Button>
          </div>
        </div>
      </div>

      {/* Confiança no ponto da decisão: preço, ordem da geração e entrega
          aparecem juntos, imediatamente antes da ação de compra. */}
      <div className="mt-8 rounded-2xl border border-secondary/25 bg-[hsl(var(--mint))] p-5 sm:p-6">
        <h3 className="text-xl font-display font-bold text-foreground">O que acontece depois</h3>
        <ul className="mt-4 grid gap-4 text-left sm:grid-cols-3">
          <li className="flex items-start gap-3">
            <ShieldCheck className="mt-0.5 h-5 w-5 shrink-0 text-secondary" aria-hidden="true" />
            <p className="text-sm font-medium text-muted-foreground">
              {guideProduct?.enabled
                ? `${formatPrice(guideProduct.amount_minor, guideProduct.currency)} em compra única no ambiente seguro do Mercado Pago.`
                : 'Seu roteiro é salvo com segurança antes de criar qualquer imagem.'}
            </p>
          </li>
          <li className="flex items-start gap-3">
            <Camera className="mt-0.5 h-5 w-5 shrink-0 text-primary" aria-hidden="true" />
            <p className="text-sm font-medium text-muted-foreground">
              Você revisa e aprova a capa antes de criarmos o guia completo.
            </p>
          </li>
          <li className="flex items-start gap-3">
            <FileText className="mt-0.5 h-5 w-5 shrink-0 text-secondary" aria-hidden="true" />
            <p className="text-sm font-medium text-muted-foreground">
              O PDF A4 chega no e-mail da sua conta; não é preciso esperar no site.
            </p>
          </li>
        </ul>
      </div>

      <div className="flex justify-center pt-8">
        <Button
          onClick={handleGenerate}
          disabled={isGenerating || !printConfirmed}
          aria-describedby={printConfirmed ? undefined : 'print-confirmation-hint'}
          className="w-full max-w-md rounded-full px-6 py-6 text-base font-bold shadow-[0_10px_22px_-12px_hsl(217_56%_30%/0.55)] transition-all hover:-translate-y-1 disabled:opacity-70 disabled:hover:translate-y-0 sm:w-auto sm:px-12 sm:py-8 sm:text-xl"
        >
          {isGenerating ? (
            <><Loader2 className="w-6 h-6 animate-spin mr-3 inline-block" /> Preparando o checkout...</>
          ) : guideProduct?.enabled ? (
            <>
              <CreditCard className="mr-3 inline-block h-6 w-6" /> Comprar por{' '}
              {formatPrice(guideProduct.amount_minor, guideProduct.currency)}
            </>
          ) : (
            <><Sparkles className="w-6 h-6 mr-3 inline-block" /> Criar e revisar a capa</>
          )}
        </Button>
      </div>
      {!printConfirmed && (
        <p id="print-confirmation-hint" className="mt-4 text-center text-sm font-medium text-muted-foreground">
          Confirme acima que os nomes estão corretos para liberar a criação das páginas.
        </p>
      )}
      {isGenerating && (
        <p className="mt-4 text-center text-sm text-muted-foreground" role="status" aria-live="polite">
          Salvando seu roteiro antes de abrir o Mercado Pago. Nenhuma imagem será gerada sem sua confirmação nem antes da liberação do pagamento.
        </p>
      )}
    </div>
  );
};

export default Step5Review;
