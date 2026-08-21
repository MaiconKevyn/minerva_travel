import React, { useMemo, useState } from 'react';
import { BookHeart, Check, Clock3, Eye, Palette, Pencil, Plane, Plus, Sparkles } from 'lucide-react';
import { useConversationalGuide } from '@/contexts/ConversationalGuideContext.jsx';
import { Button } from '@/components/ui/button';
import ActivityLandmarkPicker from '@/components/ActivityLandmarkPicker.jsx';
import ActivityPlanSummary from '@/components/ActivityPlanSummary.jsx';
import ActivityPreviewDialog from '@/components/ActivityPreviewDialog.jsx';
import FlightVocabularyCard from '@/components/FlightVocabularyCard.jsx';
import { selectGuideLandmarks } from '@/utils/minerva-api.js';
import { pluralize } from '@/utils/guide-form.js';
import {
  activityOptionsByCategory,
  countryHasPhrasebook,
  landmarksWithActivity,
  MAX_OPTIONAL_ACTIVITIES_PER_GUIDE,
  MAX_OPTIONAL_ACTIVITIES_PER_LANDMARK,
  toggleLandmarkActivitySelection,
} from '@/utils/landmark-activities.js';

const landmarkSelectionId = (landmark) => landmark.selection_id || landmark.id;

