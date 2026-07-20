
import React, { useState } from 'react';
import { motion } from 'framer-motion';
import {
  Camera,
  Loader2,
  MapPin,
  Navigation,
  Sparkles,
  Star,
  Users,
  BookHeart,
  Plane,
  Puzzle,
} from 'lucide-react';
import { useConversationalGuide } from '@/contexts/ConversationalGuideContext.jsx';
import { Button } from '@/components/ui/button';
import {
  categoryLabelForAttraction,
  buildGuideItineraryPayload,
  createGuideBuilder,
  RESTAURANT_RECOMMENDATIONS_EXTRA,
  selectGuideLandmarks,
} from '@/utils/minerva-api.js';
import {
  deriveChildAges,
  deriveChildNames,
  PRIVACY_CONSENT_VERSION,
  serializeGuideDestinations,
} from '@/utils/guide-form.js';
import GuideAssembly from '@/components/GuideAssembly.jsx';
import { activityOptionForType } from '@/utils/landmark-activities.js';
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
    setRestaurantRecommendationsExtra,
    year
  } = useConversationalGuide();

  const [isGenerating, setIsGenerating] = useState(false);
  const [builderSession, setBuilderSession] = useState(null);

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
    };
  };

  const handleGenerate = async () => {
    setIsGenerating(true);
    const guideData = buildGuideData();
    try {
      const session = await createGuideBuilder(guideData);
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
        <h2 className="text-3xl md:text-4xl font-serif font-bold text-foreground">
          Perfeito! Aqui está o resumo do seu roteiro
        </h2>
        <p className="text-lg text-muted-foreground font-medium">Revise as informações antes de gerarmos o guia ilustrado da família.</p>
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
                        <LandmarkActivities landmark={landmark} />
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
                      <LandmarkActivities landmark={landmark} />
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>

        <div className="mt-8 rounded-3xl border-2 border-secondary/25 bg-secondary/5 p-5 sm:p-6">
          <div className="flex items-start gap-4">
            <BookHeart className="mt-1 h-7 w-7 shrink-0 text-secondary" aria-hidden="true" />
            <div>
              <h3 className="text-xl font-serif font-bold text-foreground">Minha melhor memória</h3>
              <p className="mt-1 text-sm font-medium text-muted-foreground">
                Página obrigatória depois dos passeios, com espaço para registrar a descoberta
                favorita, fazer um desenho, assinar e datar.
              </p>
            </div>
          </div>
          <div className="mt-5 flex items-start gap-4 border-t border-secondary/20 pt-5">
            <Plane className="mt-1 h-7 w-7 shrink-0 text-secondary" aria-hidden="true" />
            <div>
              <h3 className="text-xl font-serif font-bold text-foreground">
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
            <><Loader2 className="w-6 h-6 animate-spin mr-3 inline-block" /> Preparando as páginas...</>
          ) : (
            <><Sparkles className="w-6 h-6 mr-3 inline-block" /> Começar pelas páginas</>
          )}
        </Button>
      </div>
      {isGenerating && (
        <p className="mt-4 text-center text-sm text-muted-foreground" role="status" aria-live="polite">
          Preparando a ordem das páginas. Nenhuma imagem será gerada sem sua confirmação.
        </p>
      )}
    </div>
  );
};

export default Step5Review;
