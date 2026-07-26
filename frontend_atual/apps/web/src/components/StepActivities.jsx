import React, { useMemo, useState } from 'react';
import { BookHeart, Check, Clock3, Palette, Pencil, Plane, Plus, Sparkles } from 'lucide-react';
import { useConversationalGuide } from '@/contexts/ConversationalGuideContext.jsx';
import { Button } from '@/components/ui/button';
import { selectGuideLandmarks } from '@/utils/minerva-api.js';
import { pluralize } from '@/utils/guide-form.js';
import {
  activityOptionsByCategory,
  activityOptionsForCountry,
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
        {/* Dito uma vez: com o catálogo cheio, um selo "Assim fica" por card
            cobriria boa parte da miniatura. */}
        <p className="text-sm font-medium text-muted-foreground">
          Assim fica: cada miniatura é a página impressa de verdade.
        </p>
        {/* Informação de apoio: chip suave, não texto na cor de ação/alerta. */}
        <p className="inline-flex items-center gap-2 rounded-full bg-accent/15 px-4 py-1.5 text-sm font-bold text-foreground">
          <Sparkles className="h-4 w-4 text-accent-foreground" aria-hidden="true" />
          {ageSummary}
        </p>
      </div>

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
        {landmarks.map((landmark, landmarkIndex) => {
          const selectionId = landmarkSelectionId(landmark);
          const selectedForPoint = landmarkActivitySelections.filter(
            (selection) => selection.landmark_selection_id === selectionId,
          ).length;
          const location = [landmark.city, landmark.country].filter(Boolean).join(', ');
          // O guia de frases só existe para países conferidos; nos demais o
          // card some em vez de prometer uma página que não seria gerada.
          const categories = activityOptionsByCategory(
            activityOptionsForCountry(landmark.country),
          );

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
                <div className="sm:text-right">
                  <span className="inline-block w-fit rounded-full bg-background px-4 py-2 text-sm font-bold text-muted-foreground">
                    {selectedForPoint}/{MAX_OPTIONAL_ACTIVITIES_PER_LANDMARK} escolhidas
                  </span>
                  {/* Dito uma vez por ponto: antes repetia em cada card. */}
                  <p className="mt-1.5 text-xs font-medium text-muted-foreground">
                    Cada atividade será adaptada para {landmark.name}.
                  </p>
                </div>
              </div>

              <div className="space-y-6 p-5 sm:p-6">
                {categories.map((category) => (
                  <div key={category.id}>
                    <div className="mb-3 flex flex-wrap items-baseline gap-x-2">
                      <h4 className="text-sm font-bold uppercase tracking-[0.14em] text-foreground">
                        {category.label}
                      </h4>
                      <span className="text-xs font-medium text-muted-foreground">
                        {category.hint}
                      </span>
                    </div>
                    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                      {category.options.map((activity) => {
                        const selected = isSelected(selectionId, activity.type);
                        const inputId = `${selectionId}-${activity.type}`.replace(
                          /[^a-zA-Z0-9_-]/g,
                          '-',
                        );
                        return (
                          <label
                            key={activity.type}
                            htmlFor={inputId}
                            // h-full + flex mantém todos os cards da linha alinhados
                            // mesmo com descrições de tamanhos diferentes.
                            className={`group relative flex h-full cursor-pointer flex-col overflow-hidden rounded-2xl border-2 bg-background transition focus-within:ring-4 focus-within:ring-primary/25 ${
                              selected
                                ? 'border-primary shadow-md ring-2 ring-primary/20'
                                : 'border-border/70 hover:-translate-y-0.5 hover:border-primary/45 hover:shadow-md'
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
                                loading="lazy"
                                className="h-full w-full object-cover object-top transition duration-300 group-hover:scale-[1.03]"
                              />
                              {/* Marca de seleção sempre visível: o estado vazio antes
                                  era transparente e não parecia clicável. */}
                              <span
                                className={`absolute right-2 top-2 flex h-7 w-7 items-center justify-center rounded-full border-2 shadow-sm transition ${
                                  selected
                                    ? 'border-primary bg-primary text-white'
                                    : 'border-white bg-white/90 text-muted-foreground/70 group-hover:text-primary'
                                }`}
                                aria-hidden="true"
                              >
                                {selected ? (
                                  <Check className="h-4 w-4" />
                                ) : (
                                  <Plus className="h-4 w-4" />
                                )}
                              </span>
                              <span
                                className={`absolute inset-x-0 bottom-0 py-1 text-center text-[11px] font-bold text-white transition ${
                                  selected
                                    ? 'bg-primary/90'
                                    : 'bg-foreground/70 opacity-0 group-hover:opacity-100'
                                }`}
                              >
                                {selected ? 'No guia' : 'Incluir no guia'}
                              </span>
                            </div>
                            <div className="flex flex-1 flex-col gap-1.5 p-3">
                              <h5 className="text-sm font-bold leading-snug text-foreground">
                                {activity.label}
                              </h5>
                              <p
                                id={`${inputId}-description`}
                                className="line-clamp-2 text-xs font-medium leading-relaxed text-muted-foreground"
                              >
                                {activity.description}
                              </p>
                              <div className="mt-auto flex flex-wrap gap-1.5 pt-1 text-[10px] font-bold text-muted-foreground">
                                <span className="rounded-full bg-muted px-2 py-0.5">
                                  {activity.ageLabel}
                                </span>
                                <span className="flex items-center gap-1 rounded-full bg-muted px-2 py-0.5">
                                  <Clock3 className="h-2.5 w-2.5" aria-hidden="true" />
                                  {activity.durationLabel}
                                </span>
                                <span
                                  className="flex items-center gap-1 rounded-full bg-muted px-2 py-0.5"
                                  title={activity.materialLabel}
                                >
                                  <Pencil className="h-2.5 w-2.5" aria-hidden="true" />
                                  {activity.materialLabel}
                                </span>
                              </div>
                            </div>
                          </label>
                        );
                      })}
                    </div>
                  </div>
                ))}
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
            : `Continuar com ${pluralize(landmarkActivitySelections.length, 'atividade', 'atividades')}`}
        </Button>
      </div>
    </div>
  );
};

export default StepActivities;
