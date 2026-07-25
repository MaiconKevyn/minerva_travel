import React, { useEffect, useState } from 'react';
import { BookOpen } from 'lucide-react';
import { fetchGuideCoverObjectUrl } from '@/utils/minerva-api.js';

/**
 * Capa do guia no painel. O produto entrega livros ilustrados, então a lista
 * mostra a capa de cada um — mas a rota é privada e exige token, por isso a
 * imagem é buscada e convertida em object URL em vez de ir direto no `src`.
 *
 * Guias antigos (gerados antes da miniatura existir) e falhas de rede caem no
 * placeholder ilustrado: a lista nunca mostra imagem quebrada.
 */
const GuideCover = ({ coverUrl, title }) => {
  const [objectUrl, setObjectUrl] = useState('');
  const [isLoading, setIsLoading] = useState(Boolean(coverUrl));

  useEffect(() => {
    if (!coverUrl) {
      setObjectUrl('');
      setIsLoading(false);
      return undefined;
    }

    let revokedUrl = '';
    const controller = new AbortController();
    setIsLoading(true);

    fetchGuideCoverObjectUrl(coverUrl, { signal: controller.signal })
      .then((url) => {
        revokedUrl = url;
        setObjectUrl(url);
      })
      .catch((error) => {
        if (error.name !== 'AbortError') {
          console.error('Erro ao carregar a capa do guia:', error);
          setObjectUrl('');
        }
      })
      .finally(() => setIsLoading(false));

    return () => {
      controller.abort();
      if (revokedUrl) URL.revokeObjectURL(revokedUrl);
    };
  }, [coverUrl]);

  return (
    <div className="w-20 shrink-0 xl:w-24">
      <div className="aspect-[3/4] overflow-hidden rounded-xl border border-border/60 bg-muted shadow-sm">
        {objectUrl ? (
          <img
            src={objectUrl}
            alt={`Capa do guia ${title || 'da família'}`}
            className="h-full w-full object-cover"
            loading="lazy"
          />
        ) : (
          <div
            className={`flex h-full w-full items-center justify-center bg-gradient-to-br from-muted to-accent/15 ${
              isLoading ? 'animate-pulse' : ''
            }`}
          >
            {!isLoading && (
              <BookOpen className="h-7 w-7 text-muted-foreground/60" aria-hidden="true" />
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default GuideCover;
