import React from 'react';
import {
  CheckSquare,
  Loader2,
  Map as MapIcon,
  MapPin,
  MessageSquareText,
  Plus,
  Square,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { motion } from 'framer-motion';
import WarmCard from './WarmCard.jsx';
import { Suitcase } from './DecorativeElements.jsx';

const CountryAttractionSelector = ({
  catalog,
  selectedLandmarks,
  landmarkMessage,
  onLandmarkMessageChange,
  landmarkPreview,
  isParsingLandmarks,
  onParseLandmarkMessage,
  customLandmarksText,
  onCustomLandmarksTextChange,
  onToggleLandmark,
  onSelectDestination,
  error,
}) => {
  const selectedCount = selectedLandmarks.size;
  const totalCount = catalog.destinations.reduce(
    (count, destination) => count + destination.landmarks.length,
    0
  );

  return (
    <WarmCard className="border-t-4 border-t-accent relative">
      <Suitcase className="absolute -top-4 right-8 w-16 h-16 text-accent opacity-20 rotate-[-15deg]" />

      <div className="mb-8 flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <h3 className="text-3xl font-serif font-bold mb-2 flex items-center gap-3">
            <MapIcon className="w-8 h-8 text-accent" />
            Roteiro da Europa
          </h3>
          <p className="text-muted-foreground text-lg">
            Escolha quais pontos turisticos entram no guia final.
          </p>
        </div>
        <div className="rounded-full bg-accent/15 px-5 py-2 text-sm font-bold text-foreground">
          {selectedCount} de {totalCount} selecionados
        </div>
      </div>

      <div className="space-y-6">
        {catalog.destinations.map((destination) => {
          const allSelected = destination.landmarks.every((landmark) =>
            selectedLandmarks.has(landmark.selection_id)
          );
          const selectedInDestination = destination.landmarks.filter((landmark) =>
            selectedLandmarks.has(landmark.selection_id)
          ).length;

          return (
            <motion.section
              key={destination.id}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.2 }}
              className="bg-white rounded-3xl p-6 shadow-sm border border-border space-y-5"
            >
              <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                <div className="flex items-start gap-4">
                  <div className="w-12 h-12 bg-accent/20 rounded-2xl flex items-center justify-center flex-shrink-0">
                    <MapPin className="w-6 h-6 text-accent" />
                  </div>
                  <div>
                    <h4 className="text-2xl font-serif font-bold">{destination.display_title}</h4>
                    <p className="mt-1 text-sm text-muted-foreground">
                      {selectedInDestination} de {destination.landmarks.length} locais selecionados
                    </p>
                  </div>
                </div>

                <Button
                  type="button"
                  variant="outline"
                  onClick={() => onSelectDestination(destination.id, !allSelected)}
                  className="rounded-full border-accent/40 text-foreground hover:bg-accent hover:text-accent-foreground"
                >
                  {allSelected ? (
                    <CheckSquare className="w-4 h-4 mr-2" />
                  ) : (
                    <Square className="w-4 h-4 mr-2" />
                  )}
                  {allSelected ? 'Remover cidade' : 'Selecionar cidade'}
                </Button>
              </div>

              <div className="grid gap-3 md:grid-cols-2">
                {destination.landmarks.map((landmark) => {
                  const selected = selectedLandmarks.has(landmark.selection_id);

                  return (
                    <button
                      key={landmark.selection_id}
                      type="button"
                      onClick={() => onToggleLandmark(landmark.selection_id)}
                      className={`text-left rounded-2xl border p-4 transition-all duration-200 ${
                        selected
                          ? 'border-accent bg-accent/10 shadow-sm'
                          : 'border-border bg-background/60 hover:border-accent/60 hover:bg-white'
                      }`}
                    >
                      <div className="flex items-start gap-3">
                        <span
                          className={`mt-0.5 flex h-6 w-6 items-center justify-center rounded-lg border ${
                            selected
                              ? 'border-accent bg-accent text-accent-foreground'
                              : 'border-border bg-white text-transparent'
                          }`}
                        >
                          <CheckSquare className="h-4 w-4" />
                        </span>
                        <span>
                          <span className="block font-bold text-foreground">{landmark.name}</span>
                          <span className="mt-1 line-clamp-2 block text-sm leading-6 text-muted-foreground">
                            {landmark.description[0]}
                          </span>
                        </span>
                      </div>
                    </button>
                  );
                })}
              </div>
            </motion.section>
          );
        })}

        <section className="bg-white rounded-3xl p-6 shadow-sm border border-dashed border-accent/50 space-y-5">
          <div className="flex items-start gap-4">
            <div className="w-12 h-12 bg-accent/20 rounded-2xl flex items-center justify-center flex-shrink-0">
              <MessageSquareText className="w-6 h-6 text-accent" />
            </div>
            <div>
              <h4 className="text-2xl font-serif font-bold">Adicionar por linguagem natural</h4>
              <p className="mt-1 text-sm leading-6 text-muted-foreground">
                Escreva os lugares que a familia pretende visitar. Vamos separar os pontos,
                organizar os pontos em cards para confirmacao.
              </p>
            </div>
          </div>

          <Textarea
            value={landmarkMessage}
            onChange={(event) => onLandmarkMessageChange(event.target.value)}
            placeholder={'Em Paris queremos visitar Torre Eiffel, Louvre e Arco do Triunfo. Em Londres vamos ver Big Ben e London Eye.'}
            className="min-h-32 rounded-2xl bg-background border-border text-base leading-7 focus-visible:ring-accent"
          />

          <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
            <Button
              type="button"
              onClick={onParseLandmarkMessage}
              disabled={isParsingLandmarks}
              className="rounded-full bg-accent px-6 text-accent-foreground hover:bg-accent/90"
            >
              {isParsingLandmarks ? (
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              ) : (
                <Plus className="w-4 h-4 mr-2" />
              )}
              Interpretar pontos turisticos
            </Button>
            {customLandmarksText.trim() && (
              <span className="text-sm font-medium text-muted-foreground">
                {customLandmarksText.split('\n').filter(Boolean).length} pontos prontos para o guia
              </span>
            )}
          </div>

          {landmarkPreview && (
            <div className="space-y-5">
              {landmarkPreview.destinations.map((destination) => (
                <div key={destination.id} className="space-y-3">
                  <div>
                    <p className="font-serif text-xl font-bold text-foreground">
                      {destination.city}
                    </p>
                    <p className="text-sm text-muted-foreground">{destination.country}</p>
                  </div>
                  <div className="grid gap-4 md:grid-cols-2">
                    {destination.landmarks.map((landmark) => (
                      <article
                        key={landmark.selection_id}
                        className="rounded-2xl border border-border bg-background p-4"
                      >
                        <p className="font-bold text-foreground">{landmark.name}</p>
                        <p className="mt-1 text-sm text-muted-foreground">
                          {destination.city}, {destination.country}
                        </p>
                        <p className="mt-2 text-sm text-muted-foreground">
                          Confianca: {Math.round((landmark.confidence || 0) * 100)}%
                        </p>
                      </article>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}

          <div className="space-y-2">
            <p className="text-sm font-bold uppercase tracking-[0.16em] text-muted-foreground">
              Lista confirmada
            </p>
            <p className="text-sm leading-6 text-muted-foreground">
              Edite se algum nome, cidade ou pais estiver incorreto.
            </p>
          </div>
          <Textarea
            value={customLandmarksText}
            onChange={(event) => onCustomLandmarksTextChange(event.target.value)}
            placeholder={'Colosseum, Rome, Italy\nTrevi Fountain, Rome, Italy\nSagrada Familia, Barcelona, Spain'}
            className="min-h-36 rounded-2xl bg-background border-border text-base leading-7 focus-visible:ring-accent"
          />
        </section>

        {error && (
          <p className="text-sm font-medium text-destructive bg-destructive/10 py-1.5 px-3 rounded-lg inline-block">
            {error}
          </p>
        )}
      </div>
    </WarmCard>
  );
};

export default CountryAttractionSelector;
