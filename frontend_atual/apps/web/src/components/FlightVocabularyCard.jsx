import React from 'react';
import { Check, MessageCircleHeart } from 'lucide-react';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { countryHasFlightVocabulary, guideFlightVocabularyCountries } from '@/utils/landmark-activities.js';

/**
 * "O primeiro olá": a página que abre o capítulo de cada país ensinando a
 * criança a conversar — olá, tudo bem?, por favor, obrigado e tchau, com a
 * pronúncia como ela lê e uma curiosidade do idioma.
 *
 * Vem ligada, ao contrário do resto do catálogo: quem não conhece o produto
 * não iria procurá-la. Desligar é um clique; descobrir que ela existia, não.
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
      className="rounded-2xl border border-primary/25 bg-[hsl(var(--blush))] p-5 sm:p-6"
      aria-labelledby="flight-vocabulary-title"
    >
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex min-w-0 flex-1 items-start gap-4">
          <MessageCircleHeart className="mt-1 h-7 w-7 shrink-0 text-primary" aria-hidden="true" />
          <div>
            <h3 id="flight-vocabulary-title" className="text-xl font-display font-bold text-foreground">
              O primeiro olá, no idioma de cada país
            </h3>
            <p className="mt-1 font-medium text-muted-foreground">
              Uma página abrindo cada país: olá, tudo bem?, por favor, obrigado e tchau — como se
              escreve, como se fala — e uma curiosidade do idioma.
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
                className="pill-flag pill-flag--paper text-sm"
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
