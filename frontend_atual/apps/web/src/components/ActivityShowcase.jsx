import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Clock3, MapPin, NotebookPen, Palette, Puzzle } from 'lucide-react';
import { GuideLockup } from '@/components/GuideLockup.jsx';
import { activityOptionsByCategory } from '@/utils/landmark-activities.js';

/**
 * O catálogo real, lido do mesmo módulo que monta o passo de atividades.
 *
 * Escrever a lista à mão aqui seria deixá-la envelhecer: a home prometeria
 * doze atividades enquanto o produto já entrega dezoito. Vindo da fonte, a
 * vitrine não tem como divergir do que a família vai encontrar.
 */
const CATEGORIES = activityOptionsByCategory();
const CATEGORY_ICONS = {
  onsite: MapPin,
  puzzle: Puzzle,
  art: Palette,
  writing: NotebookPen,
};

const ActivityShowcase = () => {
  const [activeCategoryId, setActiveCategoryId] = useState(CATEGORIES[0]?.id);
  const activeCategory = CATEGORIES.find((category) => category.id === activeCategoryId)
    || CATEGORIES[0];

  return (
    <section
      id="atividades"
      className="travel-page editorial-section relative overflow-hidden py-16 sm:py-20"
      aria-labelledby="atividades-title"
    >
      <div className="guide-shell">
      <GuideLockup
        id="atividades-title"
        overline="O que a criança faz"
        title={`${CATEGORIES.reduce((total, category) => total + category.options.length, 0)} atividades diferentes`}
        arched="Escolhidas por vocês"
      />
      <div className="mx-auto max-w-2xl text-center">
        <p className="editorial-copy mt-4 text-foreground/70">
          Cada uma nasce do ponto turístico da vez — o caça-palavras usa o nome do lugar, o
          labirinto leva até ele, o guia de frases é do idioma do país.
        </p>
      </div>

        <div
          className="font-ui mx-auto mt-10 flex max-w-4xl gap-2 overflow-x-auto rounded-xl bg-muted p-1.5 sm:mt-12"
          role="tablist"
          aria-label="Filtrar atividades por momento"
        >
          {CATEGORIES.map((category) => {
            const Icon = CATEGORY_ICONS[category.id] || Puzzle;
            const selected = category.id === activeCategory.id;
            return (
              <button
                key={category.id}
                type="button"
                role="tab"
                aria-selected={selected}
                aria-controls="activity-category-panel"
                onClick={() => setActiveCategoryId(category.id)}
                className={`flex min-h-11 shrink-0 items-center gap-2 rounded-lg px-4 text-sm font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ${selected ? 'bg-secondary text-secondary-foreground shadow-sm' : 'text-muted-foreground hover:bg-background/70 hover:text-foreground'}`}
              >
                <Icon className="h-4 w-4" aria-hidden="true" />
                {category.label}
                <span className={selected ? 'text-secondary-foreground/70' : 'text-muted-foreground/70'}>
                  {category.options.length}
                </span>
              </button>
            );
          })}
        </div>

        <motion.section
          key={activeCategory.id}
          id="activity-category-panel"
          role="tabpanel"
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.25 }}
          className="clean-surface mx-auto mt-5 max-w-5xl overflow-hidden"
          aria-labelledby={`categoria-${activeCategory.id}`}
        >
          <div className="border-b border-secondary/15 bg-[hsl(var(--mint)/0.55)] px-5 py-4 sm:px-7">
            <h3 id={`categoria-${activeCategory.id}`} className="font-serif text-xl font-semibold text-foreground">
              {activeCategory.label}
            </h3>
            <p className="mt-1 text-sm text-muted-foreground">{activeCategory.hint}</p>
          </div>

          <ul>
            {activeCategory.options.map((activity) => (
              <li
                key={activity.type}
                className="grid grid-cols-[4rem_1fr] gap-4 border-b border-secondary/15 p-5 last:border-b-0 sm:grid-cols-[5rem_1fr] sm:p-6"
              >
                <img
                  src={activity.preview}
                  alt=""
                  width="128"
                  height="192"
                  loading="lazy"
                  decoding="async"
                  className="aspect-[2/3] w-16 rounded-lg border border-border object-cover sm:w-20"
                />
                <div className="min-w-0">
                  <h4 className="font-serif text-lg font-semibold text-foreground">{activity.label}</h4>
                  <p className="mt-1 line-clamp-2 text-sm leading-relaxed text-foreground/65">
                    {activity.description}
                  </p>
                  <div className="metadata-row mt-3">
                    <span>{activity.ageLabel}</span>
                    <span className="inline-flex items-center gap-1.5">
                      <Clock3 className="h-3.5 w-3.5" aria-hidden="true" />
                      {activity.durationLabel}
                    </span>
                    <span>{activity.materialLabel}</span>
                  </div>
                </div>
              </li>
            ))}
          </ul>
        </motion.section>
      </div>
    </section>
  );
};

export default ActivityShowcase;
