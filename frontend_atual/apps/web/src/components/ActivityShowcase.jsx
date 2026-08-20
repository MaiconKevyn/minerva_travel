import React from 'react';
import { motion } from 'framer-motion';
import { Clock3 } from 'lucide-react';
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

const ActivityShowcase = () => (
  <section
    className="border-t border-border/50 py-20 sm:py-24"
    aria-labelledby="atividades-title"
  >
    <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
      <GuideLockup
        id="atividades-title"
        overline="O que a criança faz"
        title={`${CATEGORIES.reduce((total, category) => total + category.options.length, 0)} atividades diferentes`}
        arched="Escolhidas por vocês"
      />
      <div className="mx-auto max-w-2xl text-center">
        <p className="mt-4 text-lg font-medium text-muted-foreground">
          Cada uma nasce do ponto turístico da vez — o caça-palavras usa o nome do lugar, o
          labirinto leva até ele, o guia de frases é do idioma do país.
        </p>
      </div>

      <div className="mt-14 grid gap-6 md:grid-cols-2">
        {CATEGORIES.map((category, index) => (
          <motion.section
            key={category.id}
            initial={{ opacity: 0, y: 18 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: '-60px' }}
            transition={{ duration: 0.5, delay: (index % 2) * 0.08 }}
            className="rounded-[2rem] border border-border/50 bg-card p-6 sm:p-7"
            aria-labelledby={`categoria-${category.id}`}
          >
            <h3
              id={`categoria-${category.id}`}
              className="font-serif text-xl font-bold text-foreground"
            >
              {category.label}
            </h3>
            <p className="mt-1 text-sm font-medium text-muted-foreground">{category.hint}</p>

            <ul className="mt-5 space-y-2.5">
              {category.options.map((activity) => (
                <li
                  key={activity.type}
                  className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1 border-b border-border/40 pb-2.5 last:border-0 last:pb-0"
                >
                  <span className="font-bold text-foreground">{activity.label}</span>
                  <span className="flex items-center gap-3 text-sm font-medium text-muted-foreground">
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
          </motion.section>
        ))}
      </div>
    </div>
  </section>
);

export default ActivityShowcase;
