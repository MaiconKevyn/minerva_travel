import React from 'react';
import { AlertCircle, CheckCircle2, Cloud, Loader2 } from 'lucide-react';

const statusConfig = {
  saving: {
    Icon: Loader2,
    className: 'border-secondary/15 bg-secondary/5 text-secondary',
    iconClassName: 'animate-spin motion-reduce:animate-none',
    message: 'Salvando as escolhas mais recentes…',
  },
  saved: {
    Icon: CheckCircle2,
    className: 'border-emerald-700/15 bg-emerald-500/10 text-emerald-800 dark:text-emerald-200',
    message: 'Tudo salvo. Você pode continuar depois.',
  },
  local: {
    Icon: Cloud,
    className: 'border-amber-700/15 bg-amber-500/10 text-amber-900 dark:text-amber-100',
  },
  error: {
    Icon: AlertCircle,
    className: 'border-destructive/20 bg-destructive/10 text-destructive',
  },
};

const DraftStatusNotice = ({
  status,
  error,
  restoredProgress,
  builderSessionId,
  hasUnsavedPhoto,
}) => {
  const config = statusConfig[status];
  if (!config) return null;

  const restoredMessage = restoredProgress && builderSessionId
    ? 'Progresso recuperado. Suas páginas geradas continuam salvas com segurança.'
    : restoredProgress
      ? 'Seu rascunho foi recuperado e está salvo.'
      : '';
  const savedMessage = hasUnsavedPhoto
    ? 'Roteiro salvo. Por privacidade, escolha a foto novamente quando retomar.'
    : config.message;
  const message = error || restoredMessage || savedMessage;
  if (!message) return null;

  const { Icon } = config;
  const isError = status === 'error';
  return (
    <div
      className={`mt-3 flex items-start gap-2 rounded-2xl border px-4 py-3 font-ui text-sm font-bold ${config.className}`}
      role={isError ? 'alert' : 'status'}
      aria-live={isError ? 'assertive' : 'polite'}
    >
      <Icon className={`mt-0.5 h-4 w-4 shrink-0 ${config.iconClassName || ''}`} aria-hidden="true" />
      <span>{message}</span>
    </div>
  );
};

export default DraftStatusNotice;
