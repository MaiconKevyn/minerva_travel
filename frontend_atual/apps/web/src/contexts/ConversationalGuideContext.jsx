
import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import {
  createGuideDestination,
  normalizeFamilyMemberCount,
  normalizeGuideDestinations,
  serializeGuideDestinations,
} from '@/utils/guide-form.js';
import {
  createGuideDraft,
  discardGuideDraft,
  getCurrentGuideDraft,
  updateGuideDraft,
} from '@/utils/minerva-api.js';
import {
  normalizeLandmarkActivitySelections,
  pruneLandmarkActivitySelections,
} from '@/utils/landmark-activities.js';

const ConversationalGuideContext = createContext();

export const useConversationalGuide = () => {
  const context = useContext(ConversationalGuideContext);
  if (!context) {
    throw new Error('useConversationalGuide must be used within a ConversationalGuideProvider');
  }
  return context;
};

export const ConversationalGuideProvider = ({ children }) => {
  const [currentStep, setCurrentStep] = useState(1);
  const [familyName, setFamilyName] = useState('');
  const [coverPhoto, setCoverPhoto] = useState(null);
  const [coverPhotoUrl, setCoverPhotoUrl] = useState('');
  const [expectedCoverFamilyMemberCount, setExpectedCoverFamilyMemberCount] = useState(0);
  const [photoProcessingConsent, setPhotoProcessingConsent] = useState(false);
  const [privacyConsentAt, setPrivacyConsentAt] = useState('');
  const [destination, setDestination] = useState('');
  const [destinationsList, setDestinationsListState] = useState(
    () => [createGuideDestination()]
  );
  const [itineraryMode, setItineraryMode] = useState('known');

  // Family Details State
  const [childrenList, setChildrenList] = useState([]);
  const [parentsList, setParentsList] = useState([]);
  const [year, setYear] = useState(2026);

  // Minerva API Integration State
  const [parsedData, setParsedData] = useState({ destinations: [], landmarks: [] });
  const [selectedLandmarks, setSelectedLandmarks] = useState([]); // Array of IDs
  const [landmarkActivitySelections, setLandmarkActivitySelections] = useState([]);
  const [recommendedItinerary, setRecommendedItinerary] = useState(null);
  const [restaurantRecommendationsExtra, setRestaurantRecommendationsExtra] = useState(false);
  const [itineraryPreferences, setItineraryPreferences] = useState({
    days: 3,
    interests: [],
    pace: 'balanced',
  });
  const [isLoadingLandmarks, setIsLoadingLandmarks] = useState(false);
  const [hasSearchedLandmarks, setHasSearchedLandmarks] = useState(false);
  const [draftId, setDraftId] = useState(null);
  const [restoredDraftId, setRestoredDraftId] = useState(null);
  const [restoredDestinationsList, setRestoredDestinationsList] = useState(null);
  const [draftResetKey, setDraftResetKey] = useState(0);
  const [draftRevision, setDraftRevision] = useState(null);
  const [draftStatus, setDraftStatus] = useState('loading');
  const [draftError, setDraftError] = useState('');
  const [draftReady, setDraftReady] = useState(false);
  const lastSavedDraftPayload = useRef('');
  const saveInFlight = useRef(false);

  const guideDraftPayload = useMemo(() => ({
    current_step: currentStep,
    family_name: familyName,
    destination,
    destinations_list: destinationsList,
    itinerary_mode: itineraryMode,
    children_list: childrenList,
    parents_list: parentsList,
    year,
    parsed_data: parsedData,
    selected_landmarks: selectedLandmarks,
    landmark_activity_selections: landmarkActivitySelections,
    recommended_itinerary: recommendedItinerary,
    restaurant_recommendations_extra: restaurantRecommendationsExtra,
    itinerary_preferences: itineraryPreferences,
    has_searched_landmarks: hasSearchedLandmarks,
  }), [
    childrenList,
    currentStep,
    destination,
    destinationsList,
    familyName,
    hasSearchedLandmarks,
    itineraryMode,
    itineraryPreferences,
    landmarkActivitySelections,
    parentsList,
    parsedData,
    recommendedItinerary,
    restaurantRecommendationsExtra,
    selectedLandmarks,
    year,
  ]);

  const hasMeaningfulDraftContent = (payload) => Boolean(
    payload.family_name ||
    payload.destination ||
    payload.children_list?.length ||
    payload.parents_list?.length ||
    payload.selected_landmarks?.length ||
    payload.destinations_list?.some((item) => item.place || item.timing || item.landmarks?.some(Boolean))
  );

  useEffect(() => {
    let active = true;
    getCurrentGuideDraft()
      .then((draft) => {
        if (!active || !draft?.payload) return;
        const payload = draft.payload;
        setCurrentStep(Number(payload.current_step) || 1);
        setFamilyName(String(payload.family_name || ''));
        setDestination(String(payload.destination || ''));
        const restoredDestinations = Array.isArray(payload.destinations_list) && payload.destinations_list.length
          ? normalizeGuideDestinations(payload.destinations_list)
          : [createGuideDestination()];
        setDestinationsListState(restoredDestinations);
        setRestoredDestinationsList(restoredDestinations);
        setItineraryMode(['known', 'freeform', 'suggested'].includes(payload.itinerary_mode)
          ? payload.itinerary_mode
          : 'known');
        setChildrenList(Array.isArray(payload.children_list) ? payload.children_list : []);
        setParentsList(Array.isArray(payload.parents_list) ? payload.parents_list : []);
        setYear(Number(payload.year) || 2026);
        setParsedData(payload.parsed_data && typeof payload.parsed_data === 'object'
          ? payload.parsed_data
          : { destinations: [], landmarks: [] });
        setSelectedLandmarks(Array.isArray(payload.selected_landmarks) ? payload.selected_landmarks : []);
        setLandmarkActivitySelections(
          normalizeLandmarkActivitySelections(payload.landmark_activity_selections),
        );
        setRecommendedItinerary(payload.recommended_itinerary || null);
        setRestaurantRecommendationsExtra(Boolean(payload.restaurant_recommendations_extra));
        setItineraryPreferences(payload.itinerary_preferences && typeof payload.itinerary_preferences === 'object'
          ? payload.itinerary_preferences
          : { days: 3, interests: [], pace: 'balanced' });
        setHasSearchedLandmarks(Boolean(payload.has_searched_landmarks));
        setDraftId(draft.id);
        setRestoredDraftId(draft.id);
        setDraftRevision(draft.revision);
        lastSavedDraftPayload.current = JSON.stringify(payload);
        setDraftStatus('saved');
      })
      .catch(() => {
        if (active) {
          setDraftStatus('error');
          setDraftError('Não foi possível recuperar seu rascunho. Seus novos dados continuam neste dispositivo até serem salvos.');
        }
      })
      .finally(() => {
        if (active) {
          setDraftReady(true);
          setDraftStatus((status) => (status === 'loading' ? 'idle' : status));
        }
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (!draftReady || saveInFlight.current || !hasMeaningfulDraftContent(guideDraftPayload)) {
      return undefined;
    }
    const serialized = JSON.stringify(guideDraftPayload);
    if (serialized === lastSavedDraftPayload.current) return undefined;

    const timer = window.setTimeout(async () => {
      saveInFlight.current = true;
      setDraftStatus('saving');
      setDraftError('');
      try {
        const saved = draftId && draftRevision
          ? await updateGuideDraft(
              draftId,
              { title: 'Rascunho de guia', payload: guideDraftPayload, revision: draftRevision },
            )
          : await createGuideDraft({ title: 'Rascunho de guia', payload: guideDraftPayload });
        lastSavedDraftPayload.current = serialized;
        setDraftId(saved.id);
        setDraftRevision(saved.revision);
        setDraftStatus('saved');
      } catch (error) {
        setDraftStatus('error');
        setDraftError(error.message || 'Não foi possível salvar o rascunho. Tente novamente.');
      } finally {
        saveInFlight.current = false;
      }
    }, 800);
    return () => window.clearTimeout(timer);
  }, [draftId, draftReady, draftRevision, guideDraftPayload]);

  const discardDraft = async () => {
    try {
      if (draftId) await discardGuideDraft(draftId);
    } catch (error) {
      setDraftStatus('error');
      setDraftError(error.message || 'Não foi possível descartar o rascunho.');
      return false;
    }
    setDraftId(null);
    setRestoredDraftId(null);
    setRestoredDestinationsList(null);
    setDraftRevision(null);
    setDraftStatus('idle');
    setDraftError('');
    lastSavedDraftPayload.current = '';
    setCurrentStep(1);
    setFamilyName('');
    updateCoverPhoto(null);
    setExpectedCoverFamilyMemberCount(0);
    setPhotoProcessingConsent(false);
    setPrivacyConsentAt('');
    setDestination('');
    setDestinationsListState([createGuideDestination()]);
    setItineraryMode('known');
    setChildrenList([]);
    setParentsList([]);
    setYear(2026);
    setParsedData({ destinations: [], landmarks: [] });
    setSelectedLandmarks([]);
    setLandmarkActivitySelections([]);
    setRecommendedItinerary(null);
    setRestaurantRecommendationsExtra(false);
    setItineraryPreferences({ days: 3, interests: [], pace: 'balanced' });
    setHasSearchedLandmarks(false);
    setDraftResetKey((value) => value + 1);
    return true;
  };

  const setStep = (step) => {
    setCurrentStep(step);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  // No modo "Ja sei o roteiro" a etapa de preferencias (2) e pulada: o usuario
  // ja informou os pontos turisticos e vai direto para a confirmacao com fotos.
  const nextStep = () => {
    const skipPreferences = itineraryMode === 'known' && currentStep === 1;
    setStep(Math.min(skipPreferences ? 3 : currentStep + 1, 7));
  };

  const goBack = () => {
    const skipPreferences = itineraryMode === 'known' && currentStep === 3;
    setStep(Math.max(skipPreferences ? 1 : currentStep - 1, 1));
  };

  const updateFamilyName = (name) => setFamilyName(name);

  const updateCoverPhoto = (file) => {
    setCoverPhoto(file);
    setCoverPhotoUrl((previousUrl) => {
      if (previousUrl) URL.revokeObjectURL(previousUrl);
      return file ? URL.createObjectURL(file) : '';
    });
  };

  const updatePhotoProcessingConsent = (granted) => {
    const accepted = Boolean(granted);
    setPhotoProcessingConsent(accepted);
    setPrivacyConsentAt(accepted ? new Date().toISOString() : '');
  };

  const updateExpectedCoverFamilyMemberCount = (count) => {
    setExpectedCoverFamilyMemberCount(normalizeFamilyMemberCount(count));
  };

  const resetRouteData = useCallback((nextDestination = '') => {
    setDestination(nextDestination);
    setHasSearchedLandmarks(false);
    setParsedData({ destinations: [], landmarks: [] });
    setSelectedLandmarks([]);
    setLandmarkActivitySelections([]);
    setRecommendedItinerary(null);
  }, []);

  const updateDestination = useCallback((dest) => {
    resetRouteData(dest);
  }, [resetRouteData]);

  const updateDestinationsList = useCallback((destinations) => {
    const normalized = normalizeGuideDestinations(destinations);
    const summary = serializeGuideDestinations(normalized);
    setDestinationsListState(normalized);
    resetRouteData(summary);
  }, [resetRouteData]);

  const setParsedDataState = (data) => {
    setParsedData(data);
  };

  const toggleLandmarkSelection = (landmarkId) => {
    setSelectedLandmarks(prev => {
      if (prev.includes(landmarkId)) {
        return prev.filter(id => id !== landmarkId);
      }
      return [...prev, landmarkId];
    });
  };

  useEffect(() => {
    const selectedIds = new Set(selectedLandmarks.map((id) => String(id)));
    const selectedCanonicalIds = (parsedData.landmarks || [])
      .filter((landmark) =>
        selectedIds.has(String(landmark.id)) ||
        selectedIds.has(String(landmark.selection_id)),
      )
      .map((landmark) => landmark.selection_id || landmark.id);
    setLandmarkActivitySelections((current) => {
      const next = pruneLandmarkActivitySelections(
        current,
        selectedCanonicalIds.length > 0 ? selectedCanonicalIds : selectedLandmarks,
      );
      return JSON.stringify(next) === JSON.stringify(current) ? current : next;
    });
  }, [parsedData.landmarks, selectedLandmarks]);

  return (
    <ConversationalGuideContext.Provider
      value={{
        currentStep,
        setStep,
        nextStep,
        goBack,
        familyName,
        updateFamilyName,
        coverPhoto,
        coverPhotoUrl,
        updateCoverPhoto,
        expectedCoverFamilyMemberCount,
        updateExpectedCoverFamilyMemberCount,
        photoProcessingConsent,
        privacyConsentAt,
        updatePhotoProcessingConsent,
        destination,
        updateDestination,
        destinationsList,
        updateDestinationsList,
        itineraryMode,
        setItineraryMode,

        // Family Details
        childrenList,
        setChildrenList,
        parentsList,
        setParentsList,
        year,
        setYear,

        // Landmark state
        parsedData,
        setParsedData: setParsedDataState,
        selectedLandmarks,
        setSelectedLandmarks,
        toggleLandmarkSelection,
        landmarkActivitySelections,
        setLandmarkActivitySelections,
        recommendedItinerary,
        setRecommendedItinerary,
        restaurantRecommendationsExtra,
        setRestaurantRecommendationsExtra,
        itineraryPreferences,
        setItineraryPreferences,
        isLoadingLandmarks,
        setIsLoadingLandmarks,
        hasSearchedLandmarks,
        setHasSearchedLandmarks,

        // Drafts are saved server-side for the authenticated owner. Photo
        // bytes and photo consent deliberately stay ephemeral and are asked
        // again before generation.
        draftId,
        restoredDraftId,
        restoredDestinationsList,
        draftResetKey,
        draftStatus,
        draftError,
        discardDraft,
      }}
    >
      {children}
    </ConversationalGuideContext.Provider>
  );
};
