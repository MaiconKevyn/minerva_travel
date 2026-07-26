import React from 'react';
import { Check, PlaneTakeoff } from 'lucide-react';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { countryHasFlightVocabulary, guideFlightVocabularyCountries } from '@/utils/landmark-activities.js';

/**
 * A página que a criança faz no avião, antes de pousar em cada país.
 *
 * Vem ligada, ao contrário do resto do catálogo: é a única atividade que
 * acontece antes da viagem começar, e quem não conhece o produto não iria
 * procurá-la. Desligar é um clique; descobrir que ela existia, não.
 */
const FlightVocabularyCard = ({ landmarks, enabled, onChange }) => {
  const covered = guideFlightVocabularyCountries(landmarks);
  const uncovered = [
    ...new Set(
      landmarks
        .map((landmark) => String(landmark.country || '').trim())
        .filter((country) => country && !countryHasFlightVocabulary(country)),
    ),
  ];

  return (
    <section
      className="rounded-[2rem] border-2 border-primary/25 bg-primary/5 p-5 sm:p-6"
      aria-labelledby="flight-vocabulary-title"
    >
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex min-w-0 flex-1 items-start gap-4">
          <PlaneTakeoff className="mt-1 h-7 w-7 shrink-0 text-primary" aria-hidden="true" />
          <div>
            <h3 id="flight-vocabulary-title" className="text-xl font-serif font-bold text-foreground">
              Primeiras palavras, para treinar no avião
            </h3>
            <p className="mt-1 font-medium text-muted-foreground">
              Uma página antes de cada país, com palavras do dia a dia e palavras dos lugares que
              vocês vão visitar — como se escreve, como se fala e o que quer dizer.
            </p>
          </div>
        </div>

        <div className="flex shrink-0 items-center gap-3">
          <Label htmlFor="flight-vocabulary" className="text-sm font-bold text-foreground">
            {enabled ? 'No guia' : 'Fora do guia'}
          </Label>
          <Switch
            id="flight-vocabulary"
            checked={enabled}
            onCheckedChange={onChange}
            aria-describedby="flight-vocabulary-countries"
          />
        </div>
      </div>

      <div id="flight-vocabulary-countries" className="mt-4 border-t border-primary/20 pt-4">
        {covered.length > 0 ? (
          <ul className="flex flex-wrap gap-2">
            {covered.map((item) => (
              <li
                key={item.country}
                className="inline-flex items-center gap-1.5 rounded-full bg-background px-3 py-1 text-sm font-bold text-foreground"
              >
                <Check className="h-3.5 w-3.5 text-primary" aria-hidden="true" />
                {item.country} · {item.language}
              </li>
            ))}
          </ul>
        ) : (
          // O país sai do destino no formato "Cidade, País". Quem digita só
          // "Paris" e segue em frente perderia a página sem saber por quê.
          <p className="text-sm font-medium text-muted-foreground">
            Ainda não sabemos o país da viagem. Volte ao roteiro e escolha o destino pela busca —
            ela preenche "Cidade, País", e é do país que vem o idioma das palavras.
          </p>
        )}

        {/* Dizer o que não vem evita a família procurar uma página que não existe. */}
        {uncovered.length > 0 && (
          <p className="mt-3 text-sm font-medium text-muted-foreground">
            Ainda não temos o idioma conferido de {uncovered.join(', ')} — esses países ficam sem a
            página, em vez de sair com uma pronúncia que não checamos.
          </p>
        )}
      </div>
    </section>
  );
};

export default FlightVocabularyCard;