const StepActivities = () => {
  const {
    parsedData,
    selectedLandmarks,
    childrenList,
    landmarkActivitySelections,
    setLandmarkActivitySelections,
    flightVocabularyPages,
    setFlightVocabularyPages,
    nextStep,
  } = useConversationalGuide();
  const [selectionError, setSelectionError] = useState('');
  const [previewing, setPreviewing] = useState(null);

  const landmarks = useMemo(
    () => selectGuideLandmarks(parsedData.landmarks, selectedLandmarks),
    [parsedData.landmarks, selectedLandmarks],
  );
  // O catálogo aparece uma vez, não uma vez por parada: são os mesmos cards em
  // todos os pontos, e repeti-los enterrava o plano num scroll interminável.
  const categories = useMemo(
    () =>
      activityOptionsByCategory().map((category) => ({
        ...category,
        options: category.options.filter(
          (option) =>
            option.type !== 'language_survival' ||
            landmarks.some((landmark) => countryHasPhrasebook(landmark.country)),
        ),
      })).filter((category) => category.options.length > 0),
    [landmarks],
  );

  const childAges = childrenList
    .map((child) => Number.parseInt(child.age, 10))
    .filter((age) => Number.isFinite(age) && age > 0);
  const ageSummary = childAges.length > 0
    ? `Adaptaremos os desafios para ${childAges.join(', ')} anos.`
    : 'Adaptaremos os desafios para a família.';

  const guideFull = landmarkActivitySelections.length >= MAX_OPTIONAL_ACTIVITIES_PER_GUIDE;
  const onlyLandmark = landmarks.length === 1 ? landmarkSelectionId(landmarks[0]) : null;

  // Atualização funcional de propósito: no seletor a família marca duas
  // paradas em sequência, e ler o estado do closure faria o segundo clique
  // apagar o primeiro.
  const toggleActivity = (selectionId, activityType) => {
    let error = '';
    setLandmarkActivitySelections((current) => {
      const result = toggleLandmarkActivitySelection(current, selectionId, activityType);
      error = result.error;
      return result.selections;
    });
    setSelectionError(error);
  };

  return (
    <div className="mx-auto w-full max-w-6xl space-y-8 py-4">
      <div className="mx-auto max-w-3xl space-y-4 text-center">
        <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/10 text-primary">
          <Palette className="h-7 w-7" aria-hidden="true" />
        </div>
        <h2 className="text-3xl font-serif font-bold text-foreground sm:text-4xl md:text-5xl">
          Atividades da aventura
        </h2>
        <p className="text-lg font-medium text-muted-foreground">
          Escolha uma brincadeira e diga em quais paradas ela entra.
          <br />
          Nenhuma vem marcada automaticamente.
        </p>
        <p className="text-sm font-medium text-muted-foreground">
          Toque na lupa de cada card para ver a página inteira antes de decidir.
        </p>
        <p className="inline-flex items-center gap-2 rounded-full bg-accent/15 px-4 py-1.5 text-sm font-bold text-foreground">
          <Sparkles className="h-4 w-4 text-accent-foreground" aria-hidden="true" />
          {ageSummary}
        </p>
      </div>

      <ActivityPlanSummary
        landmarks={landmarks}
        selections={landmarkActivitySelections}
        onRemove={toggleActivity}
      />

      <FlightVocabularyCard
        landmarks={landmarks}
        enabled={flightVocabularyPages}
        onChange={setFlightVocabularyPages}
      />

      <section className="rounded-[2rem] border-2 border-secondary/25 bg-secondary/5 p-5 sm:p-6" aria-labelledby="mandatory-pages-title">
        <h3 id="mandatory-pages-title" className="sr-only">Páginas finais obrigatórias</h3>
        <div className="flex items-start gap-4">
          <BookHeart className="mt-1 h-7 w-7 shrink-0 text-secondary" aria-hidden="true" />
          <div>
            <h4 className="text-xl font-serif font-bold text-foreground">
              Minha melhor memória
            </h4>
            <p className="mt-1 font-medium text-muted-foreground">
              Página obrigatória depois dos passeios, com espaço para desenho, descoberta favorita,
              assinatura e data.
            </p>
          </div>
        </div>
        <div className="mt-5 flex items-start gap-4 border-t border-secondary/20 pt-5">
          <Plane className="mt-1 h-7 w-7 shrink-0 text-secondary" aria-hidden="true" />
          <div>
            <h4 className="text-xl font-serif font-bold text-foreground">
              Hora de voltar para casa
            </h4>
            <p className="mt-1 font-medium text-muted-foreground">
              Página final obrigatória, com a mesma família da capa e linhas para a criança contar
              algo especial quando chegar em casa.
            </p>
          </div>
        </div>
      </section>

      <div className="space-y-8">
        {categories.map((category) => (
          <section key={category.id} aria-labelledby={`activity-category-${category.id}`}>
            <div className="mb-3 flex flex-wrap items-baseline gap-x-2">
              <h3
                id={`activity-category-${category.id}`}
                className="text-sm font-bold uppercase tracking-[0.14em] text-foreground"
              >
                {category.label}
              </h3>
              <span className="text-xs font-medium text-muted-foreground">{category.hint}</span>
            </div>
            {/* Três colunas, não quatro: a página impressa é o argumento de
                venda da atividade e precisa caber legível no card. */}
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {category.options.map((activity) => {
                const chosenIds = landmarksWithActivity(landmarkActivitySelections, activity.type);
                const chosen = chosenIds.length > 0;
                const inputId = `activity-${activity.type}`;
                return (
                  <article
                    key={activity.type}
                    className={`group relative flex h-full flex-col overflow-hidden rounded-2xl border-2 bg-background transition ${
                      chosen
                        ? 'border-primary shadow-md ring-2 ring-primary/20'
                        : 'border-border/70 hover:border-primary/45 hover:shadow-md'
                    }`}
                  >
                    {/* A moldura tem a proporção da folha impressa e a arte
                        entra inteira. Numa janela 3:2 cortada pelo topo só
                        sobravam 44% da página: a cruzadinha aparecia sem as
                        dicas, o labirinto sem a saída e o cartão-postal sem o
                        espaço de escrever — justamente o que explica cada uma. */}
                    <div className="relative aspect-[2/3] overflow-hidden bg-muted">
                      <img
                        src={activity.preview}
                        alt={`Exemplo visual de ${activity.label}`}
                        loading="lazy"
                        className="h-full w-full object-contain transition duration-300 group-hover:scale-[1.03]"
                      />
                      <button
                        type="button"
                        onClick={() => setPreviewing(activity.type)}
                        aria-label={`Ver a página de ${activity.label} inteira`}
                        className="absolute left-2 top-2 flex h-11 w-11 items-center justify-center rounded-full border-2 border-white bg-white/90 text-muted-foreground shadow-sm transition hover:text-primary focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-primary/35"
                      >
                        <Eye className="h-4 w-4" aria-hidden="true" />
                      </button>
                      {chosen && (
                        <span className="absolute right-2 top-2 flex h-7 items-center gap-1 rounded-full border-2 border-primary bg-primary px-2 text-[11px] font-bold text-white shadow-sm">
                          <Check className="h-3.5 w-3.5" aria-hidden="true" />
                          {chosenIds.length}
                        </span>
                      )}
                    </div>
                    <div className="flex flex-1 flex-col gap-2 p-4">
                      <h4 className="text-base font-bold leading-snug text-foreground">
                        {activity.label}
                      </h4>
                      <p
                        id={`${inputId}-description`}
                        className="text-[13px] font-medium leading-relaxed text-muted-foreground"
                      >
                        {activity.description}
                      </p>
                      <div className="flex flex-wrap gap-1.5 pt-1 text-[10px] font-bold text-muted-foreground">
                        <span className="rounded-full bg-muted px-2 py-0.5">{activity.ageLabel}</span>
                        <span className="flex items-center gap-1 rounded-full bg-muted px-2 py-0.5">
                          <Clock3 className="h-2.5 w-2.5" aria-hidden="true" />
                          {activity.durationLabel}
                        </span>
                        <span className="flex items-center gap-1 rounded-full bg-muted px-2 py-0.5">
                          <Pencil className="h-2.5 w-2.5" aria-hidden="true" />
                          {activity.materialLabel}
                        </span>
                      </div>
                      <div className="mt-auto pt-2">
                        {/* Com uma parada só, escolher onde seria uma pergunta
                            com uma resposta possível: o card decide direto. */}
                        {onlyLandmark ? (
                          <button
                            type="button"
                            onClick={() => toggleActivity(onlyLandmark, activity.type)}
                            aria-describedby={`${inputId}-description`}
                            className={`flex min-h-11 w-full items-center justify-center gap-1.5 rounded-xl border-2 px-3 py-2 text-xs font-bold transition ${
                              chosen
                                ? 'border-primary bg-primary/10 text-primary'
                                : 'border-border/70 bg-background text-muted-foreground hover:border-primary/45 hover:text-foreground'
                            }`}
                          >
                            {chosen ? (
                              <><Check className="h-3.5 w-3.5" aria-hidden="true" /> No guia</>
                            ) : (
                              <><Plus className="h-3.5 w-3.5" aria-hidden="true" /> Incluir no guia</>
                            )}
                          </button>
                        ) : (
                          <ActivityLandmarkPicker
                            activity={activity}
                            landmarks={landmarks}
                            selections={landmarkActivitySelections}
                            perLandmarkLimit={MAX_OPTIONAL_ACTIVITIES_PER_LANDMARK}
                            guideFull={guideFull}
                            chosenIds={chosenIds}
                            onToggle={(id) => toggleActivity(id, activity.type)}
                          />
                        )}
                      </div>
                    </div>

                    <ActivityPreviewDialog
                      activity={activity}
                      landmarks={landmarks}
                      chosenIds={chosenIds}
                      onToggle={toggleActivity}
                      open={previewing === activity.type}
                      onOpenChange={(next) => setPreviewing(next ? activity.type : null)}
                    />
                  </article>
                );
              })}
            </div>
          </section>
        ))}
      </div>

      <div className="sticky bottom-4 z-10 rounded-3xl border-2 border-border/70 bg-card/95 p-4 shadow-xl backdrop-blur sm:flex sm:items-center sm:justify-between sm:gap-6">
        <div className="mb-4 sm:mb-0">
          <p className="font-bold text-foreground" aria-live="polite">
            {landmarkActivitySelections.length} de {MAX_OPTIONAL_ACTIVITIES_PER_GUIDE} páginas opcionais
          </p>
          <p className="text-sm text-muted-foreground">A página “Minha melhor memória” será adicionada separadamente.</p>
          {selectionError && <p className="mt-1 text-sm font-bold text-destructive" role="alert">{selectionError}</p>}
        </div>
        <Button
          type="button"
          onClick={nextStep}
          className="w-full rounded-full px-8 py-6 font-bold sm:w-auto"
        >
          {landmarkActivitySelections.length === 0
            ? 'Continuar sem atividades opcionais'
            : `Continuar com ${pluralize(landmarkActivitySelections.length, 'atividade', 'atividades')}`}
        </Button>
      </div>
    </div>
  );
};

export default StepActivities;
