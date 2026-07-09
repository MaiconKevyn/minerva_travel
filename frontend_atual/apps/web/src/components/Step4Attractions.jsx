import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import {
  AlertCircle,
  ArrowLeft,
  ArrowRight,
  Loader2,
  Map as MapIcon,
  RefreshCcw,
} from 'lucide-react';
import { useConversationalGuide } from '@/contexts/ConversationalGuideContext.jsx';
import { Button } from '@/components/ui/button';
import {
  defaultSelectedLandmarksForMode,
  buildDiscoverItineraryPayload,
  buildStructuredLandmarksPayload,
  categoryLabelForAttraction,
  discoverItinerary,
  filterAttractionsByCategory,
  mergeDestinationSuggestions,
  mergeLandmarkSuggestions,
  mergeResolvedLandmarkLocations,
  mapParsedLandmarksToParsedData,
  mapRecommendationToParsedData,
  missingSelectedMapLandmarks,
  parseLandmarks,
  primaryAttractionCategory,
  resolveStructuredLandmarks,
  splitLandmarksBySource,
  splitQuickSuggestionLandmarks,
} from '@/utils/minerva-api.js';
import LandmarkCard from './LandmarkCard.jsx';
import DestinationGroup from './DestinationGroup.jsx';
import MapOverviewModal from './MapOverviewModal.jsx';

