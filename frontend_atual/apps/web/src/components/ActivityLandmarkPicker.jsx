import React from 'react';
import { Check, ChevronDown, MapPin } from 'lucide-react';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { countryHasPhrasebook } from '@/utils/landmark-activities.js';

const landmarkId = (landmark) => landmark.selection_id || landmark.id;

/**
 * Motivo pelo qual um ponto não aceita esta atividade agora.
 *
 * Desabilitar sem dizer por quê faria a família clicar de novo achando que
 * quebrou; a frase curta resolve na hora.
 */
export const unavailableReason = ({ activity, landmark, assigned, perLandmarkLimit, guideFull }) => {
  if (activity.type === 'language_survival' && !countryHasPhrasebook(landmark.country)) {
    return `Ainda não temos o guia de frases para ${landmark.country || 'este país'}`;
  }
  if (assigned.length >= perLandmarkLimit) {
    return `Já tem ${perLandmarkLimit} atividades neste ponto`;
  }
  if (guideFull) return 'O guia já está no limite de páginas opcionais';
  return '';
};

const ActivityLandmarkPicker = ({
  activity,
  landmarks,
  selections,
  perLandmarkLimit,
  guideFull,
  chosenIds,
  onToggle,
}) => {
  const label = chosenIds.length === 0
    ? 'Escolher pontos'
    : chosenIds.length === 1
      ? landmarks.find((item) => landmarkId(item) === chosenIds[0])?.name || '1 ponto'
      : `Em ${chosenIds.length} pontos`;

  return (
    <Popover>
      <PopoverTrigger asChild>
        <button
          type="button"
          aria-label={`Escolher em quais pontos incluir ${activity.label}`}
          className={`flex min-h-11 w-full items-center justify-between gap-2 rounded-xl border-2 px-3 py-2 text-xs font-bold transition ${
            chosenIds.length > 0
              ? 'border-primary bg-primary/10 text-primary'
              : 'border-border/70 bg-background text-muted-foreground hover:border-primary/45 hover:text-foreground'
          }`}
        >
          <span className="flex min-w-0 items-center gap-1.5">
            <MapPin className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
            <span className="truncate">{label}</span>
          </span>
          <ChevronDown className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
        </button>
      </PopoverTrigger>
      <PopoverContent align="start" className="w-72 p-2">
        <p className="px-2 pb-2 pt-1 text-xs font-semibold text-muted-foreground">
          Incluir em
        </p>
        <ul className="space-y-0.5">
          {landmarks.map((landmark) => {
            const id = landmarkId(landmark);
            const chosen = chosenIds.includes(id);
            const assigned = selections.filter(
              (selection) => selection.landmark_selection_id === id,
            );
            const reason = chosen
              ? ''
              : unavailableReason({
                  activity,
                  landmark,
                  assigned,
                  perLandmarkLimit,
                  guideFull,
                });
            return (
              <li key={id}>
                <button
                  type="button"
                  disabled={Boolean(reason)}
                  onClick={() => onToggle(id)}
                  title={reason || undefined}
                  className={`flex min-h-11 w-full items-start gap-2 rounded-lg px-2 py-2 text-left transition disabled:cursor-not-allowed disabled:opacity-45 ${
                    chosen ? 'bg-primary/10' : 'hover:bg-muted/70'
                  }`}
                >
                  <span
                    className={`mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded border-2 ${
                      chosen ? 'border-primary bg-primary text-white' : 'border-border bg-background'
                    }`}
                    aria-hidden="true"
                  >
                    {chosen && <Check className="h-3.5 w-3.5" />}
                  </span>
                  <span className="min-w-0">
                    <span className="block truncate text-sm font-bold text-foreground">
                      {landmark.name}
                    </span>
                    <span className="block truncate text-xs font-medium text-muted-foreground">
                      {reason || `${assigned.length}/${perLandmarkLimit} atividades`}
                    </span>
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
      </PopoverContent>
    </Popover>
  );
};

export default ActivityLandmarkPicker;
