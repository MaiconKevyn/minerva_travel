
import React from 'react';
import { Helmet } from 'react-helmet';
import { motion, AnimatePresence } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Loader2 } from 'lucide-react';
import Header from '@/components/Header.jsx';
import { CompassRose, LeafSprig } from '@/components/DecorativeElements.jsx';
import DraftStatusNotice from '@/components/DraftStatusNotice.jsx';
import GuideCreationProgress from '@/components/GuideCreationProgress.jsx';
import GuideDraftActions from '@/components/GuideDraftActions.jsx';
import { useConversationalGuide } from '@/contexts/ConversationalGuideContext.jsx';
import Step2CoverPhoto from '@/components/Step2CoverPhoto.jsx';
import Step3Destination from '@/components/Step3Destination.jsx';
import StepTripPreferences from '@/components/StepTripPreferences.jsx';
import Step4Attractions from '@/components/Step4Attractions.jsx';
import EnhancedStep5FamilyDetails from '@/components/EnhancedStep5FamilyDetails.jsx';
import StepActivities from '@/components/StepActivities.jsx';
import Step5Review from '@/components/Step5Review.jsx';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';

const STEP_NAMES = {
  1: 'Destinos da viagem',
  2: 'Ritmo da família',
  3: 'Pontos turísticos',
  4: 'Quem embarca?',
  5: 'Atividades',
  6: 'Capa do guia',
  7: 'Revisão',
};

const CreateGuidePageContent = () => {
  const navigate = useNavigate();
  const [isLeaving, setIsLeaving] = React.useState(false);
  const {
    currentStep,
    goBack,
    itineraryMode,
    draftId,
    draftStatus,
    draftError,
    draftReady,
    restoredProgress,
    builderSessionId,
    coverPhoto,
    saveDraftNow,
    discardDraft,
  } = useConversationalGuide();
  // No modo "Ja sei o roteiro" a etapa de preferencias (2) e pulada.
  const visibleSteps = itineraryMode === 'known' ? [1, 3, 4, 5, 6, 7] : [1, 2, 3, 4, 5, 6, 7];

  const handleContinueLater = async () => {
    setIsLeaving(true);
    const saved = await saveDraftNow();
    if (saved) {
      navigate('/dashboard');
      return;
    }
    setIsLeaving(false);
    toast.error('Não conseguimos salvar o rascunho agora. Tente novamente antes de sair.');
  };

  const handleDiscard = async () => {
    const discarded = await discardDraft();
    if (discarded) toast.success('Rascunho descartado.');
    return discarded;
  };

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

  if (!draftReady) {
    return (
      <>
        <Helmet>
          <title>Retomando guia - Minerva Travel</title>
        </Helmet>
        <div className="min-h-screen bg-background">
          <Header />
          <main
            id="main-content"
            tabIndex={-1}
            className="travel-page storybook-mint mx-auto flex min-h-[70vh] max-w-none flex-col items-center justify-center overflow-hidden px-6 text-center"
          >
            <CompassRose className="page-corner -right-5 top-10 rotate-12" />
            <div className="clean-surface relative max-w-xl px-8 py-10">
              <Loader2 className="mx-auto mb-5 h-12 w-12 animate-spin text-primary" aria-hidden="true" />
              <h1 className="font-display text-3xl font-bold text-secondary">Retomando seu guia…</h1>
              <p className="editorial-copy mt-3 text-muted-foreground">
                Estamos reabrindo a etapa, as escolhas e as páginas que você já criou.
              </p>
            </div>
          </main>
        </div>
      </>
    );
  }

  return (
    <>
      <Helmet>
        <title>Criar Guia - Minerva Travel</title>
        <meta name="description" content="Monte o guia de atividades da viagem da sua família: um PDF ilustrado para a criança preencher pelo caminho." />
      </Helmet>

      <div className="min-h-screen bg-background flex flex-col transition-colors duration-200">
        <Header />

        <main id="main-content" tabIndex={-1} className="travel-page storybook-paper relative flex flex-1 flex-col overflow-hidden px-4 py-5 sm:px-6 sm:py-7 lg:px-8 lg:py-10">
          <CompassRose className="page-corner -right-6 top-16 rotate-12" />
          <LeafSprig className="page-corner -bottom-12 -left-8 -rotate-12 text-accent" />

          <div className="guide-shell relative z-10 mb-6 md:mb-10">
            <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
              <div>
                {currentStep > 1 && currentStep <= 7 && (
                  <Button
                    variant="ghost"
                    onClick={goBack}
                    aria-label="Voltar para a etapa anterior"
                    className="font-ui h-11 min-w-11 rounded-lg border border-secondary/20 bg-[hsl(var(--paper)/0.82)] px-3 font-semibold text-secondary hover:bg-muted sm:px-4"
                  >
                    <ArrowLeft className="h-5 w-5 sm:mr-2" />
                    <span className="hidden sm:inline">Voltar</span>
                  </Button>
                )}
              </div>
              <GuideDraftActions
                hasDraft={Boolean(draftId)}
                busy={isLeaving || draftStatus === 'saving'}
                onContinueLater={handleContinueLater}
                onDiscard={handleDiscard}
              />
            </div>

            <GuideCreationProgress
              visibleSteps={visibleSteps}
              currentStep={currentStep}
              stepNames={STEP_NAMES}
            />
            <DraftStatusNotice
              status={draftStatus}
              error={draftError}
              restoredProgress={restoredProgress}
              builderSessionId={builderSessionId}
              hasUnsavedPhoto={Boolean(coverPhoto)}
            />
          </div>

          {/* Form Area */}
          <div className="guide-shell relative z-10 flex flex-1 flex-col justify-center">
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
