import React, { useState } from 'react';
import { Check, Clock3, MapPin, Pencil, Users } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { activityGallery, countryHasPhrasebook } from '@/utils/landmark-activities.js';

/**
 * Página inteira da atividade em tamanho de leitura.
 *
 * O card compacto mostra só o topo da página numa miniatura de 3:2 — dá para
 * reconhecer, não para julgar. Aqui a família vê a folha inteira, e nos
 * quebra-cabeças vê também a versão resolvida, que é o que responde de
 * verdade "o que essa atividade é".
 */
const ActivityPreviewDialog = ({ activity, landmarks, chosenIds, onToggle, open, onOpenChange }) => {
  const gallery = activityGallery(activity);
  const [shownIndex, setShownIndex] = useState(0);
  const shown = gallery[Math.min(shownIndex, gallery.length - 1)];

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (!next) setShownIndex(0);
        onOpenChange(next);
      }}
    >
      <DialogContent className="max-h-[92vh] max-w-3xl overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="font-serif text-2xl">{activity.label}</DialogTitle>
          <DialogDescription className="text-base">
            {activity.about || activity.description}
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-wrap gap-2 text-xs font-bold text-muted-foreground">
          <span className="flex items-center gap-1 rounded-full bg-muted px-3 py-1">
            <Users className="h-3.5 w-3.5" aria-hidden="true" />
            {activity.ageLabel}
          </span>
          <span className="flex items-center gap-1 rounded-full bg-muted px-3 py-1">
            <Clock3 className="h-3.5 w-3.5" aria-hidden="true" />
            {activity.durationLabel}
          </span>
          <span className="flex items-center gap-1 rounded-full bg-muted px-3 py-1">
            <Pencil className="h-3.5 w-3.5" aria-hidden="true" />
            {activity.materialLabel}
          </span>
        </div>

        {gallery.length > 1 && (
          <div className="flex flex-wrap gap-2" role="tablist" aria-label="Versões da página">
            {gallery.map((item, index) => (
              <button
                key={item.src}
                type="button"
                role="tab"
                aria-selected={index === shownIndex}
                onClick={() => setShownIndex(index)}
                className={`rounded-full px-4 py-1.5 text-sm font-bold transition ${
                  index === shownIndex
                    ? 'bg-primary text-white'
                    : 'bg-muted text-muted-foreground hover:text-foreground'
                }`}
              >
                {item.label}
              </button>
            ))}
          </div>
        )}

        <figure className="space-y-2">
          <img
            src={shown.src}
            alt={`${activity.label} — ${shown.label}`}
            className="w-full rounded-xl border-2 border-border bg-muted"
          />
          <figcaption className="text-center text-sm font-medium text-muted-foreground">
            {shown.caption}
          </figcaption>
        </figure>

        {/* Decidir aqui evita fechar o modal só para marcar a parada: a
            página inteira continua à vista enquanto a família escolhe. */}
        <div className="space-y-2 border-t border-border/60 pt-4">
          <p className="flex items-center gap-1.5 text-sm font-bold text-foreground">
            <MapPin className="h-4 w-4 text-primary" aria-hidden="true" />
            Em quais paradas esta página entra?
          </p>
          <div className="flex flex-wrap gap-2">
            {landmarks.map((landmark) => {
              const id = landmark.selection_id || landmark.id;
              const chosen = chosenIds.includes(id);
              const blocked =
                activity.type === 'language_survival' && !countryHasPhrasebook(landmark.country);
              return (
                <button
                  key={id}
                  type="button"
                  disabled={blocked && !chosen}
                  onClick={() => onToggle(id, activity.type)}
                  title={
                    blocked
                      ? `Ainda não temos o guia de frases para ${landmark.country || 'este país'}`
                      : undefined
                  }
                  className={`flex items-center gap-1.5 rounded-full border-2 px-4 py-2 text-sm font-bold transition disabled:cursor-not-allowed disabled:opacity-45 ${
                    chosen
                      ? 'border-primary bg-primary text-white'
                      : 'border-border/70 bg-background text-muted-foreground hover:border-primary/45 hover:text-foreground'
                  }`}
                >
                  {chosen && <Check className="h-3.5 w-3.5" aria-hidden="true" />}
                  {landmark.name}
                </button>
              );
            })}
          </div>
          <p className="text-xs font-medium text-muted-foreground">
            A página é adaptada para cada parada que você marcar.
          </p>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default ActivityPreviewDialog;
