import React, { useMemo, useState } from 'react';
import { BookHeart, Check, Clock3, Palette, Pencil, Sparkles } from 'lucide-react';
import { useConversationalGuide } from '@/contexts/ConversationalGuideContext.jsx';
import { Button } from '@/components/ui/button';
import { selectGuideLandmarks } from '@/utils/minerva-api.js';
import {
  LANDMARK_ACTIVITY_OPTIONS,
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
    nextStep,
  } = useConversationalGuide();
  const [selectionError, setSelectionError] = useState('');

  const landmarks = useMemo(
    () => selectGuideLandmarks(parsedData.landmarks, selectedLandmarks),
    [parsedData.landmarks, selectedLandmarks],
  );
  const childAges = childrenList
    .map((child) => Number.parseInt(child.age, 10))
    .filter((age) => Number.isFinite(age) && age > 0);
  const ageSummary = childAges.length > 0
    ? `Adaptaremos os desafios para ${childAges.join(', ')} anos.`
    : 'Adaptaremos os desafios para a família.';

  const isSelected = (selectionId, activityType) => landmarkActivitySelections.some(
    (selection) =>
      selection.landmark_selection_id === selectionId &&
      selection.activity_type === activityType,
  );

  const toggleActivity = (selectionId, activityType) => {
    const result = toggleLandmarkActivitySelection(
      landmarkActivitySelections,
      selectionId,
      activityType,
    );
    setLandmarkActivitySelections(result.selections);
    setSelectionError(result.error);
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
          Escolha as brincadeiras que a criança encontrará depois de cada ponto turístico.
          Nenhuma atividade opcional vem marcada automaticamente.
        </p>
        <p className="text-sm font-bold text-primary">{ageSummary}</p>
      </div>

      <section className="rounded-[2rem] border-2 border-secondary/25 bg-secondary/5 p-5 sm:p-6" aria-labelledby="memory-page-title">
        <div className="flex items-start gap-4">
          <BookHeart className="mt-1 h-7 w-7 shrink-0 text-secondary" aria-hidden="true" />
          <div>
            <h3 id="memory-page-title" className="text-xl font-serif font-bold text-foreground">
              Minha melhor memória
            </h3>
            <p className="mt-1 font-medium text-muted-foreground">
              Esta página é obrigatória e será incluída no final do guia, com espaço para desenho,
              descoberta favorita, assinatura e data.
            </p>
          </div>
        </div>
      </section>

      <div className="space-y-8">
        {landmarks.map((landmark, landmarkIndex) => {
          const selectionId = landmarkSelectionId(landmark);
          const selectedForPoint = landmarkActivitySelections.filter(
            (selection) => selection.landmark_selection_id === selectionId,
          ).length;
          const location = [landmark.city, landmark.country].filter(Boolean).join(', ');

          return (
            <section
              key={selectionId}
              className="overflow-hidden rounded-[2rem] border-2 border-border/70 bg-card shadow-sm"
              aria-labelledby={`activity-landmark-${landmarkIndex}`}
            >
              <div className="flex flex-col gap-4 border-b border-border/70 bg-muted/35 p-5 sm:flex-row sm:items-center sm:justify-between sm:p-6">
                <div className="flex items-center gap-4">
                  {landmark.image ? (
                    <img
                      src={landmark.image}
                      alt=""
                      className="h-20 w-20 rounded-2xl bg-muted object-cover"
                    />
                  ) : (
                    <div className="flex h-20 w-20 items-center justify-center rounded-2xl bg-primary/10 text-primary">
                      <Sparkles className="h-8 w-8" aria-hidden="true" />
                    </div>
                  )}
                  <div>
                    <p className="text-xs font-bold uppercase tracking-[0.16em] text-primary">
                      Ponto {landmarkIndex + 1}
                    </p>
                    <h3 id={`activity-landmark-${landmarkIndex}`} className="text-2xl font-serif font-bold text-foreground">
                      {landmark.name}
                    </h3>
                    {location && <p className="text-sm font-medium text-muted-foreground">{location}</p>}
                  </div>
                </div>
                <span className="w-fit rounded-full bg-background px-4 py-2 text-sm font-bold text-muted-foreground">
                  {selectedForPoint}/{MAX_OPTIONAL_ACTIVITIES_PER_LANDMARK} escolhidas
                </span>
              </div>

              <div className="grid gap-5 p-5 sm:grid-cols-2 sm:p-6 lg:grid-cols-4">
                {LANDMARK_ACTIVITY_OPTIONS.map((activity) => {
                  const selected = isSelected(selectionId, activity.type);
                  const inputId = `${selectionId}-${activity.type}`.replace(/[^a-zA-Z0-9_-]/g, '-');
                  return (
                    <label
                      key={activity.type}
                      htmlFor={inputId}
                      className={`group relative cursor-pointer overflow-hidden rounded-3xl border-2 bg-background transition focus-within:ring-4 focus-within:ring-primary/25 ${
                        selected
                          ? 'border-primary shadow-md'
                          : 'border-border/70 hover:border-primary/45 hover:shadow-sm'
                      }`}
                    >
                      <input
                        id={inputId}
                        type="checkbox"
                        checked={selected}
                        onChange={() => toggleActivity(selectionId, activity.type)}
                        className="sr-only"
                        aria-describedby={`${inputId}-description`}
                      />
                      <div className="relative aspect-[3/2] overflow-hidden bg-muted">
                        <img
                          src={activity.preview}
                          alt={`Exemplo visual de ${activity.label}`}
                          className="h-full w-full object-cover transition duration-300 group-hover:scale-[1.02]"
                        />
                        <span className="absolute left-3 top-3 rounded-full bg-foreground/85 px-3 py-1 text-[11px] font-bold uppercase tracking-wide text-background">
                          Exemplo
                        </span>
                        <span className={`absolute right-3 top-3 flex h-8 w-8 items-center justify-center rounded-full border-2 ${
                          selected
                            ? 'border-primary bg-primary text-primary-foreground'
                            : 'border-white bg-white/90 text-transparent'
                        }`} aria-hidden="true">
                          <Check className="h-5 w-5" />
                        </span>
                      </div>
                      <div className="space-y-3 p-4">
                        <h4 className="text-lg font-serif font-bold text-foreground">{activity.label}</h4>
                        <p id={`${inputId}-description`} className="text-sm font-medium leading-relaxed text-muted-foreground">
                          {activity.description}
                        </p>
                        <div className="flex flex-wrap gap-2 text-[11px] font-bold text-muted-foreground">
                          <span className="rounded-full bg-muted px-2.5 py-1">{activity.ageLabel}</span>
                          <span className="flex items-center gap-1 rounded-full bg-muted px-2.5 py-1">
                            <Clock3 className="h-3 w-3" aria-hidden="true" /> {activity.durationLabel}
                          </span>
                          <span className="flex items-center gap-1 rounded-full bg-muted px-2.5 py-1">
                            <Pencil className="h-3 w-3" aria-hidden="true" /> {activity.materialLabel}
                          </span>
                        </div>
                        <p className="text-xs font-bold text-primary">Será adaptada para {landmark.name}</p>
                      </div>
                    </label>
                  );
                })}
              </div>
            </section>
          );
        })}
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
            : `Continuar com ${landmarkActivitySelections.length} atividades`}
        </Button>
      </div>
    </div>
  );
};

export default StepActivities;
