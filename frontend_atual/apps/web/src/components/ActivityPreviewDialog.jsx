import React, { useState } from 'react';
import { Check, Clock3, Pencil, Plus, Users } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { activityGallery } from '@/utils/landmark-activities.js';

/**
 * Página inteira da atividade em tamanho de leitura.
 *
 * O card compacto mostra só o topo da página numa miniatura de 3:2 — dá para
 * reconhecer, não para julgar. Aqui a família vê a folha inteira, e nos
 * quebra-cabeças vê também a versão resolvida, que é o que responde de
 * verdade "o que essa atividade é".
 */
const ActivityPreviewDialog = ({ activity, landmarkName, selected, onToggle, open, onOpenChange }) => {
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
            className="w-full rounded-2xl border-2 border-border bg-muted"
          />
          <figcaption className="text-center text-sm font-medium text-muted-foreground">
            {shown.caption}
          </figcaption>
        </figure>

        <div className="flex flex-col gap-3 border-t border-border/60 pt-4 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-sm font-medium text-muted-foreground">
            Será adaptada para {landmarkName}.
          </p>
          <Button
            type="button"
            onClick={() => {
              onToggle();
              onOpenChange(false);
            }}
            variant={selected ? 'outline' : 'default'}
            className="rounded-full px-6 py-5 font-bold"
          >
            {selected ? (
              <><Check className="mr-2 h-4 w-4" aria-hidden="true" /> Tirar do guia</>
            ) : (
              <><Plus className="mr-2 h-4 w-4" aria-hidden="true" /> Incluir no guia</>
            )}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default ActivityPreviewDialog;
