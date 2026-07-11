import React, { useEffect, useRef, useState } from 'react';
import { motion } from 'framer-motion';
import {
  ArrowRight,
  CalendarDays,
  Landmark,
  ListChecks,
  Loader2,
  MapPin,
  MessageSquareText,
  Plus,
  Sparkles,
  Trash2,
  X,
} from 'lucide-react';
import { useConversationalGuide } from '@/contexts/ConversationalGuideContext.jsx';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  normalizeRouteSuggestionDestinations,
  createGuideDestination,
  normalizeGuideDestinations,
  parseFreeformItineraryText,
  validGuideDestinations,
  validKnownGuideDestinations,
} from '@/utils/guide-form.js';
import {
  buildRouteSuggestionPayload,
  suggestItineraryRoutes,
} from '@/utils/minerva-api.js';

const itineraryModeOptions = [
  {
    id: 'known',
    label: 'Já sei o roteiro',
    description: 'Adicionar cada destino com os pontos turísticos que vão visitar.',
    icon: ListChecks,
  },
  {
    id: 'freeform',
    label: 'Falar livremente',
    description: 'Colar uma ideia de rota e completar o que faltar.',
    icon: MessageSquareText,
  },
  {
    id: 'suggested',
    label: 'Quero sugestões',
    description: 'Gerar uma rota editável antes das atrações.',
    icon: Sparkles,
  },
];

