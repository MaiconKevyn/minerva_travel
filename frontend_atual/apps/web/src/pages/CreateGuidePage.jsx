
import React from 'react';
import { Helmet } from 'react-helmet';
import { motion, AnimatePresence } from 'framer-motion';
import { ArrowLeft } from 'lucide-react';
import Header from '@/components/Header.jsx';
import { useConversationalGuide } from '@/contexts/ConversationalGuideContext.jsx';
import Step2CoverPhoto from '@/components/Step2CoverPhoto.jsx';
import Step3Destination from '@/components/Step3Destination.jsx';
import StepTripPreferences from '@/components/StepTripPreferences.jsx';
import Step4Attractions from '@/components/Step4Attractions.jsx';
import EnhancedStep5FamilyDetails from '@/components/EnhancedStep5FamilyDetails.jsx';
import StepActivities from '@/components/StepActivities.jsx';
import Step5Review from '@/components/Step5Review.jsx';
import { Button } from '@/components/ui/button';

const CreateGuidePageContent = () => {
  const {
    currentStep,
    goBack,
    itineraryMode,
    draftId,
    draftStatus,
    draftError,
    discardDraft,
  } = useConversationalGuide();
  // No modo "Ja sei o roteiro" a etapa de preferencias (2) e pulada.
  const visibleSteps = itineraryMode === 'known' ? [1, 3, 4, 5, 6, 7] : [1, 2, 3, 4, 5, 6, 7];
  const currentStepPosition = Math.max(visibleSteps.indexOf(currentStep), 0);

  const renderStep = () => {
    switch (currentStep) {
      case 1: return <Step3Destination />;
      case 2: return <StepTripPreferences />;
      case 3: return <Step4Attractions />;
      case 4: return <EnhancedStep5FamilyDetails />;
      case 5: return <StepActivities />;
      case 6: return <Step2CoverPhoto />;
      case 7: return <Step5Review />;
      default: return <Step3Destination />;
    }
  };

  return (
    <>
      <Helmet>
        <title>Criar Guia - Minerva Travel</title>
        <meta name="description" content="Crie seu guia de viagem conversando com nosso assistente." />
      </Helmet>

      <div className="min-h-screen bg-background flex flex-col transition-colors duration-200">
        <Header />

        <main id="main-content" tabIndex={-1} className="flex-1 flex flex-col relative py-8 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto w-full">

          {/* Top Bar with Progress and Back Button */}
          <div className="flex items-center justify-between gap-2 mb-8 md:mb-16">
            <div className="w-14 sm:w-24">
              {currentStep > 1 && currentStep <= 7 && (
                <Button
                  variant="ghost"
                  onClick={goBack}
                  className="rounded-full px-3 font-bold text-muted-foreground hover:text-foreground hover:bg-muted sm:px-4"
                >
                  <ArrowLeft className="h-5 w-5 sm:mr-2" />
                  <span className="hidden sm:inline">Voltar</span>
                </Button>
              )}
            </div>

            <div className="flex-1 max-w-xs mx-auto text-center">
              <div className="flex items-center justify-center gap-2 mb-2">
                {visibleSteps.map((s) => (
                  <div
                    key={s}
                    className={`h-2 rounded-full transition-all duration-500 ${
                      s === currentStep ? 'w-8 bg-primary' : s < currentStep ? 'w-4 bg-primary/40' : 'w-4 bg-border'
                    }`}
                  />
                ))}
              </div>
              <p className="text-sm font-bold text-muted-foreground uppercase tracking-widest">
                Passo {currentStepPosition + 1} de {visibleSteps.length}
              </p>
            </div>

            <div className="flex w-14 justify-end sm:w-24">
              {draftId && (
                <Button
                  type="button"
                  variant="ghost"
                  onClick={discardDraft}
                  disabled={draftStatus === 'saving'}
                  aria-label="Descartar rascunho"
                  className="px-2 text-xs font-bold text-muted-foreground hover:text-destructive sm:px-3"
                >
                  <span className="hidden sm:inline">Descartar</span>
                  <span className="sm:hidden" aria-hidden="true">×</span>
                </Button>
              )}
            </div>
          </div>

          <p
            className={`-mt-5 mb-5 text-center text-xs font-medium ${
              draftStatus === 'error' ? 'text-destructive' : 'text-muted-foreground'
            }`}
            role="status"
            aria-live="polite"
          >
            {draftStatus === 'saving' && 'Salvando rascunho…'}
            {draftStatus === 'saved' && 'Rascunho salvo com segurança. A foto será enviada novamente antes da geração.'}
            {draftStatus === 'error' && draftError}
          </p>

          {/* Form Area */}
          <div className="flex-1 flex flex-col justify-center">
            <AnimatePresence mode="wait">
              <motion.div
                key={currentStep}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -12 }}
                transition={{ duration: 0.3 }}
                className="w-full"
              >
                {renderStep()}
              </motion.div>
            </AnimatePresence>
          </div>
        </main>
      </div>
    </>
  );
};

export default CreateGuidePageContent;
