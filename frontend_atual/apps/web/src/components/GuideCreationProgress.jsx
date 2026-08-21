import React from 'react';
import { Check, MapPin } from 'lucide-react';

const GuideCreationProgress = ({ visibleSteps, currentStep, stepNames }) => {
  const currentPosition = Math.max(visibleSteps.indexOf(currentStep), 0);
  const currentName = stepNames[currentStep] || 'Criar guia';
  const nextStep = visibleSteps[currentPosition + 1];
  const nextName = nextStep ? stepNames[nextStep] : '';
  const progressValue = currentPosition + 1;
  const progressPercent = (progressValue / visibleSteps.length) * 100;

  return (
    <section
      className="travel-card storybook-mint relative overflow-hidden px-5 py-5 sm:px-7 sm:py-6"
      aria-labelledby="guide-creation-progress-title"
    >
      <div className="flex flex-col justify-between gap-2 sm:flex-row sm:items-end sm:gap-5">
        <div>
          <p className="font-ui text-xs font-black uppercase tracking-[0.16em] text-primary">
            Passo {progressValue} de {visibleSteps.length}
          </p>
          <h1
            id="guide-creation-progress-title"
            className="mt-1 font-serif text-2xl font-bold text-secondary sm:text-3xl"
          >
            {currentName}
          </h1>
        </div>
        <p className="font-ui text-sm font-bold text-muted-foreground sm:text-right">
          {nextName ? (
            <>
              Próximo: <span className="text-foreground">{nextName}</span>
            </>
          ) : (
            <span className="text-secondary">Última etapa da criação</span>
          )}
        </p>
      </div>

      <div
        className="mt-4 h-2.5 overflow-hidden rounded-full bg-[hsl(var(--paper)/0.85)] shadow-inner"
        role="progressbar"
        aria-label="Progresso da criação do guia"
        aria-valuemin={1}
        aria-valuemax={visibleSteps.length}
        aria-valuenow={progressValue}
        aria-valuetext={`${currentName}: passo ${progressValue} de ${visibleSteps.length}`}
      >
        <div
          className="h-full rounded-full bg-secondary transition-[width] duration-500 motion-reduce:transition-none"
          style={{ width: `${progressPercent}%` }}
        />
      </div>

      <ol
        className="mt-5 hidden gap-2 lg:grid"
        style={{ gridTemplateColumns: `repeat(${visibleSteps.length}, minmax(0, 1fr))` }}
        aria-label="Etapas da criação"
      >
        {visibleSteps.map((step, index) => {
          const isCurrent = step === currentStep;
          const isComplete = index < currentPosition;
          return (
            <li
              key={step}
              aria-current={isCurrent ? 'step' : undefined}
              className={`flex min-w-0 items-center gap-2 rounded-xl px-2 py-2 text-xs font-bold ${
                isCurrent
                  ? 'bg-primary/10 text-primary'
                  : isComplete
                    ? 'text-secondary'
                    : 'text-muted-foreground'
              }`}
            >
              <span
                className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full border text-[0.65rem] ${
                  isCurrent
                    ? 'border-primary bg-primary text-white'
                    : isComplete
                      ? 'border-secondary bg-secondary text-white'
                      : 'border-secondary/25 bg-[hsl(var(--paper))]'
                }`}
                aria-hidden="true"
              >
                {isComplete ? <Check className="h-3.5 w-3.5" /> : isCurrent ? <MapPin className="h-3.5 w-3.5" /> : index + 1}
              </span>
              <span className="min-w-0 leading-tight">{stepNames[step]}</span>
            </li>
          );
        })}
      </ol>
    </section>
  );
};

export default GuideCreationProgress;