const Step3Destination = () => {
  const {
    destinationsList,
    updateDestinationsList,
    itineraryMode,
    setItineraryMode,
    itineraryPreferences,
    childrenList,
    restoredDraftId,
    restoredDestinationsList,
    draftResetKey,
    nextStep
  } = useConversationalGuide();
  const [localDestinations, setLocalDestinations] = useState(
    destinationsList?.length ? destinationsList : [createGuideDestination()]
  );
  const [error, setError] = useState('');
  const [freeformText, setFreeformText] = useState('');
  const [freeformResult, setFreeformResult] = useState(null);
  const [routeIdea, setRouteIdea] = useState('');
  const [suggestedRoutes, setSuggestedRoutes] = useState([]);
  const [isLoadingSuggestions, setIsLoadingSuggestions] = useState(false);
  const pendingFocusDestinationId = useRef(null);
  const formErrorRef = useRef(null);

  useEffect(() => {
    const hasMeaningfulChange = localDestinations.some((item) =>
      item.place.trim() || item.timing.trim() || item.landmarks?.some((landmark) => landmark.trim())
    );
    if (hasMeaningfulChange) updateDestinationsList(localDestinations);
  }, [localDestinations, updateDestinationsList]);

  useEffect(() => {
    if (!restoredDraftId) return;
    setLocalDestinations(
      restoredDestinationsList?.length
        ? normalizeGuideDestinations(restoredDestinationsList)
        : [createGuideDestination()]
    );
  }, [restoredDestinationsList, restoredDraftId]);

  useEffect(() => {
    if (draftResetKey > 0) setLocalDestinations([createGuideDestination()]);
  }, [draftResetKey]);

  const changeItineraryMode = (mode) => {
    setItineraryMode(mode);
    setError('');
  };

  const updateDestinationField = (id, field, value) => {
    setLocalDestinations((prev) =>
      prev.map((destination) =>
        destination.id === id ? { ...destination, [field]: value } : destination
      )
    );
    setError('');
  };

  const handleAddDestination = () => {
    const newDestination = createGuideDestination();
    pendingFocusDestinationId.current = newDestination.id;
    setLocalDestinations((prev) => [
      ...prev,
      newDestination,
    ]);
    setError('');
  };

  const handleRemoveDestination = (id) => {
    if (localDestinations.length === 1) return;

    const removedIndex = localDestinations.findIndex((destination) => destination.id === id);
    const remainingDestinations = localDestinations.filter(
      (destination) => destination.id !== id
    );
    const focusIndex = Math.min(Math.max(removedIndex, 0), remainingDestinations.length - 1);
    pendingFocusDestinationId.current = remainingDestinations[focusIndex]?.id || null;
    setLocalDestinations(remainingDestinations);
    setError('');
  };

  const landmarkBoxesFor = (destination) =>
    destination.landmarks?.length ? destination.landmarks : [''];

  const focusFirstInvalidField = (destinations) => {
    const destinationIndex = destinations.findIndex((item) =>
      !item.place || !item.timing || !Number.isFinite(Number(item.days)) || Number(item.days) < 1
    );
    if (destinationIndex >= 0) {
      const invalid = destinations[destinationIndex];
      const field = !invalid.place
        ? 'place'
        : !invalid.timing
          ? 'timing'
          : 'days';
      document.getElementById(`${invalid.id}-${field}`)?.focus();
      return;
    }
    const missingLandmarkDestination = destinations.find((item) =>
      !landmarkBoxesFor(item).some((landmark) => landmark.trim())
    );
    document.getElementById(`${missingLandmarkDestination?.id}-landmark-0`)?.focus();
  };

  const updateLandmarkField = (id, landmarkIndex, value) => {
    setLocalDestinations((prev) =>
      prev.map((destination) => {
        if (destination.id !== id) return destination;
        const landmarks = [...landmarkBoxesFor(destination)];
        landmarks[landmarkIndex] = value;
        return { ...destination, landmarks };
      })
    );
    setError('');
  };

  const handleAddLandmark = (id) => {
    setLocalDestinations((prev) =>
      prev.map((destination) =>
        destination.id === id
          ? { ...destination, landmarks: [...landmarkBoxesFor(destination), ''] }
          : destination
      )
    );
    setError('');
  };

  const handleRemoveLandmark = (id, landmarkIndex) => {
    setLocalDestinations((prev) =>
      prev.map((destination) => {
        if (destination.id !== id) return destination;
        const landmarks = landmarkBoxesFor(destination);
        if (landmarks.length === 1) {
          return { ...destination, landmarks: [''] };
        }
        return {
          ...destination,
          landmarks: landmarks.filter((_, index) => index !== landmarkIndex),
        };
      })
    );
    setError('');
  };

  const handleSubmit = (event) => {
    event.preventDefault();
    const normalized = normalizeGuideDestinations(localDestinations);

    if (
      itineraryMode === 'freeform' &&
      freeformResult?.followUpQuestions?.some((question) => question.field === 'order')
    ) {
      setError('Confirme a ordem dos destinos antes de continuar.');
      formErrorRef.current?.focus();
      return;
    }

    if (!validGuideDestinations(normalized)) {
      setError('Preencha o destino, quando a viagem acontece e por quantos dias em cada parada.');
      focusFirstInvalidField(normalized);
      return;
    }

    if (itineraryMode === 'known' && !validKnownGuideDestinations(normalized)) {
      setError('Adicione pelo menos um ponto turístico em cada destino.');
      focusFirstInvalidField(normalized);
      return;
    }

    updateDestinationsList(normalized);
    nextStep();
  };

  const applyFreeformItinerary = () => {
    const result = parseFreeformItineraryText(freeformText);
    setFreeformResult(result);
    if (result.destinations.length > 0) {
      setLocalDestinations(result.destinations);
    }
    setError('');
  };

  const confirmCurrentOrder = () => {
    setFreeformResult((current) => ({
      ...current,
      followUpQuestions: (current?.followUpQuestions || []).filter(
        (question) => question.field !== 'order'
      ),
    }));
    setError('');
  };

  const loadSuggestedRoutes = async () => {
    setIsLoadingSuggestions(true);
    setError('');
    try {
      const payload = buildRouteSuggestionPayload({
        tripIdea: routeIdea,
        destinationsList: localDestinations,
        itineraryPreferences,
        childrenList,
      });
      const data = await suggestItineraryRoutes(payload);
      setSuggestedRoutes(data.options || []);
    } catch (nextError) {
      setError(nextError.message || 'Não foi possível gerar sugestões de roteiro.');
    } finally {
      setIsLoadingSuggestions(false);
    }
  };

  const acceptSuggestedRoute = (route) => {
    const destinations = normalizeRouteSuggestionDestinations(route.structured_destinations || []);
    if (destinations.length > 0) {
      setLocalDestinations(destinations);
      setError('');
    }
  };

  const rejectSuggestedRoutes = () => {
    setSuggestedRoutes([]);
    setItineraryMode('known');
    setError('');
  };

  return (
    <div className="w-full max-w-4xl mx-auto flex flex-col min-h-[60vh] justify-center py-4">
      <div className="text-center space-y-4 mb-10">
        <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-secondary/10 text-secondary">
          <MapPin className="h-8 w-8" />
        </div>
        <h2 className="text-3xl sm:text-4xl md:text-5xl font-serif font-bold text-foreground">
          Para onde vai ser a aventura?
        </h2>
        <p className="mx-auto max-w-2xl text-lg text-muted-foreground font-medium">
          Adicione cada destino separadamente para montarmos o guia na ordem da viagem.
        </p>
      </div>

      <motion.form
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        className="space-y-6"
        onSubmit={handleSubmit}
      >
        <div className="grid gap-3 sm:grid-cols-3" role="radiogroup" aria-label="Como montar o roteiro">
          {itineraryModeOptions.map((option) => {
            const Icon = option.icon;
            const selected = itineraryMode === option.id;
            return (
              <button
                key={option.id}
                type="button"
                role="radio"
                aria-checked={selected}
                onClick={() => changeItineraryMode(option.id)}
                className={`rounded-2xl border p-4 text-left transition ${
                  selected
                    ? 'border-secondary bg-secondary/10 text-foreground shadow-sm'
                    : 'border-border/70 bg-background text-muted-foreground hover:border-secondary/50'
                }`}
              >
                <span className="mb-3 flex h-10 w-10 items-center justify-center rounded-xl bg-card text-secondary">
                  <Icon className="h-5 w-5" />
                </span>
                <span className="block text-sm font-bold">{option.label}</span>
                <span className="mt-1 block text-xs leading-relaxed">{option.description}</span>
              </button>
            );
          })}
        </div>

        {itineraryMode === 'freeform' && (
          <div className="rounded-[2rem] border border-border/70 bg-background p-5">
            <div className="space-y-2">
              <Label htmlFor="freeform-itinerary" className="font-bold">
                Conte seu roteiro do seu jeito
              </Label>
              <Textarea
                id="freeform-itinerary"
                value={freeformText}
                onChange={(event) => setFreeformText(event.target.value)}
                placeholder="Ex: Primeiro Paris em julho por 3 dias; depois Londres por 2 dias."
                className="min-h-28 rounded-xl text-base"
              />
            </div>
            <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <Button
                type="button"
                variant="outline"
                onClick={applyFreeformItinerary}
                className="rounded-full px-6 py-5 font-bold"
              >
                Converter em destinos
              </Button>
              {freeformResult?.followUpQuestions?.some((question) => question.field === 'order') && (
                <Button
                  type="button"
                  onClick={confirmCurrentOrder}
                  className="rounded-full bg-secondary px-6 py-5 font-bold text-white hover:bg-secondary/90"
                >
                  Usar esta ordem
                </Button>
              )}
            </div>
            {freeformResult?.followUpQuestions?.length > 0 && (
              <div className="mt-4 rounded-2xl bg-muted/60 p-4">
                <p className="text-sm font-bold text-foreground">Perguntas para completar:</p>
                <ul className="mt-2 space-y-1 text-sm text-muted-foreground">
                  {freeformResult.followUpQuestions.map((question, index) => (
                    <li key={`${question.field}-${question.destinationId || index}`}>
                      {question.message}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        {itineraryMode === 'suggested' && (
          <div className="rounded-[2rem] border border-border/70 bg-background p-5">
            <div className="space-y-2">
              <Label htmlFor="route-suggestion" className="font-bold">
                O que vocês imaginam para essa viagem?
              </Label>
              <Textarea
                id="route-suggestion"
                value={routeIdea}
                onChange={(event) => setRouteIdea(event.target.value)}
                placeholder="Ex: Queremos Paris e Londres com parques, museus e ritmo leve."
                className="min-h-28 rounded-xl text-base"
              />
            </div>
            <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-center">
              <Button
                type="button"
                onClick={loadSuggestedRoutes}
                disabled={isLoadingSuggestions}
                className="rounded-full bg-secondary px-6 py-5 font-bold text-white hover:bg-secondary/90"
              >
                {isLoadingSuggestions ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <Sparkles className="mr-2 h-4 w-4" />
                )}
                Gerar opções
              </Button>
              {suggestedRoutes.length > 0 && (
                <Button
                  type="button"
                  variant="outline"
                  onClick={rejectSuggestedRoutes}
                  className="rounded-full px-6 py-5 font-bold"
                >
                  Inserir manualmente
                </Button>
              )}
            </div>
            {suggestedRoutes.length > 0 && (
              <div className="mt-5 space-y-3">
                {suggestedRoutes.map((route) => (
                  <div key={route.id} className="rounded-2xl border border-border/70 bg-card p-4">
                    <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                      <div>
                        <p className="font-bold text-foreground">{route.title}</p>
                        <p className="mt-1 text-sm text-muted-foreground">{route.summary}</p>
                      </div>
                      <Button
                        type="button"
                        onClick={() => acceptSuggestedRoute(route)}
                        className="rounded-full bg-primary px-5 py-4 text-white hover:bg-primary/90"
                      >
                        Usar rota
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {localDestinations.map((destination, index) => (
          <div
            key={destination.id}
            className="rounded-[2rem] border-2 border-border/70 bg-card p-5 shadow-sm dark:bg-slate-800/50 sm:p-6"
          >
            <div className="mb-5 flex items-center justify-between gap-4">
              <div>
                <p className="text-sm font-bold uppercase tracking-[0.2em] text-muted-foreground">
                  Destino {index + 1}
                </p>
                <h3 className="text-xl font-serif font-bold text-foreground">
                  Parada da viagem
                </h3>
              </div>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                disabled={localDestinations.length === 1}
                onClick={() => handleRemoveDestination(destination.id)}
                className="rounded-xl text-muted-foreground hover:bg-destructive/10 hover:text-destructive disabled:opacity-30"
                aria-label="Remover destino"
              >
                <Trash2 className="h-5 w-5" />
              </Button>
            </div>

            <div className="grid grid-cols-1 gap-4 md:grid-cols-[1.4fr_1fr_0.7fr]">
              <div className="space-y-2">
                <Label htmlFor={`${destination.id}-place`} className="font-bold">
                  Pra onde você vai?
                </Label>
                <Input
                  id={`${destination.id}-place`}
                  ref={(input) => {
                    if (input && pendingFocusDestinationId.current === destination.id) {
                      pendingFocusDestinationId.current = null;
                      input.focus();
                    }
                  }}
                  autoFocus={index === 0}
                  value={destination.place}
                  onChange={(event) =>
                    updateDestinationField(destination.id, 'place', event.target.value)
                  }
                  placeholder="Ex: Paris, França"
                  className="rounded-xl py-6 text-base"
                  aria-invalid={Boolean(error && !destination.place.trim())}
                  aria-describedby={error && !destination.place.trim() ? 'destination-error' : undefined}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor={`${destination.id}-timing`} className="font-bold">
                  Quando?
                </Label>
                <Input
                  id={`${destination.id}-timing`}
                  value={destination.timing}
                  onChange={(event) =>
                    updateDestinationField(destination.id, 'timing', event.target.value)
                  }
                  placeholder="Ex: Julho de 2026"
                  className="rounded-xl py-6 text-base"
                  aria-invalid={Boolean(error && !destination.timing.trim())}
                  aria-describedby={error && !destination.timing.trim() ? 'destination-error' : undefined}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor={`${destination.id}-days`} className="font-bold">
                  Por quantos dias?
                </Label>
                <Input
                  id={`${destination.id}-days`}
                  type="number"
                  min="1"
                  value={destination.days}
                  onChange={(event) =>
                    updateDestinationField(destination.id, 'days', event.target.value)
                  }
                  className="rounded-xl py-6 text-base"
                  aria-invalid={Boolean(error && Number(destination.days) < 1)}
                  aria-describedby={error && Number(destination.days) < 1 ? 'destination-error' : undefined}
                />
              </div>
            </div>

            {itineraryMode === 'known' && (
              <div className="mt-6 rounded-2xl border border-border/60 bg-background/60 p-4 sm:p-5">
                <Label className="mb-3 flex items-center gap-2 font-bold">
                  <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10 text-primary">
                    <Landmark className="h-4 w-4" />
                  </span>
                  Pontos turísticos {destination.place ? `em ${destination.place}` : 'deste destino'}
                </Label>
                <div className="space-y-3">
                  {landmarkBoxesFor(destination).map((landmarkName, landmarkIndex) => (
                    <div
                      key={`${destination.id}-landmark-${landmarkIndex}`}
                      className="flex items-center gap-3"
                    >
                      <Input
                        id={`${destination.id}-landmark-${landmarkIndex}`}
                        value={landmarkName}
                        onChange={(event) =>
                          updateLandmarkField(destination.id, landmarkIndex, event.target.value)
                        }
                        placeholder={`Ex: ${landmarkIndex === 0 ? 'Torre Eiffel' : 'Museu do Louvre'}`}
                        aria-label={`Ponto turístico ${landmarkIndex + 1} do destino ${index + 1}`}
                        aria-invalid={Boolean(
                          error &&
                            itineraryMode === 'known' &&
                            !landmarkBoxesFor(destination).some((item) => item.trim())
                        )}
                        aria-describedby={
                          error &&
                          itineraryMode === 'known' &&
                          !landmarkBoxesFor(destination).some((item) => item.trim())
                            ? 'destination-error'
                            : undefined
                        }
                        className="rounded-xl py-6 text-base"
                      />
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        onClick={() => handleRemoveLandmark(destination.id, landmarkIndex)}
                        disabled={
                          landmarkBoxesFor(destination).length === 1 && !landmarkName.trim()
                        }
                        className="h-12 w-12 shrink-0 rounded-xl text-muted-foreground hover:bg-destructive/10 hover:text-destructive disabled:opacity-30"
                        aria-label="Remover ponto turístico"
                      >
                        <X className="h-5 w-5" />
                      </Button>
                    </div>
                  ))}
                </div>
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => handleAddLandmark(destination.id)}
                  className="mt-4 w-full rounded-xl border-2 border-dashed py-5 font-bold text-muted-foreground transition-colors hover:border-primary hover:bg-primary/5 hover:text-primary"
                >
                  <Plus className="mr-2 h-5 w-5" />
                  Adicionar ponto turístico
                </Button>
              </div>
            )}
          </div>
        ))}

        {error && (
          <p
            ref={formErrorRef}
            id="destination-error"
            role="alert"
            tabIndex={-1}
            className="rounded-2xl bg-destructive/10 px-4 py-3 text-center text-sm font-bold text-destructive"
          >
            {error}
          </p>
        )}

        <div className="flex flex-col gap-4 pt-2 sm:flex-row sm:items-center sm:justify-between">
          <Button
            type="button"
            variant="outline"
            onClick={handleAddDestination}
            className="rounded-full border-dashed px-6 py-6 font-bold"
          >
            <Plus className="mr-2 h-5 w-5" />
            Adicionar destino
          </Button>

          <Button
            type="submit"
            className="rounded-full bg-secondary px-8 py-6 text-lg font-bold text-white shadow-lg transition-all hover:-translate-y-1 hover:bg-secondary/90"
          >
            Próximo
            <ArrowRight className="ml-2 h-5 w-5" />
          </Button>
        </div>

        <div className="flex items-center justify-center gap-2 text-sm font-medium text-muted-foreground">
          <CalendarDays className="h-4 w-4" />
          {itineraryMode === 'known'
            ? 'Vamos buscar as fotos e o mapa dos pontos turísticos que você informar.'
            : 'O tempo de cada destino será usado para montar o ritmo do roteiro.'}
        </div>
      </motion.form>
    </div>
  );
};

export default Step3Destination;
