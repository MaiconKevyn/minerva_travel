import React from 'react';
import { MapPin, X } from 'lucide-react';
import { activityPlanByLandmark } from '@/utils/landmark-activities.js';

/**
 * O plano de cada parada, montado a partir das escolhas do catálogo.
 *
 * Sem isto, escolher por atividade esconderia a distribuição: dá para
 * empilhar seis no primeiro ponto e deixar o último sem nada, e só descobrir
 * com o guia impresso na mão.
 */
const ActivityPlanSummary = ({ landmarks, selections, onRemove }) => {
  const plan = activityPlanByLandmark(selections, landmarks);
  const total = selections.length;

  return (
    <section
      className="rounded-2xl border border-primary/25 bg-primary/[0.04] p-5 sm:p-6"
      aria-labelledby="activity-plan-title"
    >
      <div className="mb-4 flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
        <h3 id="activity-plan-title" className="text-xl font-display font-bold text-foreground">
          O plano de cada parada
        </h3>
        <p className="text-sm font-medium text-muted-foreground" aria-live="polite">
          {total === 0
            ? 'Nada escolhido ainda'
            : `${total} ${total === 1 ? 'atividade escolhida' : 'atividades escolhidas'}`}
        </p>
      </div>

      <ul className="space-y-3">
        {plan.map(({ landmark, selectionId, activities }) => (
          <li
            key={selectionId}
            className="clean-surface flex flex-col gap-2 p-3 sm:flex-row sm:items-start sm:gap-4"
          >
            <p className="flex min-w-0 items-center gap-1.5 text-sm font-bold text-foreground sm:w-52 sm:shrink-0">
              <MapPin className="h-3.5 w-3.5 shrink-0 text-primary" aria-hidden="true" />
              <span className="truncate">{landmark.name}</span>
            </p>
            {activities.length === 0 ? (
              <p className="text-sm font-medium text-muted-foreground">
                Nenhuma atividade ainda.
              </p>
            ) : (
              <ul className="flex flex-wrap gap-1.5">
                {activities.map((activity) => (
                  <li key={activity.type}>
                    <button
                      type="button"
                      onClick={() => onRemove(selectionId, activity.type)}
                      aria-label={`Tirar ${activity.label} de ${landmark.name}`}
                      className="group flex items-center gap-1 rounded-full bg-primary/10 py-1 pl-3 pr-2 text-xs font-bold text-primary transition hover:bg-destructive/15 hover:text-destructive"
                    >
                      {activity.label}
                      <X className="h-3 w-3" aria-hidden="true" />
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
};

export default ActivityPlanSummary;
