import React from 'react';
import { ArrowLeft, ArrowRight, CalendarDays, SlidersHorizontal, Sparkles } from 'lucide-react';
import { useConversationalGuide } from '@/contexts/ConversationalGuideContext.jsx';
import { Button } from '@/components/ui/button';
import { totalTripDays } from '@/utils/guide-form.js';

const interestOptions = [
  { label: 'Parques', value: 'parques' },
  { label: 'Museus', value: 'museus' },
  { label: 'Arte', value: 'arte' },
  { label: 'Animais', value: 'animais' },
  { label: 'Comida', value: 'comida' },
  { label: 'Historia', value: 'historia' },
  { label: 'Lojas', value: 'lojas' },
  { label: 'Rio', value: 'rio' },
  { label: 'Vistas', value: 'vistas' },
];

const paceOptions = [
  { label: 'Leve', value: 'light' },
  { label: 'Equilibrado', value: 'balanced' },
  { label: 'Completo', value: 'full' },
];

const StepTripPreferences = () => {
  const {
    destinationsList,
    itineraryPreferences,
    setItineraryPreferences,
    nextStep,
    goBack,
  } = useConversationalGuide();

  const updatePreference = (key, value) => {
    setItineraryPreferences((prev) => ({ ...prev, [key]: value }));
  };

  const toggleInterest = (interest) => {
    setItineraryPreferences((prev) => ({
      ...prev,
      interests: prev.interests.includes(interest)
        ? prev.interests.filter((item) => item !== interest)
        : [...prev.interests, interest],
    }));
  };

  const days = totalTripDays(destinationsList) || itineraryPreferences.days || 3;

  return (
    <div className="w-full max-w-4xl mx-auto flex flex-col min-h-[60vh] justify-center py-4">
      <div className="text-center space-y-4 mb-10">
        <div className="w-16 h-16 rounded-full bg-primary/10 text-primary flex items-center justify-center mx-auto">
          <Sparkles className="w-8 h-8" />
        </div>
        <h2 className="text-3xl md:text-4xl font-serif font-bold text-foreground">
          Qual ritmo combina com a família?
        </h2>
        <p className="text-lg text-muted-foreground font-medium max-w-2xl mx-auto">
          Use estas preferências para calibrar as sugestões antes de escolher os pontos do guia.
        </p>
      </div>

      <div className="bg-card dark:bg-slate-800 rounded-[32px] p-6 md:p-8 border border-border/60 shadow-sm space-y-8">
        <div className="grid grid-cols-1 md:grid-cols-[0.8fr_1.2fr] gap-6">
          <div className="space-y-3">
            <label className="text-sm font-bold uppercase tracking-[0.18em] text-muted-foreground flex items-center gap-2">
              <CalendarDays className="w-4 h-4" /> Dias
            </label>
            <div className="rounded-2xl bg-muted px-5 py-4 text-lg font-bold text-foreground">
              {days} {days === 1 ? 'dia' : 'dias'} no total
            </div>
          </div>

          <div className="space-y-3">
            <label className="text-sm font-bold uppercase tracking-[0.18em] text-muted-foreground flex items-center gap-2">
              <SlidersHorizontal className="w-4 h-4" /> Ritmo
            </label>
            <div className="flex flex-wrap gap-3">
              {paceOptions.map((option) => (
                <button
                  type="button"
                  key={option.value}
                  onClick={() => updatePreference('pace', option.value)}
                  className={`rounded-full px-5 py-3 font-bold transition-all ${
                    itineraryPreferences.pace === option.value
                      ? 'bg-secondary text-white shadow-md'
                      : 'bg-muted text-muted-foreground hover:bg-secondary/10 hover:text-secondary'
                  }`}
                >
                  {option.label}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="space-y-3">
          <label className="text-sm font-bold uppercase tracking-[0.18em] text-muted-foreground">
            Programas que combinam
          </label>
          <div className="flex flex-wrap gap-3">
            {interestOptions.map((interest) => {
              const selected = itineraryPreferences.interests.includes(interest.value);
              return (
                <button
                  type="button"
                  key={interest.value}
                  onClick={() => toggleInterest(interest.value)}
                  className={`rounded-full px-5 py-3 font-bold transition-all ${
                    selected
                      ? 'bg-primary text-white shadow-md'
                      : 'bg-muted text-muted-foreground hover:bg-primary/10 hover:text-primary'
                  }`}
                >
                  {interest.label}
                </button>
              );
            })}
          </div>
        </div>

        <div className="flex flex-col gap-4 pt-2 sm:flex-row sm:justify-between">
          <Button onClick={goBack} variant="outline" className="rounded-full px-6 py-6 text-base sm:px-8 sm:text-lg">
            <ArrowLeft className="w-5 h-5 mr-2" /> Editar destinos
          </Button>
          <Button
            onClick={nextStep}
            className="rounded-full bg-primary px-6 py-6 text-base font-bold text-white hover:bg-primary/90 sm:px-8 sm:text-lg"
          >
            Ver atrações <ArrowRight className="ml-2 w-5 h-5" />
          </Button>
        </div>
      </div>
    </div>
  );
};

export default StepTripPreferences;
