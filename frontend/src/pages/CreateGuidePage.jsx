import React, { useEffect, useMemo, useState } from 'react';
import { Helmet } from 'react-helmet';
import { AlertCircle, Check, Loader2, Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';
import Header from '@/components/Header.jsx';
import PhotoUploadSection from '@/components/PhotoUploadSection.jsx';
import FamilyInfoForm from '@/components/FamilyInfoForm.jsx';
import CountryAttractionSelector from '@/components/CountryAttractionSelector.jsx';
import SummaryPreview from '@/components/SummaryPreview.jsx';
import { validateAllFields } from '@/lib/FormValidation.js';
import { fetchCatalog, generateGuide, parseLandmarks } from '@/lib/api.js';
import { Flower, Airplane, Suitcase } from '@/components/DecorativeElements.jsx';

const CreateGuidePage = () => {
  const [catalog, setCatalog] = useState(null);
  const [catalogError, setCatalogError] = useState(null);
  const [isLoadingCatalog, setIsLoadingCatalog] = useState(true);
  const [photo, setPhoto] = useState(null);
  const [title, setTitle] = useState('');
  const [year, setYear] = useState('2026');
  const [parentsNames, setParentsNames] = useState(['Ana', 'Otavio']);
  const [childrenNames, setChildrenNames] = useState(['Alice', 'Antonio']);
  const [selectedLandmarks, setSelectedLandmarks] = useState(new Set());
  const [customLandmarksText, setCustomLandmarksText] = useState('');
  const [landmarkMessage, setLandmarkMessage] = useState('');
  const [landmarkPreview, setLandmarkPreview] = useState(null);
  const [isParsingLandmarks, setIsParsingLandmarks] = useState(false);
  const [errors, setErrors] = useState({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [result, setResult] = useState(null);

  useEffect(() => {
    let mounted = true;

    async function loadCatalog() {
      try {
        const loadedCatalog = await fetchCatalog();

        if (!mounted) {
          return;
        }

        setCatalog(loadedCatalog);
        setTitle(loadedCatalog.title);
        setSelectedLandmarks(
          new Set(
            loadedCatalog.destinations.flatMap((destination) =>
              destination.landmarks.map((landmark) => landmark.selection_id)
            )
          )
        );
      } catch (error) {
        if (mounted) {
          setCatalogError(error instanceof Error ? error.message : 'Nao foi possivel carregar o roteiro.');
        }
      } finally {
        if (mounted) {
          setIsLoadingCatalog(false);
        }
      }
    }

    loadCatalog();

    return () => {
      mounted = false;
    };
  }, []);

  const selectedByCity = useMemo(() => {
    if (!catalog) {
      return [];
    }

    return catalog.destinations.map((destination) => ({
      destination,
      count: destination.landmarks.filter((landmark) =>
        selectedLandmarks.has(landmark.selection_id)
      ).length,
    }));
  }, [catalog, selectedLandmarks]);

  const steps = [
    { id: 'photo-section', label: 'A Capa', completed: !!photo, color: 'text-primary' },
    {
      id: 'family-section',
      label: 'A Família',
      completed: title && parentsNames.some((parent) => parent.trim()) && childrenNames.some((child) => child.trim()),
      color: 'text-secondary',
    },
    {
      id: 'countries-section',
      label: 'Os Destinos',
      completed: selectedLandmarks.size > 0 || customLandmarksText.trim().length > 0,
      color: 'text-accent',
    },
    { id: 'summary-section', label: 'A História', completed: !!result, color: 'text-foreground' },
  ];

  const handleSubmit = async (event) => {
    event.preventDefault();

    if (!catalog) {
      toast.error('O roteiro ainda nao carregou.');
      return;
    }

    const cleanedParents = parentsNames.map((parent) => parent.trim()).filter(Boolean);
    const cleanedChildren = childrenNames.map((child) => child.trim()).filter(Boolean);
    const formState = {
      photo,
      title,
      year,
      parents: cleanedParents,
      children: cleanedChildren,
      selectedLandmarks,
      customLandmarksText,
    };
    const validation = validateAllFields(formState);

    if (!validation.valid) {
      toast.error(validation.error);
      setErrors(mapValidationError(validation.error));
      scrollToFirstInvalid(validation.error);
      return;
    }

    setErrors({});
    setResult(null);
    setIsSubmitting(true);

    const formData = new FormData();
    formData.append('title', title.trim());
    formData.append('children_names', cleanedChildren.join(', '));
    formData.append('parents_names', cleanedParents.join(', '));
    formData.append('year', year);
    formData.append('family_photo', photo);
    selectedLandmarks.forEach((selectionId) => {
      formData.append('selected_landmarks', selectionId);
    });
    if (customLandmarksText.trim()) {
      formData.append('custom_landmarks', customLandmarksText.trim());
    }

    try {
      const generated = await generateGuide(formData);
      setResult(generated);
      toast.success('O guia da sua familia foi criado.');
      document.getElementById('summary-section')?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Nao conseguimos criar o guia agora. Tente de novo.';
      toast.error(message);
      setErrors({ submit: message });
    } finally {
      setIsSubmitting(false);
    }
  };

  const toggleLandmark = (selectionId) => {
    setSelectedLandmarks((current) => {
      const next = new Set(current);

      if (next.has(selectionId)) {
        next.delete(selectionId);
      } else {
        next.add(selectionId);
      }

      return next;
    });
  };

  const selectDestination = (destinationId, checked) => {
    setSelectedLandmarks((current) => {
      const next = new Set(current);
      const destination = catalog?.destinations.find((item) => item.id === destinationId);

      destination?.landmarks.forEach((landmark) => {
        if (checked) {
          next.add(landmark.selection_id);
        } else {
          next.delete(landmark.selection_id);
        }
      });

      return next;
    });
  };

  const handleParseLandmarkMessage = async () => {
    if (!landmarkMessage.trim()) {
      toast.error('Escreva os pontos turisticos que deseja incluir.');
      setErrors((current) => ({
        ...current,
        selectedLandmarks: 'Escreva os pontos turisticos que deseja incluir.',
      }));
      return;
    }

    setIsParsingLandmarks(true);
    setErrors((current) => ({ ...current, selectedLandmarks: null }));

    try {
      const preview = await parseLandmarks(landmarkMessage.trim());
      setLandmarkPreview(preview);
      setCustomLandmarksText(preview.custom_landmarks || '');
      toast.success('Pontos turisticos interpretados. Confira antes de gerar.');
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Nao foi possivel interpretar o roteiro.';
      toast.error(message);
      setErrors((current) => ({ ...current, selectedLandmarks: message }));
    } finally {
      setIsParsingLandmarks(false);
    }
  };

  return (
    <>
      <Helmet>
        <title>Crie Seu Guia - Aventuras em Familia</title>
        <meta name="description" content="Envie uma foto, escolha o roteiro e gere o PDF personalizado da sua familia." />
      </Helmet>

      <div className="min-h-screen bg-background">
        <Header />

        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-16 relative">
          <Flower className="absolute top-20 -left-12 w-32 h-32 text-primary opacity-5 hidden lg:block" />
          <Airplane className="absolute top-1/3 -right-16 w-40 h-40 text-secondary opacity-5 hidden lg:block" />
          <Suitcase className="absolute bottom-1/4 -left-10 w-24 h-24 text-accent opacity-5 hidden lg:block" />

          <div className="text-center mb-16 space-y-4">
            <h1 className="text-5xl md:text-6xl font-serif font-bold text-foreground">
              Escreva Sua <span className="text-primary">História</span>
            </h1>
            <p className="text-xl text-muted-foreground font-medium">
              Envie a foto, escolha o roteiro e baixe o PDF personalizado.
            </p>
          </div>

          {isLoadingCatalog && (
            <StatusCard>
              <Loader2 className="h-6 w-6 animate-spin text-primary" />
              Carregando roteiro...
            </StatusCard>
          )}

          {catalogError && (
            <StatusCard tone="error">
              <AlertCircle className="h-6 w-6 text-destructive" />
              {catalogError}
            </StatusCard>
          )}

          {catalog && (
            <>
              <div className="mb-16 bg-white p-6 rounded-3xl shadow-sm border border-border/50">
                <div className="flex items-center justify-between relative">
                  <div className="absolute top-1/2 left-0 right-0 h-1 bg-muted -z-10 -translate-y-1/2 rounded-full" />
                  {steps.map((step, index) => (
                    <button
                      key={step.id}
                      type="button"
                      onClick={() => document.getElementById(step.id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })}
                      className="flex flex-col items-center gap-3 bg-white px-2"
                    >
                      <span
                        className={`w-12 h-12 rounded-full flex items-center justify-center transition-all duration-300 border-4 border-white shadow-md ${
                          step.completed
                            ? 'bg-primary text-white scale-110'
                            : 'bg-muted text-muted-foreground'
                        }`}
                      >
                        {step.completed ? (
                          <Check className="w-6 h-6" />
                        ) : (
                          <span className="text-lg font-serif font-bold">{index + 1}</span>
                        )}
                      </span>
                      <span className={`text-sm font-bold uppercase tracking-wider hidden sm:block ${step.completed ? step.color : 'text-muted-foreground'}`}>
                        {step.label}
                      </span>
                    </button>
                  ))}
                </div>
              </div>

              <form onSubmit={handleSubmit} className="space-y-16 relative z-10">
                <div id="photo-section" className="scroll-mt-32">
                  <PhotoUploadSection
                    photo={photo}
                    onPhotoChange={setPhoto}
                    error={errors.photo}
                  />
                </div>

                <Divider />

                <div id="family-section" className="scroll-mt-32">
                  <FamilyInfoForm
                    title={title}
                    onTitleChange={setTitle}
                    year={year}
                    onYearChange={setYear}
                    parents={parentsNames}
                    onParentsChange={setParentsNames}
                    childrenNames={childrenNames}
                    onChildrenChange={setChildrenNames}
                    errors={errors}
                  />
                </div>

                <Divider />

                <div id="countries-section" className="scroll-mt-32">
                  <CountryAttractionSelector
                    catalog={catalog}
                    selectedLandmarks={selectedLandmarks}
                    landmarkMessage={landmarkMessage}
                    onLandmarkMessageChange={setLandmarkMessage}
                    landmarkPreview={landmarkPreview}
                    isParsingLandmarks={isParsingLandmarks}
                    onParseLandmarkMessage={handleParseLandmarkMessage}
                    customLandmarksText={customLandmarksText}
                    onCustomLandmarksTextChange={(value) => {
                      setCustomLandmarksText(value);
                    }}
                    onToggleLandmark={toggleLandmark}
                    onSelectDestination={selectDestination}
                    error={errors.selectedLandmarks}
                  />
                </div>

                <Divider />

                <div id="summary-section" className="scroll-mt-32 bg-white rounded-[40px] p-8 md:p-12 shadow-xl border-2 border-primary/10">
                  <SummaryPreview
                    catalog={catalog}
                    result={result}
                    formData={{
                      photo,
                      title,
                      year,
                      parents: parentsNames.map((parent) => parent.trim()).filter(Boolean),
                      children: childrenNames.map((child) => child.trim()).filter(Boolean),
                      selectedLandmarks,
                      customLandmarksText,
                    }}
                  />

                  {errors.submit && (
                    <p className="mt-8 text-center text-sm font-medium text-destructive bg-destructive/10 py-3 px-4 rounded-2xl">
                      {errors.submit}
                    </p>
                  )}

                  <div className="flex justify-center pt-12">
                    <Button
                      type="submit"
                      size="lg"
                      disabled={isSubmitting}
                      className="rounded-full text-xl px-14 py-8 bg-primary hover:bg-primary/90 text-white shadow-[0_8px_30px_rgb(232,122,93,0.3)] hover:shadow-[0_8px_40px_rgb(232,122,93,0.4)] transition-all duration-300 hover:-translate-y-1 disabled:opacity-70 disabled:hover:translate-y-0"
                    >
                      {isSubmitting ? (
                        <>
                          <Loader2 className="w-6 h-6 animate-spin mr-3 inline-block" />
                          Gerando PDF...
                        </>
                      ) : (
                        <>
                          <Sparkles className="w-6 h-6 mr-3 inline-block" />
                          Gerar PDF
                        </>
                      )}
                    </Button>
                  </div>
                </div>
              </form>

              <aside className="mt-10 grid gap-3 md:grid-cols-4">
                {selectedByCity.map(({ destination, count }) => (
                  <div key={destination.id} className="rounded-2xl border border-border bg-white/70 px-4 py-3 text-center">
                    <p className="font-serif text-lg font-bold text-foreground">{destination.city}</p>
                    <p className="text-sm text-muted-foreground">{count} locais</p>
                  </div>
                ))}
              </aside>
            </>
          )}
        </div>

        <footer className="bg-muted py-8 text-center text-muted-foreground font-medium border-t border-border mt-24">
          <p>© 2026 Minerva Travel. Feito para transformar viagens em memoria.</p>
        </footer>
      </div>
    </>
  );
};

function Divider() {
  return (
    <div className="flex justify-center">
      <div className="w-2 h-16 border-l-4 border-dotted border-border/50" />
    </div>
  );
}

function StatusCard({ children, tone = 'neutral' }) {
  const toneClass = tone === 'error' ? 'border-destructive/30 bg-destructive/10 text-destructive' : 'border-border bg-white text-foreground';

  return (
    <div className={`mx-auto mb-10 flex max-w-xl items-center justify-center gap-3 rounded-3xl border p-6 text-center font-semibold ${toneClass}`}>
      {children}
    </div>
  );
}

function mapValidationError(error) {
  if (error.includes('foto')) {
    return { photo: error };
  }
  if (error.includes('titulo')) {
    return { title: error };
  }
  if (error.includes('ano')) {
    return { year: error };
  }
  if (error.includes('responsavel')) {
    return { parents: error };
  }
  if (error.includes('crianca')) {
    return { children: error };
  }
  if (error.includes('ponto turistico')) {
    return { selectedLandmarks: error };
  }
  return { submit: error };
}

function scrollToFirstInvalid(error) {
  if (error.includes('foto')) {
    document.getElementById('photo-section')?.scrollIntoView({ behavior: 'smooth', block: 'center' });
  } else if (error.includes('titulo') || error.includes('ano') || error.includes('responsavel') || error.includes('crianca')) {
    document.getElementById('family-section')?.scrollIntoView({ behavior: 'smooth', block: 'center' });
  } else if (error.includes('ponto turistico')) {
    document.getElementById('countries-section')?.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }
}

export default CreateGuidePage;
