import React, { useCallback, useEffect, useRef, useState } from 'react';
import { AlertCircle, FolderOpen, Loader2, RefreshCw, Save, Trash2, UsersRound } from 'lucide-react';
import { toast } from 'sonner';
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
import {
  familyFormFromProfile,
  familyProfileFromForm,
  pluralize,
} from '@/utils/guide-form.js';
import {
  deleteFamilyProfile,
  getFamilyProfile,
  saveFamilyProfile,
} from '@/utils/minerva-api.js';

const savedAtLabel = (isoDate) => {
  const date = new Date(isoDate);
  return Number.isNaN(date.getTime())
    ? ''
    : date.toLocaleDateString('pt-BR', { day: '2-digit', month: 'long', year: 'numeric' });
};

const profileSummary = (profile) => [
  pluralize(profile.parents.length, 'responsável', 'responsáveis'),
  pluralize(profile.children.length, 'criança', 'crianças'),
].join(' · ');

/**
 * Os dados reutilizáveis da família, guardados uma vez e recarregados a cada
 * novo guia. Foto e consentimento ficam de fora de propósito: cada guia pede
 * os dois de novo.
 */
const SavedFamilyPanel = ({ tripYear, collectFamilyData, onLoad }) => {
  const [profile, setProfile] = useState(null);
  const [status, setStatus] = useState('loading');
  const [loadError, setLoadError] = useState('');
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const mountedRef = useRef(true);

  useEffect(() => () => {
    mountedRef.current = false;
  }, []);

  const fetchProfile = useCallback(async ({ signal } = {}) => {
    setStatus('loading');
    setLoadError('');
    try {
      const saved = await getFamilyProfile({ signal });
      if (!mountedRef.current || signal?.aborted) return;
      setProfile(saved);
      setStatus('idle');
    } catch (error) {
      if (!mountedRef.current || signal?.aborted) return;
      // Uma falha aqui não pode travar a etapa: a família ainda consegue
      // digitar tudo e seguir para a próxima parte do guia.
      setLoadError(error?.message || 'Não foi possível verificar os dados salvos.');
      setStatus('idle');
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    fetchProfile({ signal: controller.signal });
    return () => controller.abort();
  }, [fetchProfile]);

  const handleSave = async () => {
    const collected = collectFamilyData();
    if (!collected) return;

    setStatus('saving');
    try {
      const saved = await saveFamilyProfile({
        ...familyProfileFromForm(collected, tripYear),
        revision: profile?.revision ?? null,
      });
      if (!mountedRef.current) return;
      setProfile(saved);
      setStatus('idle');
      toast.success('Dados da família salvos', {
        description: 'No próximo guia é só tocar em "Carregar dados salvos".',
      });
    } catch (error) {
      if (!mountedRef.current) return;
      setStatus('idle');
      if (error?.code === 'family_profile_revision_conflict') {
        // Outra aba salvou primeiro. Sobrescrever apagaria o que ela guardou.
        await fetchProfile();
        toast.error('Os dados foram alterados em outra aba', {
          description: 'Recarregamos o que está salvo. Confira antes de salvar de novo.',
        });
        return;
      }
      toast.error('Não foi possível salvar', {
        description: error?.message || 'Tente novamente em instantes.',
      });
    }
  };

  const handleLoad = () => {
    if (!profile) return;
    const form = familyFormFromProfile(profile, tripYear);
    onLoad(form);
    if (form.needingAgeReview.length > 0) {
      toast.warning('Confira a idade', {
        description: `Informe a idade de ${form.needingAgeReview.join(', ')} para esta viagem.`,
      });
      return;
    }
    toast.success('Dados carregados', {
      description: 'As idades foram estimadas para o ano da viagem. Confira antes de seguir.',
    });
  };

  const handleDelete = async () => {
    setConfirmingDelete(false);
    setStatus('saving');
    try {
      await deleteFamilyProfile();
      if (!mountedRef.current) return;
      setProfile(null);
      setStatus('idle');
      toast.success('Dados salvos apagados');
    } catch (error) {
      if (!mountedRef.current) return;
      setStatus('idle');
      toast.error('Não foi possível apagar', {
        description: error?.message || 'Tente novamente em instantes.',
      });
    }
  };

  const busy = status === 'loading' || status === 'saving';

  return (
    <section
      aria-labelledby="saved-family-title"
      className="rounded-[2rem] border-2 border-dashed border-primary/25 bg-primary/5 p-6 md:p-8"
    >
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <div className="rounded-xl bg-primary/10 p-2 text-primary">
            <UsersRound className="h-6 w-6" aria-hidden="true" />
          </div>
          <div>
            <h3 id="saved-family-title" className="text-lg font-bold text-foreground sm:text-xl">
              Dados da família
            </h3>
            {status === 'loading' ? (
              <p className="mt-1 flex items-center gap-2 text-sm font-medium text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                Verificando o que você já salvou…
              </p>
            ) : profile ? (
              <p className="mt-1 text-sm font-medium text-muted-foreground">
                <strong className="text-foreground">{profile.family_name}</strong>
                {' — '}
                {profileSummary(profile)}
                {profile.updated_at && `, salvos em ${savedAtLabel(profile.updated_at)}`}
              </p>
            ) : (
              <p className="mt-1 text-sm font-medium text-muted-foreground">
                Preencha abaixo e salve: no próximo guia você só precisa montar o roteiro.
              </p>
            )}
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {profile && (
            <Button
              type="button"
              onClick={handleLoad}
              disabled={busy}
              className="rounded-full bg-primary px-5 font-bold text-white hover:bg-primary/90"
            >
              <FolderOpen className="mr-2 h-4 w-4" aria-hidden="true" />
              Carregar dados salvos
            </Button>
          )}
          <Button
            type="button"
            variant="outline"
            onClick={handleSave}
            disabled={busy}
            className="rounded-full border-2 px-5 font-bold"
          >
            {status === 'saving' ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />
            ) : (
              <Save className="mr-2 h-4 w-4" aria-hidden="true" />
            )}
            {profile ? 'Atualizar os salvos' : 'Salvar dados da família'}
          </Button>
        </div>
      </div>

      {loadError && (
        <p
          role="status"
          className="mt-4 flex flex-wrap items-center gap-2 text-sm font-medium text-muted-foreground"
        >
          <AlertCircle className="h-4 w-4 shrink-0 text-destructive" aria-hidden="true" />
          {loadError}
          <button
            type="button"
            onClick={() => fetchProfile()}
            className="inline-flex items-center gap-1 font-bold text-primary underline underline-offset-4"
          >
            <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />
            Tentar de novo
          </button>
        </p>
      )}

      <p className="mt-4 text-xs font-medium text-muted-foreground">
        Guardamos nomes e o ano de nascimento das crianças — nunca a foto da capa, que cada guia
        pede de novo. Carregar substitui o que estiver escrito abaixo.
      </p>

      {profile && (
        <div className="mt-3">
          <button
            type="button"
            onClick={() => setConfirmingDelete(true)}
            disabled={busy}
            className="inline-flex items-center gap-1.5 text-xs font-bold text-muted-foreground underline underline-offset-4 hover:text-destructive disabled:opacity-50"
          >
            <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
            Apagar dados salvos
          </button>
        </div>
      )}

      <AlertDialog open={confirmingDelete} onOpenChange={setConfirmingDelete}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Apagar os dados salvos da família?</AlertDialogTitle>
            <AlertDialogDescription>
              O guia em andamento e os guias já criados continuam como estão. Só deixamos de
              guardar os nomes para preencher o próximo.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction onClick={handleDelete}>Apagar</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </section>
  );
};

export default SavedFamilyPanel;