const Step4Attractions = () => {
  const {
    destination,
    destinationsList,
    childrenList,
    itineraryMode: guideItineraryMode,
    parsedData,
    setParsedData,
    selectedLandmarks,
    setSelectedLandmarks,
    toggleLandmarkSelection,
    recommendedItinerary,
    setRecommendedItinerary,
    itineraryPreferences,
    isLoadingLandmarks,
    setIsLoadingLandmarks,
    hasSearchedLandmarks,
    setHasSearchedLandmarks,
    nextStep,
    goBack,
  } = useConversationalGuide();

  const knownItineraryMode = guideItineraryMode === 'known';

  const [error, setError] = useState(null);
  const [loadingMode, setLoadingMode] = useState('quick');
  const [resultMode, setResultMode] = useState('quick');
  const [isMapOpen, setIsMapOpen] = useState(false);
  const [isMapExploringMore, setIsMapExploringMore] = useState(false);
  const [mapExploreError, setMapExploreError] = useState('');
  const [mapExploreNotice, setMapExploreNotice] = useState('');
  const [isResolvingMapLocations, setIsResolvingMapLocations] = useState(false);
  const [mapLocationError, setMapLocationError] = useState('');
  const [mapLocationNotice, setMapLocationNotice] = useState('');
  const [activeCategory, setActiveCategory] = useState('all');
  const autoLoadedDestinationRef = useRef('');

  const applyParsedResult = useCallback((mapped, mode, itinerary = null) => {
    setParsedData({
      destinations: mapped.destinations,
      landmarks: mapped.landmarks,
    });
    setSelectedLandmarks(defaultSelectedLandmarksForMode(mapped, mode));
    setRecommendedItinerary(itinerary);
    setResultMode(mode);
    setHasSearchedLandmarks(true);
  }, [
    setHasSearchedLandmarks,
    setParsedData,
    setRecommendedItinerary,
    setSelectedLandmarks,
  ]);

  const loadManualMappedLandmarks = useCallback(async () => {
    const parsedLandmarks = await parseLandmarks(destination);
    const mapped = mapParsedLandmarksToParsedData(parsedLandmarks);

    if (mapped.landmarks.length === 0) {
      throw new Error('Nao encontrei pontos turisticos claros no roteiro informado.');
    }

    return mapped;
  }, [destination]);

  const processManualAttractions = useCallback(async () => {
    if (!destination.trim()) return;

    setLoadingMode('manual');
    setIsLoadingLandmarks(true);
    setError(null);

    try {
      const mapped = await loadManualMappedLandmarks();

      applyParsedResult(mapped, 'manual', null);
    } catch (err) {
      console.error('Error parsing manual landmarks:', err);
      setError(err.message || 'Nao foi possivel organizar o roteiro informado.');
    } finally {
      setIsLoadingLandmarks(false);
    }
  }, [
    applyParsedResult,
    destination,
    loadManualMappedLandmarks,
    setIsLoadingLandmarks,
  ]);

  const processKnownItinerary = useCallback(async () => {
    const payload = buildStructuredLandmarksPayload({ destinationsList });
    if (payload.destinations.length === 0) return;

    setLoadingMode('manual');
    setIsLoadingLandmarks(true);
    setError(null);

    try {
      const data = await resolveStructuredLandmarks(payload);
      const mapped = mapParsedLandmarksToParsedData(data);

      if (mapped.landmarks.length === 0) {
        throw new Error('Nao conseguimos organizar os pontos turisticos informados.');
      }

      applyParsedResult(mapped, 'manual', null);
    } catch (err) {
      console.error('Error resolving structured landmarks:', err);
      setError(err.message || 'Nao foi possivel organizar os pontos turisticos informados.');
    } finally {
      setIsLoadingLandmarks(false);
    }
  }, [
    applyParsedResult,
    destinationsList,
    setIsLoadingLandmarks,
  ]);

  const processAttractions = useCallback(async ({
    mode = 'itinerary',
    allowManualFallback = false,
  } = {}) => {
    if (!destination.trim()) return;

    setLoadingMode(mode === 'quick' ? 'quick' : 'suggestion');
    setIsLoadingLandmarks(true);
    setError(null);

    try {
      const itinerary = await discoverItinerary(buildDiscoverItineraryPayload({
        destination,
        destinationsList,
        itineraryPreferences,
        childrenList,
      }));
      const mapped = mapRecommendationToParsedData(itinerary, null);

      applyParsedResult(mapped, mode, itinerary);
    } catch (err) {
      if (allowManualFallback) {
        try {
          const mapped = await loadManualMappedLandmarks();
          applyParsedResult(mapped, 'manual', null);
          return;
        } catch (manualErr) {
          console.error('Error parsing manual landmarks after suggestion failure:', manualErr);
        }
      }

      console.error('Error fetching landmarks:', err);
      setError(err.message || 'Nao foi possivel montar o roteiro.');
    } finally {
      setIsLoadingLandmarks(false);
    }
  }, [
    applyParsedResult,
    destination,
    destinationsList,
    childrenList,
    itineraryPreferences.days,
    itineraryPreferences.interests,
    itineraryPreferences.pace,
    loadManualMappedLandmarks,
    setIsLoadingLandmarks,
  ]);

  const exploreMoreMapPlaces = useCallback(async () => {
    if (!destination.trim() || isMapExploringMore) return;

    setIsMapExploringMore(true);
    setMapExploreError('');
    setMapExploreNotice('');

    try {
      const broaderInterests = [
        ...new Set([
          ...itineraryPreferences.interests,
          'parques',
          'pracas',
          'teatros',
          'museus',
          'arte',
          'ar livre',
          'lojas locais',
          'familia',
          'historia',
          'comida',
          'animais',
          'rio',
          'education',
        ]),
      ].slice(0, 12);

      const payload = buildDiscoverItineraryPayload({
        destination,
        destinationsList,
        itineraryPreferences: {
          ...itineraryPreferences,
          interests: broaderInterests,
          pace: 'full',
        },
        childrenList,
      });
      const itinerary = await discoverItinerary({
        ...payload,
        days: Math.max(Number(payload.days) || 1, 3),
      });
      const mapped = mapRecommendationToParsedData(itinerary, null);
      const existingIds = new Set(parsedData.landmarks.map((landmark) => landmark.id));
      const newItemsCount = mapped.landmarks.filter(
        (landmark) => landmark?.id && !existingIds.has(landmark.id)
      ).length;

      setParsedData((prev) => ({
        destinations: mergeDestinationSuggestions(prev.destinations, mapped.destinations),
        landmarks: mergeLandmarkSuggestions(prev.landmarks, mapped.landmarks),
      }));
      setHasSearchedLandmarks(true);
      setMapExploreNotice(
        newItemsCount > 0
          ? `${newItemsCount} ${newItemsCount === 1 ? 'novo ponto encontrado' : 'novos pontos encontrados'} para considerar.`
          : 'Nao encontramos pontos novos agora. Tente ajustar as preferencias ou detalhar mais o destino.'
      );
    } catch (err) {
      console.error('Error exploring more map places:', err);
      setMapExploreError(err.message || 'Nao foi possivel buscar mais pontos agora.');
    } finally {
      setIsMapExploringMore(false);
    }
  }, [
    destination,
    destinationsList,
    childrenList,
    isMapExploringMore,
    itineraryPreferences.days,
    itineraryPreferences.interests,
    parsedData.landmarks,
    setHasSearchedLandmarks,
    setParsedData,
  ]);

  const retryResolveMapLocations = useCallback(async () => {
    if (!destination.trim() || isResolvingMapLocations) return;

    setIsResolvingMapLocations(true);
    setMapLocationError('');
    setMapLocationNotice('');

    try {
      const mapped = knownItineraryMode
        ? mapParsedLandmarksToParsedData(
            await resolveStructuredLandmarks(buildStructuredLandmarksPayload({ destinationsList }))
          )
        : await loadManualMappedLandmarks();
      const mergedLandmarks = mergeResolvedLandmarkLocations(
        parsedData.landmarks,
        mapped.landmarks
      );
      const missingBefore = missingSelectedMapLandmarks(parsedData.landmarks, selectedLandmarks);
      const missingAfter = missingSelectedMapLandmarks(mergedLandmarks, selectedLandmarks);
      const resolvedCount = Math.max(0, missingBefore.length - missingAfter.length);

      setParsedData((prev) => ({
        destinations: mergeDestinationSuggestions(prev.destinations, mapped.destinations),
        landmarks: mergeResolvedLandmarkLocations(prev.landmarks, mapped.landmarks),
      }));
      setMapLocationNotice(
        resolvedCount > 0
          ? `${resolvedCount} ${resolvedCount === 1 ? 'local confirmado foi localizado' : 'locais confirmados foram localizados'} no mapa.`
          : 'Tentamos novamente, mas alguns locais ainda nao retornaram coordenadas.'
      );
    } catch (err) {
      console.error('Error resolving confirmed map locations:', err);
      setMapLocationError(err.message || 'Nao foi possivel validar os locais no mapa agora.');
    } finally {
      setIsResolvingMapLocations(false);
    }
  }, [
    destination,
    destinationsList,
    isResolvingMapLocations,
    knownItineraryMode,
    loadManualMappedLandmarks,
    parsedData.landmarks,
    selectedLandmarks,
    setParsedData,
  ]);

  useEffect(() => {
    const trimmedDestination = destination.trim();

    if (
      !trimmedDestination ||
      hasSearchedLandmarks ||
      isLoadingLandmarks ||
      error ||
      autoLoadedDestinationRef.current === trimmedDestination
    ) {
      return;
    }

    autoLoadedDestinationRef.current = trimmedDestination;
    if (knownItineraryMode) {
      processKnownItinerary();
    } else {
      processAttractions({ mode: 'quick', allowManualFallback: true });
    }
  }, [
    destination,
    error,
    hasSearchedLandmarks,
    isLoadingLandmarks,
    knownItineraryMode,
    processAttractions,
    processKnownItinerary,
  ]);

  const selectedCount = selectedLandmarks.length;
  const missingMapLandmarks = missingSelectedMapLandmarks(parsedData.landmarks, selectedLandmarks);
  const hasMissingMapLocations = missingMapLandmarks.length > 0;
  const confirmedWithMapCount = Math.max(0, selectedCount - missingMapLandmarks.length);
  const itineraryMode = Boolean(recommendedItinerary?.days?.length && resultMode === 'itinerary');
  const manualMode = resultMode === 'manual';
  const quickSections = splitLandmarksBySource(parsedData.landmarks);
  const itinerarySections = splitQuickSuggestionLandmarks(parsedData.landmarks);
  const alternatives = itinerarySections.alternatives;
  const categoryFilters = useMemo(() => {
    const categories = parsedData.landmarks
      .map((landmark) => primaryAttractionCategory(landmark))
      .filter(Boolean);
    return [...new Set(categories)];
  }, [parsedData.landmarks]);

  useEffect(() => {
    if (activeCategory !== 'all' && !categoryFilters.includes(activeCategory)) {
      setActiveCategory('all');
    }
  }, [activeCategory, categoryFilters]);

  const renderCategoryFilters = () => {
    if (categoryFilters.length <= 1) {
      return null;
    }

    const categoryCount = (category) =>
      filterAttractionsByCategory(parsedData.landmarks, category).length;

    return (
      <div className="flex flex-wrap justify-center gap-2">
        <button
          type="button"
          onClick={() => setActiveCategory('all')}
          className={`rounded-full border px-4 py-2 text-sm font-bold transition-colors ${
            activeCategory === 'all'
              ? 'border-primary bg-primary text-white'
              : 'border-border bg-card text-muted-foreground hover:border-primary/60 hover:text-primary'
          }`}
        >
          Todas ({parsedData.landmarks.length})
        </button>
        {categoryFilters.map((category) => (
          <button
            key={category}
            type="button"
            onClick={() => setActiveCategory(category)}
            className={`rounded-full border px-4 py-2 text-sm font-bold transition-colors ${
              activeCategory === category
                ? 'border-secondary bg-secondary text-white'
                : 'border-border bg-card text-muted-foreground hover:border-secondary/60 hover:text-secondary'
            }`}
          >
            {categoryLabelForAttraction(category)} ({categoryCount(category)})
          </button>
        ))}
      </div>
    );
  };

  const renderItineraryDays = () => (
    <div className="space-y-10">
      {recommendedItinerary.days.map((day) => {
        const dayLandmarks = filterAttractionsByCategory(
          parsedData.landmarks.filter(
            (landmark) => !landmark.is_alternative && landmark.itinerary_day === day.day
          ),
          activeCategory
        );

        if (dayLandmarks.length === 0) return null;

        return (
          <section key={day.day} className="space-y-5">
            <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
              <div>
                <p className="text-sm font-bold uppercase tracking-[0.2em] text-primary">
                  Dia {day.day}
                </p>
                <h3 className="text-2xl md:text-3xl font-serif font-bold text-foreground">
                  {day.title}
                </h3>
                <p className="text-muted-foreground font-medium max-w-2xl">
                  {day.theme}
                </p>
              </div>
              <div className="rounded-full bg-muted px-4 py-2 text-sm font-bold text-muted-foreground w-fit">
                {dayLandmarks.filter((landmark) => selectedLandmarks.includes(landmark.id)).length} selecionados
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
              {dayLandmarks.map((landmark, lIdx) => (
                <LandmarkCard
                  key={landmark.id}
                  landmark={landmark}
                  destination={{ city: landmark.city, country: landmark.country }}
                  index={lIdx}
                  isSelected={selectedLandmarks.includes(landmark.id)}
                  onToggle={toggleLandmarkSelection}
                />
              ))}
            </div>
          </section>
        );
      })}

      {alternatives.length > 0 && (
        <section className="pt-6 space-y-5 border-t border-border/60">
          <div>
            <p className="text-sm font-bold uppercase tracking-[0.2em] text-secondary">
              Outras opcoes
            </p>
            <h3 className="text-2xl md:text-3xl font-serif font-bold text-foreground">
              Trocas e extras para o roteiro
            </h3>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
            {filterAttractionsByCategory(alternatives, activeCategory).slice(0, 12).map((landmark, lIdx) => (
              <LandmarkCard
                key={landmark.id}
                landmark={landmark}
                destination={{ city: landmark.city, country: landmark.country }}
                index={lIdx}
                isSelected={selectedLandmarks.includes(landmark.id)}
                onToggle={toggleLandmarkSelection}
              />
            ))}
          </div>
        </section>
      )}
    </div>
  );

  const renderQuickSuggestionCards = () => (
    <div className="space-y-12">
      {filterAttractionsByCategory(quickSections.mentioned, activeCategory).length > 0 && (
        <section className="space-y-5">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <p className="text-sm font-bold uppercase tracking-[0.2em] text-primary">
                Locais citados por voce
              </p>
              <h3 className="text-2xl md:text-3xl font-serif font-bold text-foreground">
                Pontos que ja estavam no seu roteiro
              </h3>
            </div>
            <div className="rounded-full bg-muted px-4 py-2 text-sm font-bold text-muted-foreground w-fit">
              {filterAttractionsByCategory(quickSections.mentioned, activeCategory)
                .filter((landmark) => selectedLandmarks.includes(landmark.id)).length} selecionados
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
            {filterAttractionsByCategory(quickSections.mentioned, activeCategory).map((landmark, lIdx) => (
              <LandmarkCard
                key={landmark.id}
                landmark={landmark}
                destination={{ city: landmark.city, country: landmark.country }}
                index={lIdx}
                isSelected={selectedLandmarks.includes(landmark.id)}
                onToggle={toggleLandmarkSelection}
              />
            ))}
          </div>
        </section>
      )}

      {filterAttractionsByCategory(quickSections.suggested, activeCategory).length > 0 && (
        <section className="pt-6 space-y-5 border-t border-border/60">
          <div>
            <p className="text-sm font-bold uppercase tracking-[0.2em] text-secondary">
              Sugestoes para a familia
            </p>
            <h3 className="text-2xl md:text-3xl font-serif font-bold text-foreground">
              Locais que podem combinar com a viagem
            </h3>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
            {filterAttractionsByCategory(quickSections.suggested, activeCategory).slice(0, 12).map((landmark, lIdx) => (
              <LandmarkCard
                key={landmark.id}
                landmark={landmark}
                destination={{ city: landmark.city, country: landmark.country }}
                index={lIdx}
                isSelected={selectedLandmarks.includes(landmark.id)}
                onToggle={toggleLandmarkSelection}
              />
            ))}
          </div>
        </section>
      )}
    </div>
  );

  const renderManualGroups = () => (
    <div className="space-y-16">
      {parsedData.destinations.map((dest, dIdx) => {
        const destLandmarks = filterAttractionsByCategory(
          parsedData.landmarks.filter((landmark) => landmark.destination_id === dest.id),
          activeCategory
        );

        if (destLandmarks.length === 0) return null;

        return (
          <DestinationGroup key={dest.id} destination={dest} index={dIdx}>
            {destLandmarks.map((landmark, lIdx) => (
              <LandmarkCard
                key={landmark.id}
                landmark={landmark}
                destination={dest}
                index={lIdx}
                isSelected={selectedLandmarks.includes(landmark.id)}
                onToggle={toggleLandmarkSelection}
              />
            ))}
          </DestinationGroup>
        );
      })}
    </div>
  );

  return (
    <div className="w-full max-w-5xl mx-auto flex flex-col min-h-[60vh] py-4">
      <AnimatePresence mode="wait">
        {isLoadingLandmarks ? (
          <motion.div
            key="loading"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="flex flex-col items-center justify-center py-32 space-y-8 text-center"
          >
            <div className="relative">
              <div className="w-24 h-24 rounded-full border-4 border-muted flex items-center justify-center">
                <Loader2 className="w-12 h-12 animate-spin text-primary" />
              </div>
              <motion.div
                className="absolute inset-0 rounded-full border-4 border-primary border-t-transparent"
                animate={{ rotate: 360 }}
                transition={{ duration: 1.5, repeat: Infinity, ease: 'linear' }}
              />
            </div>
            <div className="space-y-3">
              <h2 className="text-3xl font-serif font-bold text-foreground">
                {loadingMode === 'manual'
                  ? 'Organizando seu roteiro...'
                  : loadingMode === 'quick'
                    ? 'Buscando locais para sua viagem...'
                    : 'Montando seu roteiro...'}
              </h2>
              <p className="text-lg text-muted-foreground font-medium animate-pulse">
                {loadingMode === 'manual'
                  ? 'Separando os locais que voce ja informou.'
                  : loadingMode === 'quick'
                    ? 'Combinando pontos citados com sugestoes relacionadas.'
                    : 'Selecionando paradas com ritmo de familia.'}
              </p>
            </div>
          </motion.div>
        ) : error ? (
          <motion.div
            key="error"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0 }}
            className="flex flex-col items-center justify-center py-20 space-y-8 text-center max-w-lg mx-auto bg-card dark:bg-slate-800 p-10 rounded-3xl shadow-sm border border-border"
          >
            <div className="w-20 h-20 bg-destructive/10 rounded-full flex items-center justify-center text-destructive">
              <AlertCircle className="w-10 h-10" />
            </div>
            <div>
              <h2 className="text-2xl font-serif font-bold text-foreground mb-3">Ops! Tivemos um imprevisto</h2>
              <p className="text-muted-foreground font-medium text-lg leading-relaxed">{error}</p>
            </div>
            <div className="flex flex-col sm:flex-row gap-4 w-full pt-4">
              <Button onClick={goBack} variant="outline" className="flex-1 rounded-full py-6 text-lg">
                <ArrowLeft className="w-5 h-5 mr-2" /> Editar destino
              </Button>
              <Button
                onClick={() => {
                  if (knownItineraryMode) {
                    processKnownItinerary();
                  } else if (loadingMode === 'manual') {
                    processManualAttractions();
                  } else {
                    processAttractions({
                      mode: loadingMode === 'quick' ? 'quick' : 'itinerary',
                      allowManualFallback: loadingMode === 'quick',
                    });
                  }
                }}
                className="flex-1 rounded-full py-6 text-lg bg-primary hover:bg-primary/90 text-white"
              >
                <RefreshCcw className="w-5 h-5 mr-2" /> Tentar novamente
              </Button>
            </div>
          </motion.div>
        ) : !hasSearchedLandmarks ? (
          <motion.div
            key="preparing"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="flex flex-col items-center justify-center py-32 space-y-4 text-center"
          >
            <div className="w-16 h-16 rounded-full bg-primary/10 text-primary flex items-center justify-center">
              <Loader2 className="w-8 h-8 animate-spin" />
            </div>
            <h2 className="text-3xl font-serif font-bold text-foreground">
              Preparando os cards...
            </h2>
          </motion.div>
        ) : hasSearchedLandmarks && parsedData.landmarks.length > 0 ? (
          <motion.div
            key="results"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="w-full space-y-10"
          >
            <div className="text-center space-y-3 mb-12">
              <h2 className="text-3xl md:text-4xl font-serif font-bold text-foreground">
                {itineraryMode
                  ? 'Roteiro sugerido para a sua familia'
                  : manualMode
                    ? 'Seu roteiro informado'
                    : 'Locais encontrados para sua viagem'}
              </h2>
              <p className="text-xl text-muted-foreground font-medium max-w-2xl mx-auto">
                {itineraryMode
                  ? recommendedItinerary.summary
                  : manualMode
                    ? knownItineraryMode
                      ? 'Confira as fotos dos pontos que voce informou e veja o mapa da viagem. Desmarque o que nao entrar no guia.'
                      : 'Organizamos os pontos que voce ja citou. Selecione os locais que farao parte do guia da sua familia.'
                    : 'Inclui pontos que voce citou e sugestoes baseadas no seu texto. Selecione o que entra no guia.'}
              </p>
              {renderCategoryFilters()}
              <div className="flex flex-col sm:flex-row justify-center gap-3 pt-2">
                <Button onClick={goBack} variant="outline" className="rounded-full px-6 py-3">
                  Editar destino
                </Button>
                <Button
                  onClick={() => setIsMapOpen(true)}
                  disabled={hasMissingMapLocations || isResolvingMapLocations}
                  variant="outline"
                  className="rounded-full px-6 py-3 font-bold"
                  title={
                    hasMissingMapLocations
                      ? 'Resolva os locais confirmados sem coordenadas antes de abrir o mapa.'
                      : 'Ver mapa da viagem'
                  }
                >
                  <MapIcon className="mr-2 h-4 w-4" />
                  Ver mapa da viagem
                </Button>
                {!knownItineraryMode && (
                  <Button
                    onClick={() => {
                      setError(null);
                      processAttractions({ mode: 'itinerary' });
                    }}
                    className="rounded-full px-6 py-3 bg-secondary hover:bg-secondary/90 text-white"
                  >
                    Atualizar sugestões
                  </Button>
                )}
              </div>
              {selectedCount > 0 && (
                <div className="mx-auto mt-5 max-w-2xl rounded-2xl border border-border/70 bg-card/80 px-4 py-3 text-left shadow-sm">
                  {!hasMissingMapLocations ? (
                    <div className="flex items-center gap-3 text-sm font-bold text-secondary">
                      <MapIcon className="h-4 w-4 shrink-0" />
                      <span>
                        Mapa validado para {confirmedWithMapCount}{' '}
                        {confirmedWithMapCount === 1 ? 'local confirmado' : 'locais confirmados'}.
                      </span>
                    </div>
                  ) : (
                    <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                      <div className="flex items-start gap-3 text-sm">
                        <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
                        <div>
                          <p className="font-bold text-foreground">
                            {missingMapLandmarks.length}{' '}
                            {missingMapLandmarks.length === 1
                              ? 'local confirmado ainda esta sem mapa'
                              : 'locais confirmados ainda estao sem mapa'}
                          </p>
                          <p className="text-xs font-medium text-muted-foreground">
                            Vou tentar resolver novamente pelo Google Places antes de fechar o roteiro.
                          </p>
                        </div>
                      </div>
                      <Button
                        type="button"
                        onClick={retryResolveMapLocations}
                        disabled={isResolvingMapLocations}
                        variant="outline"
                        className="rounded-full px-4 py-2 text-sm font-bold"
                      >
                        {isResolvingMapLocations ? (
                          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        ) : (
                          <RefreshCcw className="mr-2 h-4 w-4" />
                        )}
                        Tentar localizar no mapa
                      </Button>
                    </div>
                  )}
                  {mapLocationNotice && (
                    <p className="mt-2 text-xs font-bold text-secondary">{mapLocationNotice}</p>
                  )}
                  {mapLocationError && (
                    <p className="mt-2 text-xs font-bold text-destructive">{mapLocationError}</p>
                  )}
                </div>
              )}
            </div>

            {itineraryMode
              ? renderItineraryDays()
              : manualMode
                ? renderManualGroups()
                : renderQuickSuggestionCards()}

            <div className="sticky bottom-0 z-10 flex justify-center bg-gradient-to-t from-background via-background to-transparent px-4 pb-8 pt-16">
              <Button
                onClick={nextStep}
                disabled={selectedLandmarks.length === 0}
                className="w-full max-w-md rounded-full bg-primary px-6 py-6 text-base font-bold text-white shadow-xl transition-all hover:-translate-y-1 hover:bg-primary/90 disabled:opacity-50 disabled:hover:translate-y-0 sm:w-auto sm:px-12 sm:py-8 sm:text-xl"
              >
                Confirmar {selectedCount} {selectedCount === 1 ? 'local' : 'locais'} <ArrowRight className="ml-3 w-6 h-6" />
              </Button>
            </div>
          </motion.div>
        ) : hasSearchedLandmarks ? (
          <motion.div
            key="empty"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex flex-col items-center justify-center py-20 text-center"
          >
            <h2 className="text-3xl font-serif font-bold text-foreground mb-4">Nenhum ponto especifico encontrado</h2>
            <p className="text-lg text-muted-foreground font-medium mb-8 max-w-md mx-auto">
              Nao conseguimos extrair monumentos exatos do seu texto. Deseja adicionar mais detalhes?
            </p>
            <Button onClick={goBack} variant="outline" className="rounded-full px-8 py-6 text-lg">
              <ArrowLeft className="w-5 h-5 mr-2" /> Editar destino
            </Button>
          </motion.div>
        ) : null}
      </AnimatePresence>

      <MapOverviewModal
        open={isMapOpen}
        landmarks={parsedData.landmarks}
        selectedLandmarks={selectedLandmarks}
        onToggleLandmark={toggleLandmarkSelection}
        onExploreMore={knownItineraryMode ? undefined : exploreMoreMapPlaces}
        isExploringMore={isMapExploringMore}
        exploreError={mapExploreError}
        exploreNotice={mapExploreNotice}
        onClose={() => setIsMapOpen(false)}
      />
    </div>
  );
};

export default Step4Attractions;
