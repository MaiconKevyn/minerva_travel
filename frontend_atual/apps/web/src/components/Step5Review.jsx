
import React, { useRef, useState } from 'react';
import { motion } from 'framer-motion';
import {
  Camera,
  Download,
  ExternalLink,
  Loader2,
  MapPin,
  Navigation,
  Sparkles,
  Star,
  Users,
} from 'lucide-react';
import { useConversationalGuide } from '@/contexts/ConversationalGuideContext.jsx';
import { Button } from '@/components/ui/button';
import {
  categoryLabelForAttraction,
  buildGuideItineraryPayload,
  createIdempotencyKey,
  downloadGuidePdf,
  fetchGuidePreviewHtml,
  generatePDF,
  RESTAURANT_RECOMMENDATIONS_EXTRA,
  selectGuideLandmarks,
  waitForGuideJob,
} from '@/utils/minerva-api.js';
import {
  deriveChildAges,
  deriveChildNames,
  PRIVACY_CONSENT_VERSION,
  serializeGuideDestinations,
} from '@/utils/guide-form.js';
import { toast } from 'sonner';
import confetti from 'canvas-confetti';

const Step5Review = () => {
  const {
    familyName,
    coverPhoto,
    coverPhotoUrl,
    destination,
    destinationsList,
    parsedData,
    selectedLandmarks,
    childrenList,
    parentsList,
    expectedCoverFamilyMemberCount,
    photoProcessingConsent,
    privacyConsentAt,
    itineraryMode,
    itineraryPreferences,
    recommendedItinerary,
    restaurantRecommendationsExtra,
    setRestaurantRecommendationsExtra,
    year
  } = useConversationalGuide();

  const [isGenerating, setIsGenerating] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);
  const [pdfUrl, setPdfUrl] = useState('');
  const [pdfFilename, setPdfFilename] = useState('guia-minerva-travel.pdf');
  const [coverStatus, setCoverStatus] = useState(null);
  const [isRetrievingPdf, setIsRetrievingPdf] = useState(false);
  const [generationStatus, setGenerationStatus] = useState('');
  const [previewHtml, setPreviewHtml] = useState('');
  const [isLoadingPreview, setIsLoadingPreview] = useState(false);
  const [previewError, setPreviewError] = useState('');
  const generationIdempotencyKey = useRef(null);

  const loadGuidePreview = async (previewUrl) => {
    if (!previewUrl) return;
    setIsLoadingPreview(true);
    setPreviewError('');
    try {
      setPreviewHtml(await fetchGuidePreviewHtml(previewUrl));
    } catch (error) {
      console.error('Erro ao carregar a prévia do guia:', error);
      setPreviewError(error.message || 'Não foi possível carregar a prévia.');
    } finally {
      setIsLoadingPreview(false);
    }
  };

  // Derive the rich data from the IDs
  const finalLandmarks = selectGuideLandmarks(parsedData.landmarks, selectedLandmarks);
  const childNamesList = deriveChildNames(childrenList);
  const childrenNames = childNamesList.join(', ');
  const childrenAges = deriveChildAges(childrenList);
  const destinationSummary = serializeGuideDestinations(destinationsList) || destination;
  const parentsNames = parentsList.join(', ');
  const recommendedDays = (recommendedItinerary?.days || [])
    .map((day) => ({
      ...day,
      landmarks: finalLandmarks.filter((landmark) => landmark.itinerary_day === day.day),
    }))
    .filter((day) => day.landmarks.length > 0);
  const extraLandmarks = finalLandmarks.filter((landmark) => !landmark.itinerary_day);

  const handleGenerate = async () => {
    setIsGenerating(true);
    try {
      const itinerary = buildGuideItineraryPayload({
        itineraryMode,
        destinationsList,
        itineraryPreferences,
        recommendedDays,
        extraLandmarks,
      });
      const guideData = {
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
        itinerary,
        restaurantRecommendationsExtra,
      };

      generationIdempotencyKey.current ||= createIdempotencyKey();
      const submitted = await generatePDF(guideData, {
        idempotencyKey: generationIdempotencyKey.current,
      });
      const result = submitted.job_id
        ? await waitForGuideJob(submitted.job_id, {
          onUpdate: (job) => {
            const stage = String(job.stage || 'preparando').replaceAll('_', ' ');
            setGenerationStatus(`Etapa: ${stage} (${job.progress || 0}%).`);
          },
        })
        : submitted;

      if (result.download_url) {
        setPdfUrl(result.download_url);
        setPdfFilename(result.filename || 'guia-minerva-travel.pdf');
        setCoverStatus(result.cover_status || null);
        setIsSuccess(true);
        loadGuidePreview(result.preview_url);
        toast.success('Guia de viagem gerado com sucesso!');
        if (result.cover_status?.fallback_used) {
          toast.info('Usamos uma capa segura com a foto original para preservar todos na imagem.');
        }

        confetti({
          particleCount: 100,
          spread: 70,
          origin: { y: 0.6 },
          colors: ['#f1613b', '#489cc8', '#69b482', '#fdfbf7']
        });
      } else {
        throw new Error('URL de download não encontrada na resposta.');
      }

    } catch (error) {
      console.error(error);
      toast.error('Não foi possível gerar o PDF.');
    } finally {
      setIsGenerating(false);
      setGenerationStatus('');
    }
  };

  const handlePdfAction = async ({ open = false } = {}) => {
    setIsRetrievingPdf(true);
    try {
      const { blob, filename } = await downloadGuidePdf(pdfUrl);
      const objectUrl = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = objectUrl;
      if (open) {
        link.target = '_blank';
        link.rel = 'noopener noreferrer';
      } else {
        link.download = filename || pdfFilename;
      }
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.setTimeout(() => URL.revokeObjectURL(objectUrl), 30_000);
    } catch (error) {
      toast.error(error.message || 'Não foi possível acessar o PDF.');
    } finally {
      setIsRetrievingPdf(false);
    }
  };

  if (isSuccess) {
    return (
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        className="w-full max-w-4xl mx-auto text-center space-y-8 py-12"
      >
        <div className="w-24 h-24 bg-accent/20 rounded-full flex items-center justify-center mx-auto text-accent">
          <Sparkles className="w-12 h-12" />
        </div>
        <h2 className="text-4xl md:text-5xl font-serif font-bold text-foreground">
          Guia Gerado com Sucesso!
        </h2>
        <p className="text-xl text-muted-foreground font-medium">
          O Livro de Aventuras da Família {familyName} está pronto. Confira cada página abaixo
          antes de baixar.
        </p>
        {coverStatus?.fallback_used && (
          <p className="rounded-2xl border border-border/70 bg-card px-5 py-4 text-sm text-muted-foreground">
            A capa foi protegida com a foto original porque a ilustração não pôde ser validada com segurança.
          </p>
        )}

        {/* Prévia página a página: o MESMO HTML que o WeasyPrint transforma em PDF. */}
        <div className="rounded-[2rem] border-2 border-border/70 bg-card p-3 text-left shadow-sm sm:p-4">
          <div className="mb-3 flex items-center justify-between px-2">
            <p className="text-sm font-bold uppercase tracking-[0.2em] text-muted-foreground">
              Prévia do guia
            </p>
            {isLoadingPreview && <Loader2 className="h-4 w-4 animate-spin text-primary" />}
          </div>
          {previewHtml ? (
            <iframe
              title="Prévia do guia"
              sandbox=""
              srcDoc={previewHtml}
              className="h-[70vh] w-full rounded-2xl border border-border/60 bg-white"
            />
          ) : previewError ? (
            <p className="rounded-2xl bg-destructive/10 px-4 py-6 text-center text-sm font-bold text-destructive">
              {previewError}
            </p>
          ) : (
            <p className="px-4 py-10 text-center text-sm font-medium text-muted-foreground">
              {isLoadingPreview
                ? 'Montando a prévia com todas as imagens geradas...'
                : 'A prévia ficará disponível em instantes.'}
            </p>
          )}
        </div>

        <div className="pt-4 flex flex-col sm:flex-row gap-4 justify-center">
          <Button
            onClick={() => handlePdfAction({ open: true })}
            disabled={isRetrievingPdf}
            variant="outline"
            className="rounded-full px-10 py-6 font-bold text-lg hover:-translate-y-1 transition-all"
          >
            {isRetrievingPdf ? (
              <Loader2 className="w-5 h-5 mr-2 animate-spin" />
            ) : (
              <ExternalLink className="w-5 h-5 mr-2" />
            )}
            Abrir PDF
          </Button>
          <Button
            onClick={() => handlePdfAction()}
            disabled={isRetrievingPdf}
            className="rounded-full px-10 py-6 bg-primary hover:bg-primary/90 text-white font-bold text-lg shadow-lg hover:-translate-y-1 transition-all"
          >
            <Download className="w-5 h-5 mr-2" /> Baixar PDF
          </Button>
          <Button
            onClick={() => window.location.href = '/'}
            variant="outline"
            className="rounded-full px-10 py-6 font-bold text-lg hover:-translate-y-1 transition-all"
          >
            Voltar ao Início
          </Button>
        </div>
      </motion.div>
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

  return (
    <div className="w-full max-w-4xl mx-auto space-y-12">
      <div className="text-center space-y-4">
        <h2 className="text-3xl md:text-4xl font-serif font-bold text-foreground">
          Perfeito! Aqui está o resumo do seu roteiro
        </h2>
        <p className="text-lg text-muted-foreground font-medium">Revise as informações antes de gerarmos o PDF oficial.</p>
      </div>

      <div className="rounded-[2rem] border-2 border-border/50 bg-card p-5 shadow-storybook dark:border-slate-700 dark:bg-slate-800 sm:p-8 md:rounded-[40px] md:p-12">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-10">

          <div className="space-y-4">
            <h3 className="text-xl font-serif font-bold flex items-center gap-2 text-primary">
              <Camera className="w-5 h-5" /> A Capa
            </h3>
            {coverPhotoUrl ? (
              <>
                <div className="aspect-[4/3] rounded-3xl overflow-hidden shadow-md">
                  <img src={coverPhotoUrl} alt="Capa do Guia" className="w-full h-full object-cover" />
                </div>
                {expectedCoverFamilyMemberCount > 0 && (
                  <p className="text-sm text-muted-foreground">
                    Pessoas esperadas na capa: {expectedCoverFamilyMemberCount}
                  </p>
                )}
              </>
            ) : (
              <div className="aspect-[4/3] rounded-3xl bg-muted flex items-center justify-center border-2 border-dashed border-border">
                <p className="text-muted-foreground font-medium">Sem foto de capa</p>
              </div>
            )}
          </div>

          <div className="space-y-8">
            <div>
              <h3 className="text-xl font-serif font-bold flex items-center gap-2 text-secondary mb-3">
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
              <h3 className="text-xl font-serif font-bold flex items-center gap-2 text-accent mb-3">
                <MapPin className="w-5 h-5" /> Resumo do Destino
              </h3>
              <p className="whitespace-pre-line font-medium text-base text-muted-foreground line-clamp-5 italic">"{destinationSummary}"</p>
              <p className="text-sm text-muted-foreground mt-2">Ano: {year}</p>
              <p className="text-sm text-muted-foreground mt-1">
                Ritmo: {itineraryPreferences.pace} · Programas: {itineraryPreferences.interests.length > 0 ? itineraryPreferences.interests.join(', ') : 'sem categorias específicas'}
              </p>
            </div>
          </div>
        </div>

        <div className="mt-12 pt-8 border-t border-border/50">
          <h3 className="mb-8 flex items-center gap-2 text-xl font-serif font-bold text-primary sm:text-2xl">
            <Star className="w-6 h-6" /> O Roteiro Mágico ({finalLandmarks.length} locais selecionados)
          </h3>

          <div className="space-y-8">
            {recommendedDays.length > 0 ? recommendedDays.map(day => (
              <div key={day.day} className="bg-background rounded-3xl p-6 border border-border/60">
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
                    </li>
                  ))}
                </ul>
              </div>
            )) : Object.keys(groupedLandmarks).map(destId => {
              const destObj = parsedData.destinations.find(d => d.id === destId);
              const items = groupedLandmarks[destId];
              if (!destObj) return null;

              return (
                <div key={destId} className="bg-background rounded-3xl p-6 border border-border/60">
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
                      </li>
                    ))}
                  </ul>
                </div>
              );
            })}
            {recommendedDays.length > 0 && extraLandmarks.length > 0 && (
              <div className="bg-background rounded-3xl p-6 border border-border/60">
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
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="rounded-[2rem] border-2 border-border/50 bg-card p-5 shadow-storybook dark:border-slate-700 dark:bg-slate-800 sm:p-8">
        <label className="flex cursor-pointer flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div className="flex items-start gap-4">
            <input
              type="checkbox"
              checked={restaurantRecommendationsExtra}
              onChange={(event) => setRestaurantRecommendationsExtra(event.target.checked)}
              className="mt-1 h-5 w-5 accent-primary"
            />
            <div>
              <h3 className="text-xl font-serif font-bold text-secondary">
                {RESTAURANT_RECOMMENDATIONS_EXTRA.label}
              </h3>
              <p className="mt-1 text-sm font-medium text-muted-foreground">
                {RESTAURANT_RECOMMENDATIONS_EXTRA.description}
              </p>
            </div>
          </div>
          <span className="rounded-full bg-secondary/10 px-4 py-2 text-sm font-bold text-secondary">
            {RESTAURANT_RECOMMENDATIONS_EXTRA.price_label}
          </span>
        </label>
      </div>

      <div className="flex justify-center pt-8">
        <Button
          onClick={handleGenerate}
          disabled={isGenerating}
          className="w-full max-w-md rounded-full bg-primary px-6 py-6 text-base font-bold text-white shadow-[0_8px_30px_rgb(241,97,59,0.3)] transition-all hover:-translate-y-1 hover:bg-primary/90 disabled:opacity-70 disabled:hover:translate-y-0 sm:w-auto sm:px-12 sm:py-8 sm:text-xl"
        >
          {isGenerating ? (
            <><Loader2 className="w-6 h-6 animate-spin mr-3 inline-block" /> Criando a Magia...</>
          ) : (
            <><Sparkles className="w-6 h-6 mr-3 inline-block" /> Gerar PDF do Guia</>
          )}
        </Button>
      </div>
      {isGenerating && (
        <p className="mt-4 text-center text-sm text-muted-foreground" role="status" aria-live="polite">
          {generationStatus || 'Enviamos seu guia para a fila de geração.'}
        </p>
      )}
    </div>
  );
};

export default Step5Review;
