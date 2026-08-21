import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { ChevronDown, ChevronUp, Clock3 } from 'lucide-react';
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

const ActivityShowcase = () => {
  const [expandedCategories, setExpandedCategories] = useState(() => new Set());

  const toggleCategory = (categoryId) => {
    setExpandedCategories((current) => {
      const next = new Set(current);
      if (next.has(categoryId)) next.delete(categoryId);
      else next.add(categoryId);
      return next;
    });
  };

  return (
    <section
      className="travel-page storybook-paper relative overflow-hidden border-t border-secondary/10 py-16 sm:py-24"
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

        <div className="mt-10 grid gap-6 md:grid-cols-2 sm:mt-14">
          {CATEGORIES.map((category, index) => {
            const expanded = expandedCategories.has(category.id);
            const visibleOptions = expanded ? category.options : category.options.slice(0, 2);
            const hiddenCount = category.options.length - visibleOptions.length;
            return (
          <motion.section
            key={category.id}
            initial={{ opacity: 0, y: 18 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: '-60px' }}
            transition={{ duration: 0.5, delay: (index % 2) * 0.08 }}
            className={`travel-card p-6 sm:p-7 ${index % 2 === 0 ? 'travel-card-pink' : 'travel-card-blue'}`}
            aria-labelledby={`categoria-${category.id}`}
          >
            <h3
              id={`categoria-${category.id}`}
              className="font-serif text-xl font-bold text-foreground"
            >
              {category.label}
            </h3>
            <p className="font-ui mt-1 text-sm font-medium text-muted-foreground">{category.hint}</p>

                <ul id={`atividades-${category.id}`} className="mt-5 space-y-2.5">
                  {visibleOptions.map((activity) => (
                <li
                  key={activity.type}
                  className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1 border-b border-dashed border-secondary/20 pb-2.5 last:border-0 last:pb-0"
                >
                  <span className="font-bold text-foreground">{activity.label}</span>
                  <span className="font-ui flex items-center gap-3 text-sm font-medium text-muted-foreground">
                    <span className="rounded-full bg-muted px-2.5 py-0.5 text-xs font-bold text-foreground">
                      {activity.ageLabel}
                    </span>
                    <span className="inline-flex items-center gap-1">
                      <Clock3 className="h-3.5 w-3.5" aria-hidden="true" />
                      {activity.durationLabel}
                    </span>
                  </span>
                </li>
                  ))}
                </ul>

                {category.options.length > 2 ? (
                  <button
                    type="button"
                    onClick={() => toggleCategory(category.id)}
                    aria-expanded={expanded}
                    aria-controls={`atividades-${category.id}`}
                    className="font-ui mt-5 inline-flex min-h-11 w-full items-center justify-center rounded-xl border-2 border-dashed border-secondary/25 px-4 text-sm font-bold text-secondary transition hover:border-primary/50 hover:text-primary focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-ring/35"
                  >
                    {expanded ? (
                      <>
                        Mostrar menos
                        <ChevronUp className="ml-2 h-4 w-4" aria-hidden="true" />
                      </>
                    ) : (
                      <>
                        Ver mais {hiddenCount} {hiddenCount === 1 ? 'atividade' : 'atividades'}
                        <ChevronDown className="ml-2 h-4 w-4" aria-hidden="true" />
                      </>
                    )}
                  </button>
                ) : null}
          </motion.section>
            );
          })}
        </div>
      </div>
    </section>
  );
};

export default ActivityShowcase;
