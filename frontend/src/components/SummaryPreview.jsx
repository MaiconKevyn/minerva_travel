import React from 'react';
import { Download, MapPin, Sparkles, Users } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { absoluteDownloadUrl } from '@/lib/api.js';
import { Flower } from './DecorativeElements.jsx';

const SummaryPreview = ({ formData, catalog, result }) => {
  const { photo, title, year, parents, children, selectedLandmarks, customLandmarksText } = formData;
  const photoUrl = photo
    ? URL.createObjectURL(photo)
    : 'https://images.unsplash.com/photo-1583325033548-1eeacdb0b16e?auto=format&fit=crop&q=80&w=800';
  const selectedByDestination = catalog.destinations
    .map((destination) => ({
      destination,
      landmarks: destination.landmarks.filter((landmark) =>
        selectedLandmarks.has(landmark.selection_id)
      ),
    }))
    .filter((item) => item.landmarks.length > 0);

  return (
    <div className="space-y-8">
      <div className="text-center max-w-2xl mx-auto">
        <h3 className="text-4xl font-serif font-bold mb-3 flex items-center justify-center gap-3">
          <Sparkles className="w-8 h-8 text-primary" />
          Revisao do Guia
          <Sparkles className="w-8 h-8 text-primary" />
        </h3>
        <p className="text-muted-foreground text-lg">
          Confira os dados antes de gerar a capa ilustrada e montar o PDF.
        </p>
      </div>

      <div className="grid gap-8 lg:grid-cols-[minmax(0,360px)_1fr] lg:items-start">
        <div className="flex justify-center">
          <div className="w-full max-w-sm aspect-[3/4] rounded-r-3xl rounded-l-md book-spine-shadow bg-[#FDFBF7] relative overflow-hidden border-2 border-r-4 border-[#eaddc4] flex flex-col items-center p-7">
            <Flower className="absolute top-4 left-6 w-8 h-8 text-secondary/40" />
            <Flower className="absolute top-4 right-6 w-8 h-8 text-primary/40" />

            <div className="text-center space-y-2 mb-5 mt-3">
              <h4 className="text-xs font-bold tracking-[0.2em] text-secondary uppercase">Aventuras Inesqueciveis</h4>
              <h2 className="text-3xl font-serif font-bold text-foreground leading-tight">
                {title || 'Guia de Viagem'}
              </h2>
            </div>

            <div className="relative w-full max-w-[220px] aspect-square rounded-full border-[10px] border-white shadow-xl mx-auto overflow-hidden bg-muted z-10 mb-6">
              <img
                src={photoUrl}
                alt="Previa da capa do guia"
                className="w-full h-full object-cover"
              />
            </div>

            <div className="flex items-center gap-2 text-foreground/70 mb-5 text-center">
              <Users className="w-4 h-4 shrink-0" />
              <span className="font-medium text-sm">
                Com: {children.length > 0 ? children.join(', ') : 'Aventureiros'}
              </span>
            </div>

            <div className="mt-auto w-[112%] -ml-4 bg-secondary py-4 px-6 text-center shadow-lg transform -rotate-2">
              <p className="text-white font-serif font-semibold text-base flex items-center justify-center gap-2">
                <MapPin className="w-5 h-5 shrink-0" />
                {year}
              </p>
            </div>

            <div className="absolute top-0 bottom-0 left-3 w-1 bg-black/5 mix-blend-multiply" />
            <div className="absolute top-0 bottom-0 left-6 w-0.5 bg-black/5 mix-blend-multiply" />
          </div>
        </div>

        <div className="space-y-5">
          <ReviewBlock label="Criancas" value={children.join(', ') || 'Nenhuma crianca informada'} />
          <ReviewBlock label="Pais ou responsaveis" value={parents.join(', ') || 'Nenhum responsavel informado'} />

          <div className="rounded-3xl border border-border bg-background/70 p-5">
            <p className="text-sm font-bold uppercase tracking-[0.16em] text-muted-foreground">
              Roteiro selecionado
            </p>
            <div className="mt-4 space-y-4">
              {selectedByDestination.map(({ destination, landmarks }) => (
                <div key={destination.id}>
                  <p className="font-serif text-xl font-bold text-foreground">{destination.city}</p>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {landmarks.map((landmark) => (
                      <span
                        key={landmark.selection_id}
                        className="rounded-full bg-white px-3 py-1 text-sm font-medium text-muted-foreground border border-border"
                      >
                        {landmark.name}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {customLandmarksText?.trim() && (
            <div className="rounded-3xl border border-accent/40 bg-accent/10 p-5">
              <p className="text-sm font-bold uppercase tracking-[0.16em] text-muted-foreground">
                Pontos adicionados livremente
              </p>
              <div className="mt-3 flex flex-wrap gap-2">
                {customLandmarksText
                  .split('\n')
                  .map((line) => line.trim())
                  .filter(Boolean)
                  .map((line, index) => (
                    <span
                      key={`${line}-${index}`}
                      className="rounded-full bg-white px-3 py-1 text-sm font-medium text-muted-foreground border border-border"
                    >
                      {line}
                    </span>
                  ))}
              </div>
            </div>
          )}

          {result && (
            <div className="rounded-3xl border-2 border-secondary/30 bg-secondary/10 p-6">
              <p className="font-serif text-2xl font-bold text-foreground">PDF pronto</p>
              <p className="mt-2 text-muted-foreground">
                A capa foi gerada e o guia foi montado com o roteiro selecionado.
              </p>
              <Button
                asChild
                className="mt-5 rounded-full bg-secondary px-7 py-6 text-base text-white hover:bg-secondary/90"
              >
                <a href={absoluteDownloadUrl(result.download_url)}>
                  <Download className="mr-2 h-5 w-5" />
                  Baixar PDF
                </a>
              </Button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

function ReviewBlock({ label, value }) {
  return (
    <div className="rounded-3xl border border-border bg-background/70 p-5">
      <p className="text-sm font-bold uppercase tracking-[0.16em] text-muted-foreground">{label}</p>
      <p className="mt-2 text-lg font-semibold text-foreground">{value}</p>
    </div>
  );
}

export default SummaryPreview;
