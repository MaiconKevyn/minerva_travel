import React, { useState } from 'react';
import { Bookmark, Loader2, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';

const GuideDraftActions = ({ hasDraft, busy, onContinueLater, onDiscard }) => {
  const [discardOpen, setDiscardOpen] = useState(false);
  const [discarding, setDiscarding] = useState(false);

  if (!hasDraft) return null;

  const handleDiscard = async (event) => {
    event.preventDefault();
    setDiscarding(true);
    const discarded = await onDiscard();
    setDiscarding(false);
    if (discarded) setDiscardOpen(false);
  };

  return (
    <div className="flex flex-wrap justify-end gap-2" aria-label="Ações do rascunho">
      <Button
        type="button"
        variant="outline"
        onClick={onContinueLater}
        disabled={busy || discarding}
        className="font-ui h-11 rounded-lg border-secondary/25 bg-[hsl(var(--paper)/0.86)] px-3 text-xs font-semibold text-secondary sm:px-4 sm:text-sm"
      >
        {busy ? (
          <Loader2 className="h-4 w-4 animate-spin motion-reduce:animate-none" aria-hidden="true" />
        ) : (
          <Bookmark className="h-4 w-4" aria-hidden="true" />
        )}
        Continuar depois
      </Button>

      <Button
        type="button"
        variant="ghost"
        onClick={() => setDiscardOpen(true)}
        disabled={busy || discarding}
        className="font-ui h-11 rounded-lg px-3 text-xs font-semibold text-muted-foreground hover:bg-destructive/10 hover:text-destructive sm:text-sm"
      >
        <Trash2 className="h-4 w-4" aria-hidden="true" />
        Descartar
      </Button>

      <AlertDialog open={discardOpen} onOpenChange={setDiscardOpen}>
        <AlertDialogContent className="clean-surface max-w-lg border-destructive/20">
          <AlertDialogHeader>
            <AlertDialogTitle className="font-display text-2xl font-bold text-secondary">
              Descartar este rascunho?
            </AlertDialogTitle>
            <AlertDialogDescription className="font-ui leading-relaxed text-muted-foreground">
              O roteiro, a família, as atividades e o progresso desta criação serão removidos.
              Esta ação não pode ser desfeita.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={discarding} className="rounded-lg">
              Manter rascunho
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDiscard}
              disabled={discarding}
              className="rounded-lg bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {discarding && (
                <Loader2 className="h-4 w-4 animate-spin motion-reduce:animate-none" aria-hidden="true" />
              )}
              Descartar definitivamente
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
};

export default GuideDraftActions;
